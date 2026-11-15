#!/usr/bin/env python3
"""The scorecard runner: every registered detector, run over one change.

A detector is a script that decides a condition and prints its failures. This
runner is the one place they run together and become a scorecard, so that the
verdict on a condition is the detector's and not a reviewer's reading. It takes
a base and a head, runs every detector in the registry over the head (and over
the merge base when a ratchet needs it), and writes JSON: per condition id,
passed or failed, eliminatory or indicator, with the file and line of each
failure.

The registry, `scorecard-detectors.json` beside this file, is the contract. A
detector names its script and its languages, and lists one entry per condition
it decides: the condition id of the catalogue, the `rule` and `number` the
detector prints for it, `kind`, `scope`, `threshold`, where the threshold comes
from, and a pair of fixtures, a `clean` tree the detector must pass and a
`planted` tree whose violation it must report. `--fixtures` runs every pair and
fails when a detector reports its clean tree or passes its planted one; a
detector nobody proved is a script someone may or may not trust.

`scope` is the ratchet. `added`: only a failure on a line the change adds counts
(a failure with no line counts when the file is new), and the condition fails
when more than `threshold` of them are found. `total`: the whole tree counts,
and the condition fails only when the head has more failures than the merge base
(or than `threshold`, when that is higher), so legacy never blocks and getting
worse always does. `kind` says whether a failure blocks the merge
(`eliminatory`) or only appears on the card (`indicator`); the exit code follows
the eliminatory ones.

A detector is run the way the plugins' own suites run it: as a subprocess, with
the tree as its working directory and `.` as its argument, and its output is read
back in the format every hook here prints. A detector that crashes, or fails with
nothing the runner can read, or prints a condition the registry does not name, is
an error and exits 2, never a quiet pass.

Usage:
    python3 engineering/fundamentals/hooks/scorecard.py --base <rev> --head <rev> [--out FILE]
    python3 engineering/fundamentals/hooks/scorecard.py --fixtures
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tarfile  # noqa: E402
import tempfile  # noqa: E402
from collections import Counter  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402

from changes import PINNED, Unavailable, added_lines, git  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
REGISTRY = HERE / "scorecard-detectors.json"

KINDS = ("eliminatory", "indicator")
SCOPES = ("added", "total")
SOURCE = re.compile(r"^(measured|inherited|policy):\S")

FAILURE = re.compile(r"^\s+\[([^\]]+)\] condition (\d+): (.*)$")
SUMMARY = re.compile(r"^\d+ (failure|file)\(s\)")
LINED = re.compile(r"^(.+?):(\d+)$")


@dataclass(frozen=True)
class Failure:
    rule: str
    number: int
    file: str
    line: int | None
    message: str

    def key(self) -> tuple[str, int, str, str]:
        return (self.rule, self.number, self.file, self.message)


@dataclass(frozen=True)
class Entry:
    id: str
    condition: str
    detector: Path
    languages: tuple[str, ...]
    rule: str
    number: int
    kind: str
    scope: str
    threshold: int
    source: str
    clean: Path
    planted: Path


def load_registry(path: Path) -> list[Entry]:
    """The entries of the registry, validated; a malformed one is an error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [entry for detector in data["detectors"] for entry in entries_of(detector)]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Unavailable(f"the registry {path} cannot be read: {error!r}") from error


def entries_of(detector: dict) -> list[Entry]:
    script = (ROOT / detector["path"]).resolve()
    if not script.is_file():
        raise Unavailable(f"the registry names {detector['path']}, which does not exist")
    return [entry_of(detector, condition, script) for condition in detector["conditions"]]


def entry_of(detector: dict, spec: dict, script: Path) -> Entry:
    entry = Entry(
        id=spec["id"],
        condition=spec["condition"],
        detector=script,
        languages=tuple(detector["languages"]),
        rule=spec["rule"],
        number=int(spec["number"]),
        kind=spec["kind"],
        scope=spec["scope"],
        threshold=int(spec["threshold"]),
        source=spec["threshold_source"],
        clean=(ROOT / spec["fixtures"]["clean"]).resolve(),
        planted=(ROOT / spec["fixtures"]["planted"]).resolve(),
    )
    problem = contract_problem(entry)
    if problem:
        raise Unavailable(f"registry entry {entry.id}: {problem}")
    return entry


def contract_problem(entry: Entry) -> str:
    """What breaks the detector contract for this entry, or an empty string."""
    if entry.kind not in KINDS:
        return f"kind must be one of {KINDS}, not {entry.kind!r}"
    if entry.scope not in SCOPES:
        return f"scope must be one of {SCOPES}, not {entry.scope!r}"
    if entry.threshold < 0 or not SOURCE.match(entry.source):
        return "threshold must be >= 0 and its source measured:, inherited: or policy: followed by where"
    missing = [str(path) for path in (entry.clean, entry.planted) if not path.is_dir()]
    return f"fixtures missing: {', '.join(missing)}" if missing else ""


