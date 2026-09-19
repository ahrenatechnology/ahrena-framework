#!/usr/bin/env python3
"""Tests for check-branch-name.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing name and by the name it must not flag.
Each case runs the hook as a subprocess and asserts on the exit code and the
message.

The five branch names this repository already carries are in here as cases,
because the rule changes the practice rather than describing it and the tests
are where that is visible.

Usage:
    python3 contributing/hooks/test-check-branch-name.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-branch-name.py"


def case(name: str, names: list[str], expect: list[str], ok: bool = False) -> tuple:
    return (name, names, expect, ok)


CASES = [
    case(
        "the name this rule shipped on passes",
        ["feat/38-branch-and-commit-rules"],
        ["1 branch name(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "every conventional type is accepted",
        [
            "build/1-a",
            "chore/2-a",
            "ci/3-a",
            "docs/4-a",
            "feat/5-a",
            "fix/6-a",
            "perf/7-a",
            "refactor/8-a",
            "revert/9-a",
            "style/10-a",
            "test/11-a",
        ],
        ["11 branch name(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "a single-token slug passes",
        ["fix/7-typo"],
        ["1 branch name(s), 0 failure(s)"],
        ok=True,
    ),
    # --- condition 1: the shape
    case(
        "a name with no issue number fails",
        ["feat/foundation-core"],
        ["[branch-naming] condition 1", "The issue number is the part that is usually missing"],
    ),
    case(
        "the four other branches in this repository fail the same way",
        [
            "ci/bump-actions-to-node-24",
            "docs/correctness-and-resource-discipline",
            "feat/cross-plugin-references",
            "main-3cex9i",
        ],
        ["4 branch name(s), 4 failure(s)", "[branch-naming] condition 1"],
    ),
    case(
        "a hyphen where the slash belongs fails",
        ["feat-42-oauth2"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "a leading zero on the issue number fails",
        ["feat/0042-oauth2"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "issue zero fails",
        ["feat/0-oauth2"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "an uppercase slug fails",
        ["feat/42-OAuth2"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "an empty slug fails",
        ["feat/42-"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "a doubled hyphen in the slug fails",
        ["feat/42-oauth2--client"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "an underscore in the slug fails",
        ["feat/42-oauth2_client"],
        ["[branch-naming] condition 1"],
    ),
    case(
        "a second slash fails",
        ["feat/42-oauth2/client"],
        ["[branch-naming] condition 1"],
    ),
    # --- condition 2: the type
    case(
        "a type outside the eleven fails, and says which eleven",
        ["wip/42-oauth2"],
        ["[branch-naming] condition 2", "'wip' is not one of the eleven", "build, chore, ci"],
    ),
    case(
        "a capitalised type fails condition 2 rather than condition 1",
        ["Feat/42-oauth2"],
        ["[branch-naming] condition 2", "'Feat' is not one of the eleven"],
    ),
    case(
        "a type that is a prefix of a real one fails",
        ["fea/42-oauth2"],
        ["[branch-naming] condition 2"],
    ),
    # --- names the rule does not reach
    case(
        "trunk is not a working branch",
        ["main"],
        ["main: not a working branch", "0 branch name(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "master and a release branch are not working branches either",
        ["master", "release/1.4"],
        ["0 branch name(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "a detached checkout has no branch name to judge",
        ["HEAD"],
        ["HEAD: not a working branch"],
        ok=True,
    ),
    case(
        "an exempt name beside a bad one still fails on the bad one",
        ["main", "wip/42-oauth2"],
        ["1 branch name(s), 1 failure(s)", "[branch-naming] condition 2"],
    ),
]


def run(names: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HOOK), *names], capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    found = []
    if ok and code != 0:
        found.append("expected the hook to pass, it failed")
    if not ok and code == 0:
        found.append("expected the hook to fail, it passed")
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def main() -> int:
    failed = 0
    for name, names, expect, ok in CASES:
        code, output = run(names)
        problems = problems_for(expect, ok, code, output)
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
        print("      --- hook output ---")
        for line in output.splitlines():
            print(f"      {line}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
