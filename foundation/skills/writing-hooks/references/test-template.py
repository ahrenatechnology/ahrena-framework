#!/usr/bin/env python3
"""Tests for <name>.py.

A gate that has never rejected anything is a claim, not a guardrail.

The hook runs as a subprocess on purpose: that is what CI runs, exit code
included. Importing the function under test would skip the part that decides
whether the build goes red.

Usage:
    python3 <plugin>/hooks/test-<name>.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "<name>.py"

# The smallest input that satisfies every condition. Each failing case below is
# this, with exactly one thing broken, so a case can only fail for its reason.
GOOD = """<minimal passing content>"""


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> tuple:
    return (name, files, expect, ok)


CASES = [
    case("a valid subject passes", {"<path>": GOOD}, ["no failures"], ok=True),
    case(
        "<condition 1> fails",
        {"<path>": GOOD.replace("<the good part>", "<the broken part>")},
        ["<the fragment the message must contain>"],
    ),
    # A limit you are choosing to leave open is pinned here with ok=True and a
    # comment saying why, so nobody reads it as an oversight and "fixes" it.
]


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(HOOK), str(root)], capture_output=True, text=True
        )
        return result.returncode, result.stdout + result.stderr


def main() -> int:
    failed = 0
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = []
        if ok and code != 0:
            problems.append("expected the hook to pass, it failed")
        if not ok and code == 0:
            problems.append("expected the hook to fail, it passed")
        for fragment in expect:
            if fragment not in output:
                problems.append(f"expected {fragment!r} in the output")
        if problems:
            failed += 1
            print(f"FAIL  {name}")
            for problem in problems:
                print(f"        {problem}")
            print("      --- hook output ---")
            for line in output.splitlines():
                print(f"      {line}")
        else:
            print(f"ok    {name}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
