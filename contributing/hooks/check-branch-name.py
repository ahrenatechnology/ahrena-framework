#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/branch-naming.md.

Decides both conditions the rule states:

    1. the name is a type, a slash, an issue number, a hyphen and a slug
    2. the type is one of the eleven conventional types

The hook judges names, not repositories. Each argument is a branch name; with
no argument it asks git for the branch the working copy is on, which is what a
pre-push hook has and what a person running it by hand wants.

Standard library only, and git is consulted only for that default. The rule's
subject is a git ref, so requiring git is not a dependency the way a parser
would be: without git there is no branch to name.

Usage:
    python3 contributing/hooks/check-branch-name.py [branch ...]
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass

RULE = "branch-naming"

# The eleven types in @commitlint/config-conventional's type-enum, which is the
# list the Conventional Commits specification points at for everything beyond
# feat and fix. Inherited whole and not narrowed to the five this repository
# has used: closing the set at the five in use would reject `fix` the first
# time somebody fixes a bug, which is a gate failing on correct work.
TYPES = (
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
)

# A type token, a slash, a decimal issue number with no leading zero, a hyphen
# and a kebab-case slug. The type is matched loosely so that a wrong type
# reaches condition 2 with its own message instead of collapsing into "the
# shape is wrong".
BRANCH = re.compile(r"^(?P<type>[A-Za-z]+)/(?P<issue>[1-9][0-9]*)-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")

SHAPE = "type/issue-slug, as in feat/38-branch-and-commit-rules"

# Names the rule does not reach. `main` and `master` are trunk and receive code
# through a merge rather than being worked on; `release/` is the same by
# convention; `HEAD` is what git answers with in a detached checkout, where
# there is no branch name to judge. Nothing here says trunk may be committed to
# — that is a separate rule and this plugin does not carry it yet.
OUTSIDE_EXACT = frozenset({"main", "master", "HEAD"})
OUTSIDE_PREFIX = "release/"


@dataclass
class Finding:
    where: str  # the branch name, which is the whole subject
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


def outside(name: str) -> bool:
    """True when the name is not a working branch, so the rule has nothing to decide."""
    return name in OUTSIDE_EXACT or name.startswith(OUTSIDE_PREFIX)


def judge(name: str) -> list[Finding]:
    """Every condition this name fails, in condition order."""
    match = BRANCH.match(name)
    if match is None:
        return [
            Finding(
                name,
                1,
                f"the name is not {SHAPE}. The issue number is the part that is "
                "usually missing, and it is the part that ties the branch to the "
                "work it answers; the slug is lowercase, digits and single hyphens",
            )
        ]
    kind = match.group("type")
    if kind not in TYPES:
        return [
            Finding(
                name,
                2,
                f"'{kind}' is not one of the eleven conventional types "
                f"({', '.join(TYPES)})",
            )
        ]
    return []


def current_branch() -> str:
    """The branch the working copy is on, as git reports it."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot read the current branch: {result.stderr.strip()}")
    return result.stdout.strip()


def report(findings: list[Finding], judged: int) -> int:
    for finding in findings:
        print(finding)
    print(f"{judged} branch name(s), {len(findings)} failure(s).")
    return 1 if findings else 0


def main(argv: list[str]) -> int:
    names = argv[1:] or [current_branch()]
    findings: list[Finding] = []
    judged = 0
    for name in names:
        if outside(name):
            print(f"{name}: not a working branch, nothing to decide.")
            continue
        judged += 1
        findings.extend(judge(name))
    return report(findings, judged)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
