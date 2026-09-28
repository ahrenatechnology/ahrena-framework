#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/planning.md.

Decides the two conditions the rule states:

    1. no issue the pull request closes has an open sub-issue
    2. no issue the pull request closes is blocked by an open issue, unless the
       pull request is a layer of a stack, whose order the stack already holds

A plan's units are sub-issues of the issue they plan, and their order is the
forge's native blocked-by (ADR-011). Both conditions read the forge. Without a
token, or on a forge whose schema has no sub-issues or dependencies, they are
reported unchecked rather than failed.

Usage:
    python3 contributing/hooks/check-plan.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. An event that carries no pull request has nothing to decide.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, run_on_pull_request  # noqa: E402

RULE = "planning"

HERE = Path(__file__).resolve().parent


def sibling(module: str, filename: str) -> ModuleType:
    """A hook beside this one, loaded by path because its filename has hyphens."""
    spec = importlib.util.spec_from_file_location(module, HERE / filename)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[module] = loaded  # a dataclass resolves its module by name
    spec.loader.exec_module(loaded)
    return loaded


# What a pull request closes is traceability's to read, and whether it is a
# layer is check-stack's. Both are taken from those hooks, not restated.
traceability = sibling("check_traceability", "check-traceability.py")
stacks = sibling("check_stack", "check-stack.py")

PLAN_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      subIssues(first: 100) { nodes { number state } }
      blockedBy(first: 100) { nodes { number state } }
    }
  }
}
"""


@dataclass(frozen=True)
class PullRequest:
    closing: object  # traceability's view: number, repository, body
    layer: object  # check-stack's view: number, base, trunk, repository

    @property
    def repository(self) -> str:
        return self.layer.repository

    @property
    def where(self) -> str:
        return self.layer.where


def from_event(event: dict) -> PullRequest | None:
    closing, layer = traceability.from_event(event), stacks.from_event(event)
    return None if closing is None or layer is None else PullRequest(closing, layer)


def is_a_layer(pr: PullRequest, forge: Forge) -> bool:
    if pr.layer.base != pr.layer.trunk:
        return True
    return stacks.forge_has_stacks(forge) and stacks.stack_of(pr.layer, forge) is not None


def plan_of(pr: PullRequest, forge: Forge, number: int) -> dict | None:
    owner, _, name = pr.repository.partition("/")
    data = forge.graphql(PLAN_QUERY, {"owner": owner, "name": name, "number": number})
    return data["repository"]["issue"]


def still_open(nodes: list[dict]) -> list[int]:
    return sorted(n["number"] for n in nodes if n.get("state") == "OPEN")


def issue_failures(pr: PullRequest, number: int, issue: dict, layer: bool) -> list[Finding]:
    findings = []
    units = still_open(issue["subIssues"]["nodes"])
    if units:
        findings.append(
            Finding(
                RULE,
                1,
                pr.where,
                f"#{number}, which this closes, still has open sub-issues {', '.join(f'#{n}' for n in units)}. "
                "A plan closes when its units have: close it by hand then, or say `Part of` here instead",
            )
        )
    blockers = still_open(issue["blockedBy"]["nodes"])
    if blockers and not layer:
        findings.append(
            Finding(
                RULE,
                2,
                pr.where,
                f"#{number}, which this closes, is blocked by {', '.join(f'#{n}' for n in blockers)}, still open. "
                "Land the blocking work first, stack this on it, or remove the dependency if the order was wrong",
            )
        )
    return findings


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    findings: list[Finding] = []
    try:
        layer = is_a_layer(pr, forge)
        for number in traceability.closed_issues(pr.closing, forge):
            issue = plan_of(pr, forge, number)
            if issue is not None:
                findings.extend(issue_failures(pr, number, issue, layer))
    except Unreachable as error:
        return [], [Unchecked(RULE, n, str(error)) for n in (1, 2)]
    return findings, []


def main(argv: list[str]) -> int:
    return run_on_pull_request(argv, from_event, judge)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
