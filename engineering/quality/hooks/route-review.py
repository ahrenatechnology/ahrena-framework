#!/usr/bin/env python3
"""Router for skills/reviewing-diffs/SKILL.md: which review skills a change selects.

Reads a route table and a change, and prints every route that fires with the
skill it selects, the files that skill opens for it, and the path or line that
fired it. A route fires on a changed file when each driver it declares matches:

    paths     a regular expression that matches the file's path
    lines     a regular expression that matches a line the change adds
    contains  a regular expression that matches the file's text at the head

A route marked `baseline` reaches every file and is not counted as coverage, so
a path only baseline routes reach is printed as unrouted. A path matching an
`ignore` expression selects nothing.

Usage:
    python3 engineering/fundamentals/hooks/route-review.py --changed <base>...<head>
    python3 engineering/fundamentals/hooks/route-review.py --cached
    python3 engineering/fundamentals/hooks/route-review.py --changed <range> --json
    python3 engineering/fundamentals/hooks/route-review.py --changed <range> --routes table.json

Exit 0 when the change was routed, 2 when the table is malformed or git cannot
resolve the change. It never exits 1: routing reports and decides no condition.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TABLE = Path(__file__).resolve().parent.parent / "skills" / "reviewing-diffs" / "references" / "routes.json"
DRIVERS = ("paths", "lines", "contains")
ROUTE_KEYS = {"id", "skill", "opens", "why", "baseline", *DRIVERS}
TABLE_KEYS = {"ignore", "routes"}
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
EVIDENCE_SHOWN = 3


class Unroutable(Exception):
    """The table or the change cannot be read, so nothing was routed."""


@dataclass(frozen=True)
class Route:
    id: str
    skill: str
    opens: tuple[str, ...]
    why: str
    baseline: bool
    paths: tuple[re.Pattern[str], ...]
    lines: tuple[re.Pattern[str], ...]
    contains: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class Table:
    ignore: tuple[re.Pattern[str], ...]
    routes: tuple[Route, ...]


@dataclass
class Changed:
    path: str
    deleted: bool = False
    added: list[tuple[int, str]] = field(default_factory=list)
    text: str = ""


def _compile(owner: str, key: str, sources: object) -> tuple[re.Pattern[str], ...]:
    if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
        raise Unroutable(f"{owner}: '{key}' is a list of regular expressions")
    compiled = []
    for source in sources:
        try:
            compiled.append(re.compile(source))
        except re.error as error:
            raise Unroutable(f"{owner}: '{key}' holds an invalid regular expression {source!r}: {error}") from error
    return tuple(compiled)


def _route(raw: object, position: int) -> Route:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise Unroutable(f"route {position}: a route is an object with an 'id'")
    owner = f"route '{raw['id']}'"
    unknown = sorted(set(raw) - ROUTE_KEYS)
    if unknown:
        raise Unroutable(f"{owner}: unknown key {', '.join(unknown)}")
    if not isinstance(raw.get("skill"), str):
        raise Unroutable(f"{owner}: 'skill' names the skill the route selects")
    baseline = raw.get("baseline", False) is True
    if not baseline and not any(raw.get(key) for key in DRIVERS):
        raise Unroutable(f"{owner}: no driver; declare 'paths', 'lines' or 'contains', or mark it 'baseline'")
    compiled = {key: _compile(owner, key, raw.get(key, [])) for key in DRIVERS}
    return Route(raw["id"], raw["skill"], tuple(raw.get("opens", [])), raw.get("why", ""), baseline, **compiled)


def load_table(path: Path) -> Table:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Unroutable(f"{path}: cannot be read as JSON: {error}") from error
    if not isinstance(raw, dict) or set(raw) - TABLE_KEYS or not isinstance(raw.get("routes"), list):
        raise Unroutable(f"{path}: a table is an object with 'routes' and an optional 'ignore'")
    routes = tuple(_route(entry, position) for position, entry in enumerate(raw["routes"], 1))
    seen: set[str] = set()
    for route in routes:
        if route.id in seen:
            raise Unroutable(f"route '{route.id}': the id is declared twice")
        seen.add(route.id)
    return Table(_compile("table", "ignore", raw.get("ignore", [])), routes)


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise Unroutable(f"git {' '.join(args)}: {done.stderr.strip() or 'failed'}")
    return done.stdout


def _added_lines(diff: str) -> list[tuple[int, str]]:
    """The lines a unified diff adds, each with its number in the new file."""
    added, number = [], 0
    for line in diff.splitlines():
        hunk = HUNK.match(line)
        if hunk:
            number = int(hunk.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            added.append((number, line[1:]))
            number += 1
    return added


def read_change(spec: list[str], head: str) -> list[Changed]:
    """Every file the change touches, with its added lines and its text at `head`."""
    changed = []
    for row in _git("diff", "--name-status", "--no-renames", *spec).splitlines():
        status, _, path = row.partition("\t")
        item = Changed(path, deleted=status == "D")
        if not item.deleted:
            item.added = _added_lines(_git("diff", "--unified=0", "--no-renames", *spec, "--", path))
            item.text = _git("show", f"{head}:{path}")
        changed.append(item)
    return changed


def _evidence(route: Route, item: Changed) -> str | None:
    """Where `route` fires on `item`, or None when one of its drivers does not match."""
    if route.paths and not any(p.search(item.path) for p in route.paths):
        return None
    if item.deleted:
        return None if route.lines or route.contains else f"{item.path} (deleted)"
    if route.contains and not any(p.search(item.text) for p in route.contains):
        return None
    if not route.lines:
        return item.path
    hit = next((number for number, text in item.added if any(p.search(text) for p in route.lines)), None)
    return None if hit is None else f"{item.path}:{hit}"


def route_change(table: Table, changed: list[Changed]) -> dict:
    """The routes that fire, the paths nothing but a baseline reaches, and the paths ignored."""
    fired: dict[str, list[str]] = {}
    unrouted, ignored = [], []
    for item in changed:
        if any(p.search(item.path) for p in table.ignore):
            ignored.append(item.path)
            continue
        covered = False
        for route in table.routes:
            where = _evidence(route, item)
            if where is not None:
                fired.setdefault(route.id, []).append(where)
                covered = covered or not route.baseline
        if not covered:
            unrouted.append(item.path)
    routes = [
        {"id": r.id, "skill": r.skill, "opens": list(r.opens), "why": r.why, "on": fired[r.id]}
        for r in table.routes
        if r.id in fired
    ]
    return {"routes": routes, "skills": sorted({r["skill"] for r in routes}), "unrouted": unrouted, "ignored": ignored}


def render(result: dict) -> str:
    out = []
    for route in result["routes"]:
        shown = route["on"][:EVIDENCE_SHOWN]
        more = len(route["on"]) - len(shown)
        out.append(f"route  {route['id']}  ->  {route['skill']}")
        out.extend(f"  opens  {name}" for name in route["opens"])
        out.append(f"  on     {', '.join(shown)}" + (f" and {more} more" if more else ""))
    out.extend(f"unrouted  {path}  (no route beyond the baseline reaches it)" for path in result["unrouted"])
    out.extend(f"ignored   {path}" for path in result["ignored"])
    out.append(f"skills: {', '.join(result['skills']) or 'none'}")
    return "\n".join(out)


def _option(argv: list[str], name: str) -> str | None:
    if name not in argv:
        return None
    position = argv.index(name)
    if position + 1 >= len(argv):
        raise Unroutable(f"{name} takes a value")
    return argv[position + 1]


def _change_spec(argv: list[str]) -> tuple[list[str], str]:
    """The arguments `git diff` takes for this change, and the revision its head is read at."""
    if "--cached" in argv:
        return ["--cached"], ""
    spec = _option(argv, "--changed")
    if not spec:
        raise Unroutable("name the change: --changed <base>...<head>, or --cached")
    return [spec], re.split(r"\.{2,3}", spec)[-1] or "HEAD"


def main(argv: list[str]) -> int:
    try:
        table = load_table(Path(_option(argv, "--routes") or DEFAULT_TABLE))
        result = route_change(table, read_change(*_change_spec(argv)))
    except Unroutable as error:
        print(f"route-review: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if "--json" in argv else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
