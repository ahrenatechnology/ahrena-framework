#!/usr/bin/env python3
"""Tests for route-review.py.

Each case builds a change in a scratch repository, runs the router as a
subprocess and asserts on its exit code and on what it printed. The first
cases use a small table written for the case, so each pins one behaviour. The
last ones read the table the plugin ships, because a route that names a file
nobody wrote selects a skill that cannot be loaded.

The cases name the acceptance criterion of #128 each decides, as `#128/AC-1`
through `#128/AC-6`.

Usage:
    python3 engineering/fundamentals/hooks/test-route-review.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "route-review.py"
PLUGIN = HOOK.parent.parent
ROOT = PLUGIN.parent.parent
SHIPPED = PLUGIN / "skills" / "reviewing-diffs" / "references" / "routes.json"

TABLE = {
    "ignore": ["(^|/)dist/", "\\.lock$", "\\.min\\.js$"],
    "routes": [
        {"id": "sweep", "skill": "skills/sweeping/SKILL.md", "baseline": True},
        {"id": "python", "skill": "skills/reading/SKILL.md", "opens": ["rules/a.md"], "paths": ["\\.py$"]},
        {"id": "model", "skill": "skills/prompting/SKILL.md", "paths": ["\\.py$"], "lines": ["call_model\\("]},
        {"id": "framed", "skill": "skills/framing/SKILL.md", "paths": ["\\.md$"], "contains": ["(?m)^clade:"]},
    ],
}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def scratch(repo: Path, base: dict[str, str], head: dict[str, str | None]) -> None:
    """A repository with one commit holding `base` and a second applying `head`."""
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "case@example.com")
    git(repo, "config", "user.name", "case")
    git(repo, "config", "commit.gpgsign", "false")
    write(repo, {"README": "seed\n", **base})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    write(repo, head)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "head")


def write(repo: Path, files: dict[str, str | None]) -> None:
    for name, text in files.items():
        target = repo / name
        if text is None:
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def run(repo: Path, table: dict | None, *extra: str) -> tuple[int, str]:
    args = [sys.executable, str(HOOK), "--changed", "HEAD~1...HEAD", *extra]
    if table is not None:
        path = repo.parent / f"{repo.name}-routes.json"
        path.write_text(json.dumps(table), encoding="utf-8")
        args += ["--routes", str(path)]
    done = subprocess.run(args, cwd=repo, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


CASES = [
    # (name, base files, head files, table, exit code, must appear, must not appear)
    (
        "#128/AC-1 a route that fires is printed with its skill, what it opens and where it fired",
        {},
        {"app/service.py": "x = 1\n"},
        TABLE,
        0,
        ["route  python  ->  skills/reading/SKILL.md", "opens  rules/a.md", "on     app/service.py"],
        ["route  model", "route  framed"],
    ),
    (
        "#128/AC-1 the skills line lists each selected skill once",
        {},
        {"a.py": "x = 1\n", "b.py": "y = 2\n"},
        TABLE,
        0,
        ["skills: skills/reading/SKILL.md, skills/sweeping/SKILL.md"],
        ["skills/prompting"],
    ),
    (
        "#128/AC-2 a line route fires on a line the change adds, with its number",
        {"agent.py": "import os\n"},
        {"agent.py": "import os\nanswer = call_model(text)\n"},
        TABLE,
        0,
        ["route  model  ->  skills/prompting/SKILL.md", "on     agent.py:2"],
        [],
    ),
    (
        "#128/AC-2 a line route does not fire on a line that was already in the file",
        {"agent.py": "answer = call_model(text)\n"},
        {"agent.py": "answer = call_model(text)\nprint(answer)\n"},
        TABLE,
        0,
        ["route  python"],
        ["route  model"],
    ),
    (
        "#128/AC-1 a contains route reads the whole file, not only the added lines",
        {"rules/naming.md": "---\nclade: foundation\n---\nbody\n"},
        {"rules/naming.md": "---\nclade: foundation\n---\nbody\nmore\n"},
        TABLE,
        0,
        ["route  framed", "on     rules/naming.md"],
        [],
    ),
    (
        "#128/AC-1 a contains route stays quiet on a file that lacks the text",
        {},
        {"notes/naming.md": "body\n"},
        TABLE,
        0,
        ["unrouted  notes/naming.md"],
        ["route  framed"],
    ),
    (
        "#128/AC-3 a path only the baseline reaches is printed as unrouted",
        {},
        {"Makefile": "all:\n"},
        TABLE,
        0,
        ["route  sweep", "unrouted  Makefile"],
        ["route  python"],
    ),
    (
        "#128/AC-3 a routed path is not printed as unrouted",
        {},
        {"a.py": "x = 1\n"},
        TABLE,
        0,
        ["route  python"],
        ["unrouted"],
    ),
    (
        "#128/AC-4 a generated path selects no route, the baseline included",
        {},
        {"dist/bundle.py": "x = 1\n", "poetry.lock": "x\n", "web/app.min.js": "x\n"},
        TABLE,
        0,
        ["ignored   dist/bundle.py", "ignored   poetry.lock", "ignored   web/app.min.js", "skills: none"],
        ["route  "],
    ),
    (
        "#128/AC-1 a deleted file fires a path route and no line route",
        {"old.py": "answer = call_model(text)\n"},
        {"old.py": None},
        TABLE,
        0,
        ["route  python", "old.py (deleted)"],
        ["route  model"],
    ),
    (
        "#128/AC-5 an invalid regular expression exits 2 and names the route",
        {},
        {"a.py": "x = 1\n"},
        {"routes": [{"id": "broken", "skill": "s", "paths": ["("]}]},
        2,
        ["route 'broken'", "invalid regular expression"],
        [],
    ),
    (
        "#128/AC-5 an unknown key exits 2 and names the route",
        {},
        {"a.py": "x = 1\n"},
        {"routes": [{"id": "typo", "skill": "s", "path": ["a"]}]},
        2,
        ["route 'typo'", "unknown key path"],
        [],
    ),
    (
        "#128/AC-5 a route with no driver exits 2 and names the route",
        {},
        {"a.py": "x = 1\n"},
        {"routes": [{"id": "idle", "skill": "s"}]},
        2,
        ["route 'idle'", "no driver"],
        [],
    ),
    (
        "#128/AC-5 an id declared twice exits 2",
        {},
        {"a.py": "x = 1\n"},
        {"routes": [{"id": "one", "skill": "s", "paths": ["a"]}, {"id": "one", "skill": "s", "paths": ["b"]}]},
        2,
        ["route 'one'", "declared twice"],
        [],
    ),
    (
        "#128/AC-1 the shipped table sends a model call to security and to prompts",
        {},
        {"svc/agent.py": 'SYSTEM_PROMPT = "You are a billing assistant"\nclient = anthropic.Anthropic()\n'},
        None,
        0,
        ["route  language-models  ->  ahrena-engineering-security:skills/reviewing-model-use/SKILL.md", "route  prompts-in-code", "route  source"],
        ["route  framework-artifacts", "route  contract"],
    ),
    (
        "#128/AC-1 the shipped table sends a framework agent to the foundation's review and a plain one not",
        {},
        {
            "plugin/agents/argos.md": "---\nname: argos\nclade: engineering\n---\n",
            ".claude/agents/helper.md": "---\nname: helper\n---\n",
        },
        None,
        0,
        ["route  framework-artifacts  ->  ahrena-foundation:skills/reviewing-artifacts/SKILL.md\n  on     plugin/agents/argos.md\nskills:"],
        [],
    ),
    (
        "#128/AC-1 the shipped table keeps a plain source change away from the prompt and model routes",
        {},
        {"lib/money.py": "def add(a, b):\n    return a + b\n"},
        None,
        0,
        ["route  source", "route  python", "route  secrets"],
        ["route  language-models", "reviewing-prompts", "route  untrusted-input", "route  access"],
    ),
]


def problems_for(expect: int, present: list[str], absent: list[str], code: int, output: str) -> list[str]:
    problems = []
    if code != expect:
        problems.append(f"exit code {code}, expected {expect}")
    problems += [f"missing from output: {text!r}" for text in present if text not in output]
    problems += [f"present in output: {text!r}" for text in absent if text in output]
    return problems


def missing_from_shipped_table() -> list[str]:
    """#128/AC-6: every skill and every file the shipped table names exists in the tree."""
    plugins = {p["name"]: ROOT / p["source"]["path"] for p in json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())["plugins"]}
    missing = []
    for route in json.loads(SHIPPED.read_text(encoding="utf-8"))["routes"]:
        for name in [route["skill"], *route.get("opens", [])]:
            owner, sep, path = name.partition(":")
            target = plugins.get(owner, ROOT / owner) / path if sep else PLUGIN / name
            if not target.is_file():
                missing.append(f"route '{route['id']}' names {name}, which does not exist")
    return missing


def main() -> int:
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for number, (name, base, head, table, expect, present, absent) in enumerate(CASES):
            repo = Path(tmp) / f"case-{number}"
            scratch(repo, base, head)
            code, output = run(repo, table)
            problems = problems_for(expect, present, absent, code, output)
            failed += report(name, problems, output)
    failed += report("#128/AC-6 every skill and file the shipped table names exists", missing_from_shipped_table(), "")

    total = len(CASES) + 1
    print()
    if failed:
        print(f"{failed} of {total} cases failed.")
        return 1
    print(f"{total} cases passed.")
    return 0


def report(name: str, problems: list[str], output: str) -> int:
    if not problems:
        print(f"ok    {name}")
        return 0
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    for line in output.splitlines():
        print(f"      {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