def run_detector(script: Path, tree: Path) -> list[Failure]:
    """What the detector reports over a tree; an unreadable answer is an error."""
    done = subprocess.run([sys.executable, "-B", str(script), "."], cwd=tree, capture_output=True, text=True)
    if done.returncode not in (0, 1):
        raise Unavailable(f"{script.name} exited {done.returncode} over {tree}: {done.stderr.strip() or done.stdout.strip()}")
    found = parse(done.stdout)
    if (done.returncode == 1) != bool(found):
        raise Unavailable(f"{script.name} exited {done.returncode} but printed {len(found)} failure(s) the runner can read")
    return found


def parse(output: str) -> list[Failure]:
    found: list[Failure] = []
    where = ""
    for row in output.splitlines():
        match = FAILURE.match(row)
        if match:
            found.append(failure_at(where, match))
        elif row and not row[0].isspace() and not SUMMARY.match(row):
            where = row
    return found


def failure_at(where: str, match: re.Match[str]) -> Failure:
    lined = LINED.match(where)
    file, line = (lined.group(1), int(lined.group(2))) if lined else (where, None)
    return Failure(match.group(1), int(match.group(2)), file, line, match.group(3))


def export(top: Path, rev: str, into: Path) -> None:
    """The tree of a revision, written under `into`."""
    packer = subprocess.Popen(["git", "archive", "--format=tar", rev], cwd=top, stdout=subprocess.PIPE)
    assert packer.stdout is not None
    with tarfile.open(fileobj=packer.stdout, mode="r|") as archive:
        archive.extractall(into, filter="data") if hasattr(tarfile, "data_filter") else archive.extractall(into)
    if packer.wait() != 0:
        raise Unavailable(f"git could not export {rev}")


def counts_as_added(failure: Failure, added: dict[str, set[int]]) -> bool:
    lines = added.get(failure.file)
    if lines is None:
        return False
    return failure.line in lines if failure.line is not None else 0 in lines


def fresh_since(head: list[Failure], base: list[Failure]) -> list[Failure]:
    """The head's failures the base did not already have, one for one."""
    seen = Counter(failure.key() for failure in base)
    fresh = []
    for failure in head:
        if seen[failure.key()] > 0:
            seen[failure.key()] -= 1
        else:
            fresh.append(failure)
    return fresh


class Change:
    """The two trees and the added lines of one base and head, built on demand."""

    def __init__(self, top: Path, base: str, head: str) -> None:
        self.top = top
        self.head = git(["rev-parse", "--verify", f"{head}^{{commit}}"], top).strip()
        self.merge_base = git(["merge-base", base, self.head], top).strip()
        self._dir = tempfile.TemporaryDirectory()
        self._trees: dict[str, Path] = {}
        self._runs: dict[tuple[Path, str], list[Failure]] = {}
        self.added = self._added()
        self.skip: tuple[str, ...] = ()

    def _added(self) -> dict[str, set[int]]:
        diff = git(["-c", "color.ui=false", "diff", f"{self.merge_base}..{self.head}", *PINNED], self.top)
        added = {str(path.relative_to(self.top)): set(lines) for path, lines in added_lines(diff, self.top).items()}
        names = git(["diff", f"{self.merge_base}..{self.head}", "--name-only", "-z", "--diff-filter=AR"], self.top)
        for name in filter(None, names.split("\0")):
            added.setdefault(name, set()).add(0)
        return added

    def tree(self, label: str) -> Path:
        if label not in self._trees:
            into = Path(self._dir.name) / label
            into.mkdir()
            export(self.top, self.head if label == "head" else self.merge_base, into)
            self._trees[label] = into
        return self._trees[label]

    def failures(self, script: Path, label: str) -> list[Failure]:
        if (script, label) not in self._runs:
            self._runs[(script, label)] = run_detector(script, self.tree(label))
        return self._runs[(script, label)]


def judge(entry: Entry, change: Change) -> tuple[list[Failure], dict[str, int]]:
    """The failures that count for this entry on this change, and the numbers behind them."""
    mine = [f for f in change.failures(entry.detector, "head") if (f.rule, f.number) == (entry.rule, entry.number) and not under(f.file, change.skip)]
    if entry.scope == "added":
        counted = [f for f in mine if counts_as_added(f, change.added)]
        return (counted if len(counted) > entry.threshold else []), {"count": len(counted)}
    base = [f for f in change.failures(entry.detector, "base") if (f.rule, f.number) == (entry.rule, entry.number) and not under(f.file, change.skip)]
    worse = len(mine) > max(len(base), entry.threshold)
    return (fresh_since(mine, base) if worse else []), {"count": len(mine), "base_count": len(base)}


