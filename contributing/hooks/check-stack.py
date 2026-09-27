#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/stacked-pull-requests.md.

Decides the three conditions the rule states:

    1. a pull request based off trunk is based on an open pull request's branch
    2. the chain of bases reaches trunk
    3. no commit in the pull request already landed with another pull request

A stack is read from the chain of base branches, which is GitHub's own
primitive and what every stacking tool produces; no tool is assumed. All three
conditions read the forge, so without a token they are reported unchecked
rather than failed.

Usage:
    python3 contributing/hooks/check-stack.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. An event that carries no pull request has nothing to decide.
"""

from __future__ import annotations

import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, from_environment, load_event, report  # noqa: E402

RULE = "stacked-pull-requests"

# GitHub caps a pull request's commit list at 250, in pages of 100.
COMMIT_PAGES = 3


@dataclass(frozen=True)
class PullRequest:
    number: int
    base: str
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
        (pull.get("base") or {}).get("ref") or "",
        repository.get("default_branch") or "main",
        repository.get("full_name") or "",
    )


def pulls_from(forge: Forge, pr: PullRequest, branch: str) -> list[dict]:
    """Every pull request in this repository whose head is `branch`, any state."""
    owner = pr.repository.partition("/")[0]
    head = urllib.parse.quote(f"{owner}:{branch}", safe="/:")
    return forge.get(f"pulls?head={head}&state=all&per_page=100") or []


def parent_failure(pr: PullRequest, parents: list[dict]) -> str | None:
    if any(p.get("state") == "open" for p in parents):
        return None
    merged = [p for p in parents if p.get("merged_at")]
    if merged:
        return (
            f"its base {pr.base} is the branch of #{merged[0]['number']}, which has already "
            f"landed. Retarget it to {pr.trunk} and restack it onto the squash"
        )
    if parents:
        return f"its base {pr.base} is the branch of #{parents[0]['number']}, which was closed without merging"
    return (
        f"its base {pr.base} is neither {pr.trunk} nor the branch of any pull request, so this "
        "is a pull request opened against the wrong base rather than a layer of a stack"
    )


def based_on_open_parent(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    if pr.base == pr.trunk:
        return [], []
    try:
        problem = parent_failure(pr, pulls_from(forge, pr, pr.base))
    except Unreachable as error:
        return [], [Unchecked(RULE, 1, str(error))]
    return ([Finding(RULE, 1, pr.where, problem)] if problem else []), []


def next_base(pr: PullRequest, forge: Forge, branch: str) -> str | None:
    """The base of the open pull request whose head is `branch`, if there is one."""
    open_parents = [p for p in pulls_from(forge, pr, branch) if p.get("state") == "open"]
    return (open_parents[0].get("base") or {}).get("ref") if open_parents else None


def chain_reaches_trunk(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    seen = [pr.base]
    try:
        while seen[-1] != pr.trunk:
            base = next_base(pr, forge, seen[-1])
            if base is None:
                return [], []  # condition 1 reports the break
            if base in seen:
                chain = " -> ".join([*seen, base])
                return [Finding(RULE, 2, pr.where, f"the chain of bases is a cycle and never reaches {pr.trunk}: {chain}")], []
            seen.append(base)
    except Unreachable as error:
        return [], [Unchecked(RULE, 2, str(error))]
    return [], []


def landed_elsewhere(pr: PullRequest, forge: Forge, sha: str) -> list[int]:
    """The merged pull requests other than this one that carried `sha`."""
    pulls = forge.get(f"commits/{sha}/pulls") or []
    return [p["number"] for p in pulls if p.get("merged_at") and p.get("number") != pr.number]


def commits_of(pr: PullRequest, forge: Forge) -> list[str]:
    shas: list[str] = []
    for page in range(1, COMMIT_PAGES + 1):
        batch = forge.get(f"pulls/{pr.number}/commits?per_page=100&page={page}") or []
        shas.extend(c["sha"] for c in batch)
        if len(batch) < 100:
            break
    return shas


def carries_no_landed_commit(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    carried: dict[int, list[str]] = {}
    try:
        for sha in commits_of(pr, forge):
            for number in landed_elsewhere(pr, forge, sha):
                carried.setdefault(number, []).append(sha[:7])
    except Unreachable as error:
        return [], [Unchecked(RULE, 3, str(error))]
    return [
        Finding(
            RULE,
            3,
            pr.where,
            f"it still carries {len(shas)} commit(s) of #{number}, which already landed as a squash "
            f"({', '.join(shas)}). Restack: rebase this branch onto {pr.trunk} past those commits",
        )
        for number, shas in carried.items()
    ], []


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    findings: list[Finding] = []
    unchecked: list[Unchecked] = []
    for condition in (based_on_open_parent, chain_reaches_trunk, carries_no_landed_commit):
        found, skipped = condition(pr, forge)
        findings.extend(found)
        unchecked.extend(skipped)
    return findings, unchecked


def main(argv: list[str]) -> int:
    pr = from_event(load_event(argv))
    if pr is None:
        print("not a pull-request event, nothing to decide.")
        return 0
    findings, unchecked = judge(pr, from_environment(pr.repository))
    return report(findings, unchecked, pr.where)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
