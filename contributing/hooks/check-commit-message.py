#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/commit-format.md.

Decides all six conditions the rule states:

    1. the subject parses as Conventional Commits
    2. the type is one of the eleven conventional types
    3. the subject is at most 72 characters
    4. the subject does not end in a period
    5. a body is separated from the subject by one blank line
    6. the commit object carries a signature header

Each argument is passed to `git rev-list` verbatim, so a range works
(`origin/main..HEAD`) and so does a list of revisions. With no argument the
hook judges the commit at HEAD and nothing behind it, which is what somebody
who has just committed wants.

The commit is read with `git cat-file commit`, which hands back the object as
it is stored: the headers first, then a blank line, then the message. That one
call answers conditions 1 to 5 from the message and condition 6 from the
headers, so the shape of a message and the presence of a signature are decided
on the same bytes and cannot disagree.

Standard library only, and git is the subject rather than a dependency: the
conditions are about commit objects, which do not exist without it.

Usage:
    python3 contributing/hooks/check-commit-message.py [revision ...]
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass

RULE = "commit-format"

# The eleven types in @commitlint/config-conventional's type-enum. The same set
# condition 2 of contributing/rules/branch-naming.md takes, inherited from the
# same place for the same reason, so a branch and the commits on it cannot be
# typed from two different vocabularies.
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

# `git log` indents every line of the message by four spaces, so a subject of
# 72 characters is the longest one that still fits a default 80-column terminal
# without wrapping. Inherited from that arithmetic, by way of the predecessor
# framework's codex-commit-standards, which stated 72 without deriving it. Not
# raised to the 76 this repository's longest subject reaches:
# docs/contribution-flow.md carries the distribution and the argument.
SUBJECT_MAX = 72

# Conventional Commits v1.0.0: a type, an optional parenthesised scope, an
# optional `!` for a breaking change, then a colon, one space, and a
# description that is not blank. The type is matched loosely so that a wrong
# type reaches condition 2 with its own message instead of collapsing into
# "the shape is wrong".
SUBJECT = re.compile(r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^()\n]+)\))?!?: (?P<description>\S.*)$")

# Every signature git writes is a header whose name begins `gpgsig`: `gpgsig`
# for the object's own hash algorithm, `gpgsig-sha256` in a repository that
# stores both. The payload may be OpenPGP, SSH or X.509 and this condition does
# not read it.
SIGNATURE_HEADER = "gpgsig"

PARENT_HEADER = "parent "

TYPE_LIST = ", ".join(TYPES)


@dataclass
class Finding:
    where: str  # the commit sha
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


@dataclass
class Commit:
    sha: str
    header: str  # everything before the blank line, as stored
    message: str


def git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def read(sha: str) -> Commit:
    """One commit object, split at the blank line that ends its headers.

    A signature's continuation lines are indented by one space, and git writes
    a lone space for a blank line inside the payload, so the first empty line
    in the object is always the end of the headers.
    """
    header, _, message = git(["cat-file", "commit", sha]).partition("\n\n")
    return Commit(sha, header, message)


def header_lines(commit: Commit, prefix: str) -> list[str]:
    return [line for line in commit.header.split("\n") if line.startswith(prefix)]


def subject_failures(subject: str) -> list[tuple[int, str]]:
    """Conditions 1 to 4, which all read the first line and nothing else."""
    failures: list[tuple[int, str]] = []
    match = SUBJECT.match(subject)
    if match is None:
        failures.append(
            (
                1,
                f"the subject {subject!r} is not 'type(scope): description'. The "
                "scope and its parentheses are optional; the colon and the single "
                "space after it are not",
            )
        )
    elif match.group("type") not in TYPES:
        failures.append(
            (2, f"'{match.group('type')}' is not one of the eleven conventional types ({TYPE_LIST})")
        )
    if len(subject) > SUBJECT_MAX:
        failures.append(
            (
                3,
                f"the subject is {len(subject)} characters, over the {SUBJECT_MAX} "
                "that fit a `git log` line in an 80-column terminal",
            )
        )
    if subject.endswith("."):
        failures.append((4, "the subject ends in a period; it is a title rather than a sentence"))
    return failures


def judge(commit: Commit) -> list[Finding]:
    """Every condition this commit fails, in condition order."""
    lines = commit.message.split("\n")
    findings = [Finding(commit.sha, n, m) for n, m in subject_failures(lines[0])]
    if len(lines) > 1 and lines[1].strip():
        findings.append(
            Finding(
                commit.sha,
                5,
                "the line after the subject is not blank, so the message reads as "
                "one paragraph and every tool that splits subject from body splits "
                "it in the wrong place",
            )
        )
    if not header_lines(commit, SIGNATURE_HEADER):
        findings.append(
            Finding(
                commit.sha,
                6,
                "the commit object carries no signature header. Configure a signing "
                "key and `commit.gpgsign true`, and note that a squash or rebase "
                "merge re-authors the commit and drops the signature it arrived with",
            )
        )
    return findings


def report(findings: list[Finding], judged: int, skipped: int) -> int:
    for finding in findings:
        print(finding)
    tail = f", {skipped} merge commit(s) skipped" if skipped else ""
    print(f"{judged} commit(s), {len(findings)} failure(s){tail}.")
    return 1 if findings else 0


def main(argv: list[str]) -> int:
    findings: list[Finding] = []
    judged = 0
    skipped = 0
    for sha in git(["rev-list", *(argv[1:] or ["--no-walk", "HEAD"])]).split():
        commit = read(sha)
        # A merge commit's message is written by whatever performed the merge,
        # so the rule does not reach it, and the merge carries no change of its
        # own to describe.
        if len(header_lines(commit, PARENT_HEADER)) > 1:
            skipped += 1
            continue
        judged += 1
        findings.extend(judge(commit))
    return report(findings, judged, skipped)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