def under(file: str, prefixes: tuple[str, ...]) -> bool:
    return any(file.startswith(prefix) for prefix in prefixes)


def fixture_prefixes(entries: list[Entry], top: Path) -> tuple[str, ...]:
    """The registered fixture trees, as paths in the repository: their planted defects are the proof, not the change."""
    return tuple(f"{path.relative_to(top)}/" for e in entries for path in (e.clean, e.planted) if path.is_relative_to(top))


def unregistered(entries: list[Entry], change: Change) -> None:
    """A detector printing a condition no entry names is an error."""
    named = {(e.detector, e.rule, e.number) for e in entries}
    for script in {e.detector for e in entries}:
        for failure in change.failures(script, "head"):
            if (script, failure.rule, failure.number) not in named:
                raise Unavailable(f"{script.name} reported [{failure.rule}] condition {failure.number}, which the registry does not name")


def scorecard(entries: list[Entry], change: Change, base: str) -> dict:
    unregistered(entries, change)
    change.skip = fixture_prefixes(entries, change.top)
    conditions: dict[str, dict] = {}
    for entry in entries:
        failures, numbers = judge(entry, change)
        card = conditions.setdefault(entry.condition, {"kind": entry.kind, "status": "passed", "languages": [], "entries": [], "failures": []})
        if card["kind"] != entry.kind:
            raise Unavailable(f"condition {entry.condition} is both eliminatory and indicator in the registry")
        card["languages"] = sorted(set(card["languages"]) | set(entry.languages))
        card["entries"].append({"id": entry.id, "scope": entry.scope, "threshold": entry.threshold, "threshold_source": entry.source, **numbers})
        card["failures"].extend({"entry": entry.id, "file": f.file, "line": f.line, "message": f.message} for f in failures)
        card["status"] = "failed" if card["failures"] else "passed"
    return {"schema": 1, "base": base, "merge_base": change.merge_base, "head": change.head, "conditions": dict(sorted(conditions.items())), "summary": summary(conditions)}


def summary(conditions: dict[str, dict]) -> dict:
    failed = {kind: sorted(c for c, card in conditions.items() if card["kind"] == kind and card["status"] == "failed") for kind in KINDS}
    return {"conditions": len(conditions), "eliminatory_failed": failed["eliminatory"], "indicator_failed": failed["indicator"]}


def check_fixtures(entries: list[Entry]) -> int:
    """Run every clean and planted pair; the exit code is the number of bad detectors, capped at 1."""
    bad = 0
    for entry in entries:
        problems = fixture_problems(entry)
        bad += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '}  {entry.id}")
        for problem in problems:
            print(f"        {problem}")
    print(f"\n{bad} of {len(entries)} detector fixtures failed." if bad else f"\n{len(entries)} detector fixtures passed.")
    return int(bool(bad))


def fixture_problems(entry: Entry) -> list[str]:
    problems = []
    clean = run_detector(entry.detector, entry.clean)
    if clean:
        problems.append(f"flags its clean fixture: {clean[0].file} [{clean[0].rule}] condition {clean[0].number}")
    planted = run_detector(entry.detector, entry.planted)
    if not any((f.rule, f.number) == (entry.rule, entry.number) for f in planted):
        problems.append(f"passes its planted fixture: [{entry.rule}] condition {entry.number} was not reported")
    return problems


def write_card(card: dict, out: str | None) -> None:
    text = json.dumps(card, indent=2) + "\n"
    if out:
        Path(out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    for cid in card["summary"]["eliminatory_failed"]:
        print(f"eliminatory condition failed: {cid}", file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--out")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--registry", default=str(REGISTRY))
    parser.add_argument("--fixtures", action="store_true")
    args = parser.parse_args(argv[1:])
    try:
        entries = load_registry(Path(args.registry))
        if args.fixtures:
            return check_fixtures(entries)
        if not (args.base and args.head):
            parser.error("--base and --head are required unless --fixtures is given")
        top = Path(git(["rev-parse", "--show-toplevel"], Path(args.repo).resolve()).strip()).resolve()
        card = scorecard(entries, Change(top, args.base, args.head), args.base)
    except Unavailable as error:
        print(f"scorecard: {error}", file=sys.stderr)
        return 2
    write_card(card, args.out)
    return 1 if card["summary"]["eliminatory_failed"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
