#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/concurrent-decision-records.md.

Decides the two conditions the rule states:

    1. a decision-record number this pull request introduces is not already on trunk
    2. a decision-record number this pull request introduces is not also introduced
       by another open pull request

This is the collision `check-decision-records.py` cannot see. That hook reads
one tree, so a number two branches both take passes on each branch alone and
surfaces only once both reach one tree, at rebase or at land. Here the forge is
read instead: the numbers this pull request adds, against the numbers trunk
already carries and against the numbers every other open pull request adds. All
of it is the forge's state rather than the tree's, so without a token both
conditions are reported unchecked rather than failed, per the forge tier the
repository's ADR-002 records.

Each finding names the fix, the renumber script
`contributing/skills/writing-decision-records/scripts/renumber-decision-record.py`,
which moves the losing record to the next free number. The correction is a
concrete instruction, so Erodos applies it under the applying-fixes model.

Usage:
    python3 contributing/hooks/check-decision-records-numbers.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. An event that carries no pull request has nothing to decide.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, run_on_pull_request  # noqa: E402

RULE = "concurrent-decision-records"

# Where the records live, matching contributing/rules/decision-records.md. The
# path is fixed here rather than taken as an argument, because the forge is
# asked for a path and not handed a directory to walk.
ADR_DIR = "docs/adr"

# The same shape decision-records.md condition 1 states: ADR-, three digits, a
# hyphen, a kebab-case slug. Anchored to the directory so a file of that name
# elsewhere in the diff is not read as a record.
RECORD = re.compile(rf"^{re.escape(ADR_DIR)}/ADR-(\d{{3}})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# GitHub caps a pull request's file list and the repository's open list at 100
# per page. A decision log that needed more than this many pages of either is
# not the collision this hook exists for.
PAGES = 3

RENUMBER = "contributing/skills/writing-decision-records/scripts/renumber-decision-record.py"


@dataclass(frozen=True)
class PullRequest:
    number: int
    trunk: str
    repository: str

    @property
    def where(self) -> str:
        return f"pull request #{self.number}"


def from_event(event: dict) -> PullRequest | None:
    pull = event.get("pull_request")
    if not isinstance(pull, dict):
        return None
    repository = event.get("repository") or {}
    return PullRequest(
        int(pull["number"]),
        repository.get("default_branch") or "main",
        repository.get("full_name") or "",
    )


def introduced_by(number: int, forge: Forge) -> dict[int, str]:
    """The record numbers a pull request adds, each mapped to its file.

    A pull request's files are its diff against its base, so a layer stacked on
    another never shows the record its base introduced — only its own. `added`
    is a new record; `renamed` is a record already moved to a new number, which
    this hook reads at its new one.
    """
    found: dict[int, str] = {}
    for page in range(1, PAGES + 1):
        batch = forge.get(f"pulls/{number}/files?per_page=100&page={page}") or []
        for entry in batch:
            if entry.get("status") not in ("added", "renamed"):
                continue
            match = RECORD.match(entry.get("filename") or "")
            if match is not None:
                found.setdefault(int(match.group(1)), entry["filename"])
        if len(batch) < 100:
            break
    return found


def numbers_on_trunk(pr: PullRequest, forge: Forge) -> set[int]:
    """Every record number the directory carries on the default branch."""
    listing = forge.get(f"contents/{ADR_DIR}?ref={pr.trunk}") or []
    numbers: set[int] = set()
    for entry in listing if isinstance(listing, list) else []:
        match = RECORD.match(f"{ADR_DIR}/{entry.get('name')}")
        if match is not None:
            numbers.add(int(match.group(1)))
    return numbers


def other_open_pulls(pr: PullRequest, forge: Forge) -> list[int]:
    """The numbers of every open pull request but this one."""
    numbers: list[int] = []
    for page in range(1, PAGES + 1):
        batch = forge.get(f"pulls?state=open&per_page=100&page={page}") or []
        numbers.extend(p["number"] for p in batch if p.get("number") != pr.number)
        if len(batch) < 100:
            break
    return numbers


def against_trunk(pr: PullRequest, mine: dict, forge: Forge) -> list[Finding]:
    on_trunk = numbers_on_trunk(pr, forge)
    return [
        Finding(
            RULE,
            1,
            pr.where,
            f"ADR-{number:03d} already exists on trunk ({pr.trunk}), so {mine[number]} collides once it lands. "
            f"Renumber it to the next free number: python3 {RENUMBER} {mine[number]}",
        )
        for number in sorted(set(mine) & on_trunk)
    ]


def against_other_pulls(pr: PullRequest, mine: dict, forge: Forge) -> list[Finding]:
    findings: list[Finding] = []
    for other in other_open_pulls(pr, forge):
        clash = sorted(set(mine) & set(introduced_by(other, forge)))
        findings.extend(
            Finding(
                RULE,
                2,
                pr.where,
                f"ADR-{number:03d} is also introduced by #{other}, so whichever lands second collides. "
                f"Renumber this one to the next free number: python3 {RENUMBER} {mine[number]}",
            )
            for number in clash
        )
    return findings


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    try:
        mine = introduced_by(pr.number, forge)
        if not mine:
            return [], []
        return against_trunk(pr, mine, forge) + against_other_pulls(pr, mine, forge), []
    except Unreachable as error:
        return [], [Unchecked(RULE, n, str(error)) for n in (1, 2)]


def main(argv: list[str]) -> int:
    return run_on_pull_request(argv, from_event, judge)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
