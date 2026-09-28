#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/stacked-pull-requests.md.

Decides the three conditions the rule states:

    1. a pull request based off trunk is a layer of a stack
    2. the stack lands on trunk
    3. no commit in the pull request already landed with another pull request

A stack is the forge's native stack where the forge has one, read from the
pull request's `stack` field. Where it has none, the framework runs the stack
itself, and a stack is the chain of base branches, each the branch of an open
pull request (ADR-008). Whether the forge has native stacks is read from its
schema, not assumed. All three conditions read the forge, so without a token
they are reported unchecked rather than failed.

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
from forge import Finding, Forge, Unchecked, Unreachable, run_on_pull_request  # noqa: E402

RULE = "stacked-pull-requests"

# GitHub caps a pull request's commit list at 250, in pages of 100.
COMMIT_PAGES = 3

# Null on a forge that has no native stacks: GitHub before 2026-07-30, a
# GitHub Enterprise host without the feature, or anything else that answers
# GitHub's GraphQL.
SCHEMA_QUERY = '{ __type(name: "PullRequestStack") { name } }'

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


def forge_has_stacks(forge: Forge) -> bool:
    return forge.graphql(SCHEMA_QUERY, {}).get("__type") is not None


# --- the forge's native stack


def stack_of(pr: PullRequest, forge: Forge) -> dict | None:
    """The native stack this pull request is an entry of, or None."""
    owner, _, name = pr.repository.partition("/")
    data = forge.graphql(STACK_QUERY, {"owner": owner, "name": name, "number": pr.number})
    return data["repository"]["pullRequest"]["stack"]


def native_failures(pr: PullRequest, stack: dict | None) -> list[Finding]:
    if stack is None:
        if pr.base == pr.trunk:
            return []
        return [
            Finding(
                RULE,
                1,
                pr.where,
                f"its base is {pr.base}, not {pr.trunk}, and it is in no stack although the forge has them. "
                "If it is a layer, put the layers in a stack with `gh stack link <bottom> ... <top>`; "
                "if not, its base is wrong",
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


# --- the stack the framework runs, where the forge has none


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
            f"its base {pr.base} is the branch of #{merged[0]['number']}, which has already landed. "
            f"Restack it onto {pr.trunk} and retarget it there"
        )
    if parents:
        return f"its base {pr.base} is the branch of #{parents[0]['number']}, which was closed without merging"
    return (
        f"its base {pr.base} is neither {pr.trunk} nor the branch of any pull request, so this "
        "is a pull request opened against the wrong base rather than a layer of a stack"
    )


def next_base(pr: PullRequest, forge: Forge, branch: str) -> str | None:
    """The base of the open pull request whose head is `branch`, if there is one."""
    open_parents = [p for p in pulls_from(forge, pr, branch) if p.get("state") == "open"]
    return (open_parents[0].get("base") or {}).get("ref") if open_parents else None


def chain_failures(pr: PullRequest, forge: Forge) -> list[Finding]:
    seen = [pr.base]
    while seen[-1] != pr.trunk:
        base = next_base(pr, forge, seen[-1])
        if base is None:
            return []  # condition 1 reports the break at the layer where it breaks
        if base in seen:
            chain = " -> ".join([*seen, base])
            return [Finding(RULE, 2, pr.where, f"the chain of bases is a cycle and never reaches {pr.trunk}: {chain}")]
        seen.append(base)
    return []


def framework_run_failures(pr: PullRequest, forge: Forge) -> list[Finding]:
    if pr.base == pr.trunk:
        return []
    problem = parent_failure(pr, pulls_from(forge, pr, pr.base))
    if problem:
        return [Finding(RULE, 1, pr.where, problem)]
    return chain_failures(pr, forge)


def is_a_layer_that_lands(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    """Conditions 1 and 2, on whichever kind of stack this forge can have."""
    try:
        if forge_has_stacks(forge):
            return native_failures(pr, stack_of(pr, forge)), []
        return framework_run_failures(pr, forge), []
    except Unreachable as error:
        return [], [Unchecked(RULE, n, str(error)) for n in (1, 2)]


# --- condition 3, on every pull request


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
            f"({', '.join(shas)}). Restack it onto {pr.trunk} past them: `gh stack sync` in a native "
            "stack, the rebase in skills/stacking-pull-requests otherwise",
        )
        for number, shas in carried.items()
    ], []


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    findings: list[Finding] = []
    unchecked: list[Unchecked] = []
    for condition in (is_a_layer_that_lands, carries_no_landed_commit):
        found, skipped = condition(pr, forge)
        findings.extend(found)
        unchecked.extend(skipped)
    return findings, unchecked


def main(argv: list[str]) -> int:
    return run_on_pull_request(argv, from_event, judge)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
