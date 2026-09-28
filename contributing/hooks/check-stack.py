#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/stacked-pull-requests.md.

Decides the three conditions the rule states:

    1. a pull request based off trunk belongs to a GitHub stack
    2. that stack is based on trunk
    3. no commit in the pull request already landed with another pull request

A stack is GitHub's own object, the `stack` field of a pull request, made with
`gh stack` or on github.com (ADR-008). All three conditions read the forge, so
without a token they are reported unchecked rather than failed.

Usage:
    python3 contributing/hooks/check-stack.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. An event that carries no pull request has nothing to decide.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, run_on_pull_request  # noqa: E402

RULE = "stacked-pull-requests"

# GitHub caps a pull request's commit list at 250, in pages of 100.
COMMIT_PAGES = 3

STACK_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      stack { number baseRefName }
    }
  }
}
"""


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


def stack_of(pr: PullRequest, forge: Forge) -> dict | None:
    """The GitHub stack this pull request is an entry of, or None."""
    owner, _, name = pr.repository.partition("/")
    data = forge.graphql(STACK_QUERY, {"owner": owner, "name": name, "number": pr.number})
    return data["repository"]["pullRequest"]["stack"]


def stack_failures(pr: PullRequest, stack: dict | None) -> list[Finding]:
    if stack is None:
        if pr.base == pr.trunk:
            return []
        return [
            Finding(
                RULE,
                1,
                pr.where,
                f"its base is {pr.base}, not {pr.trunk}, and it is in no GitHub stack. If it is a layer, "
                "put the layers in a stack with `gh stack link <bottom> ... <top>`; if not, its base is wrong",
            )
        ]
    if stack.get("baseRefName") != pr.trunk:
        return [
            Finding(
                RULE,
                2,
                pr.where,
                f"its stack #{stack.get('number')} is based on {stack.get('baseRefName')}, not {pr.trunk}, "
                "so merging the stack lands nothing on trunk",
            )
        ]
    return []


def in_a_stack_on_trunk(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    try:
        stack = stack_of(pr, forge)
    except Unreachable as error:
        return [], [Unchecked(RULE, n, str(error)) for n in (1, 2)]
    return stack_failures(pr, stack), []


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
            f"({', '.join(shas)}). `gh stack sync` rebases a stack's layers past them; a branch "
            f"outside a stack is rebased onto {pr.trunk} by hand",
        )
        for number, shas in carried.items()
    ], []


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    findings: list[Finding] = []
    unchecked: list[Unchecked] = []
    for condition in (in_a_stack_on_trunk, carries_no_landed_commit):
        found, skipped = condition(pr, forge)
        findings.extend(found)
        unchecked.extend(skipped)
    return findings, unchecked


def main(argv: list[str]) -> int:
    return run_on_pull_request(argv, from_event, judge)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
