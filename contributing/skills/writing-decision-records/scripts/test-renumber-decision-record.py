#!/usr/bin/env python3
"""Tests for renumber-decision-record.py.

Each case builds a decision log in a temporary tree, runs the script as a
subprocess, and asserts on what moved and what did not. The two behaviours the
script exists for are pinned against #188's acceptance criteria:

    #188/AC-6 the record moves to the next free number, with its heading, its
              README row and every reference that resolves to its file
    #188/AC-7 the decision-records gate, which failed on the duplicate, passes
              on the result

Usage:
    python3 contributing/skills/writing-decision-records/scripts/test-renumber-decision-record.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "renumber-decision-record.py"
# The tree-tier gate the renumber is meant to leave green. Three directories up
# from the scripts folder is the plugin root; the hook is beside the others.
CHECK = HERE.parents[2] / "hooks" / "check-decision-records.py"


def record(number: int, slug: str, title: str) -> str:
    """A record that passes every condition of check-decision-records.py."""
    return (
        f"# ADR-{number:03d}: {title}\n\n"
        "- **Status:** accepted\n"
        "- **Date:** 2026-10-14\n\n"
        "## Context\n\nSome context.\n\n"
        "## Decision\n\nThe decision.\n\n"
        "## Consequences\n\nThe consequences.\n\n"
        "## Alternatives considered\n\n- do nothing\n"
    )


def build(root: Path) -> Path:
    """A log with a real 002 (the keeper) and a colliding 002 (the mover)."""
    adr = root / "docs" / "adr"
    adr.mkdir(parents=True)
    (root / ".git").mkdir()
    (adr / "ADR-001-first-decision.md").write_text(record(1, "first-decision", "First decision"), encoding="utf-8")
    (adr / "ADR-002-the-keeper.md").write_text(record(2, "the-keeper", "The keeper"), encoding="utf-8")
    (adr / "ADR-002-the-mover.md").write_text(record(2, "the-mover", "The mover"), encoding="utf-8")
    (adr / "README.md").write_text(
        "# The decision log\n\n| Record | Decision |\n|---|---|\n"
        "| [ADR-001](ADR-001-first-decision.md) | First decision |\n"
        "| [ADR-002](ADR-002-the-keeper.md) | The keeper |\n"
        "| [ADR-002](ADR-002-the-mover.md) | The mover |\n",
        encoding="utf-8",
    )
    (root / "docs" / "elsewhere.md").write_text(
        "The mover is [ADR-002](adr/ADR-002-the-mover.md), see also ADR-002-the-mover.\n",
        encoding="utf-8",
    )
    return adr


def run_script(record_path: Path, root: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(record_path), "--root", str(root)],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def run_gate(adr: Path) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(CHECK), str(adr)], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def problems_for(name: str, root: Path, adr: Path, code: int, output: str) -> list[str]:
    found: list[str] = []
    if code != 0:
        found.append(f"the script exited {code}: {output.strip()}")
        return found
    moved = adr / "ADR-003-the-mover.md"
    gone = adr / "ADR-002-the-mover.md"
    keeper = adr / "ADR-002-the-keeper.md"
    elsewhere = root / "docs" / "elsewhere.md"

    # #188/AC-6: the file moved to the next free number, 003.
    if gone.exists():
        found.append("the old file ADR-002-the-mover.md still exists")
    if not moved.exists():
        found.append("the record was not renamed to ADR-003-the-mover.md")
        return found
    body = moved.read_text(encoding="utf-8")
    if not body.startswith("# ADR-003: The mover"):
        found.append("the heading was not rewritten to ADR-003")
    # The README row moved, link target and visible text both.
    readme = (adr / "README.md").read_text(encoding="utf-8")
    if "ADR-002-the-mover.md" in readme:
        found.append("the README still links the old file")
    if "[ADR-003](ADR-003-the-mover.md)" not in readme:
        found.append("the README row was not moved to ADR-003 with its link")
    # The reference in another file moved, both the link and the bare stem.
    other = elsewhere.read_text(encoding="utf-8")
    if "ADR-002-the-mover" in other:
        found.append("a reference to the old file survived in docs/elsewhere.md")
    if "[ADR-003](adr/ADR-003-the-mover.md)" not in other or "ADR-003-the-mover." not in other:
        found.append("the references in docs/elsewhere.md were not moved to ADR-003")
    # The keeper is untouched: a different record that happens to share the number.
    if keeper.read_text(encoding="utf-8") != record(2, "the-keeper", "The keeper"):
        found.append("the keeper record was changed")
    return found


def case_renumber() -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        adr = build(root)
        code, output = run_script(adr / "ADR-002-the-mover.md", root)
        return problems_for("renumber", root, adr, code, output)


def case_gate_passes() -> list[str]:
    """#188/AC-7: the gate fails on the duplicate and passes after the move."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        adr = build(root)
        before, _ = run_gate(adr)
        if before == 0:
            return ["check-decision-records.py passed on the duplicate; the case proves nothing"]
        code, output = run_script(adr / "ADR-002-the-mover.md", root)
        if code != 0:
            return [f"the script exited {code}: {output.strip()}"]
        after, gate_output = run_gate(adr)
        if after != 0:
            return [f"check-decision-records.py still fails after the renumber:\n{gate_output.strip()}"]
    return []


CASES = [
    ("the record moves to the next free number, with heading, README row and references (#188/AC-6)", case_renumber),
    ("the decision-records gate fails on the duplicate and passes after the renumber (#188/AC-7)", case_gate_passes),
]


def main() -> int:
    failed = 0
    for name, run in CASES:
        problems = run()
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
