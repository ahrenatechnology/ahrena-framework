#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/protected-trunk.md.

Decides the three conditions the rule states:

    1. the forge merges by squash only, titled with the pull request's title
    2. something on the forge requires a pull request to reach trunk
    3. every commit a push adds to trunk is the squash of a merged pull request

Conditions 1 and 2 read the repository's settings, so they are decided on
every event. Condition 3 reads a push, so it is decided only when the event is
a push to trunk; a pull request has not reached trunk yet. All three read the
forge, and without a token each is reported unchecked rather than failed.

Usage:
    python3 contributing/hooks/check-trunk.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. Condition 3 also needs the pushed commits in the local
clone, which is what a checkout with full history has.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, from_environment, load_event, report  # noqa: E402

RULE = "protected-trunk"

# The merge settings ADR-001 decides, as the REST API names them. Squash on,
# the two others off, and the squash titled from the pull request, so the
# title pr-quality condition 3 checks is the subject trunk actually receives.
MERGE_SETTINGS = (
    ("allow_squash_merge", True, "the squash is the one method ADR-001 allows"),
    ("allow_rebase_merge", False, "a rebase re-authors every commit and drops its signature"),
    ("allow_merge_commit", False, "a merge commit ends trunk's linearity"),
    ("squash_merge_commit_title", "PR_TITLE", "the title is what pr-quality checks as trunk's subject"),
)

# The subject GitHub gives a squash commit ends in ` (#<number>)`.
SQUASH_SUBJECT = re.compile(r" \(#(?P<number>[1-9][0-9]*)\)$")

# What a push reports as `before` when it creates the branch.
NO_COMMIT = "0" * 40


@dataclass(frozen=True)
class Push:
    trunk: str
    before: str
    after: str


def trunk_of(event: dict) -> str:
    return (event.get("repository") or {}).get("default_branch") or "main"


def push_to_trunk(event: dict) -> Push | None:
    """The push this event describes, when it is one and it landed on trunk."""
    trunk = trunk_of(event)
    if event.get("ref") != f"refs/heads/{trunk}" or "after" not in event:
        return None
    return Push(trunk, event.get("before") or NO_COMMIT, event["after"])


def settings_failures(repository: dict) -> tuple[list[Finding], list[Unchecked]]:
    findings = []
    for field, wanted, why in MERGE_SETTINGS:
        if field not in repository:
            reason = f"the token cannot see {field}; an owner reads it under Settings, General"
            return [], [Unchecked(RULE, 1, reason)]
        if repository[field] != wanted:
            findings.append(
                Finding(RULE, 1, "repository settings", f"{field} is {repository[field]!r}, not {wanted!r}: {why}")
            )
    return findings, []


def merges_by_squash_only(forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    try:
        repository = forge.get("")
    except Unreachable as error:
        return [], [Unchecked(RULE, 1, str(error))]
    return settings_failures(repository or {})


def requires_pull_request(forge: Forge, trunk: str) -> tuple[list[Finding], list[Unchecked]]:
    try:
        rules = forge.get(f"rules/branches/{trunk}") or []
        if any(rule.get("type") == "pull_request" for rule in rules):
            return [], []
        branch = forge.get(f"branches/{trunk}") or {}
    except Unreachable as error:
        return [], [Unchecked(RULE, 2, str(error))]
    if branch.get("protected"):
        reason = f"{trunk} has classic branch protection, whose settings only an admin token can read"
        return [], [Unchecked(RULE, 2, reason)]
    return [
        Finding(
            RULE,
            2,
            f"branch {trunk}",
            "nothing on the forge requires a pull request: no ruleset carries a pull_request "
            "rule and the branch is not protected, so a direct push reaches trunk unreviewed",
        )
    ], []


def git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def pushed(push: Push) -> list[tuple[str, str]]:
    """The first-parent commits the push added, oldest first, with their subjects."""
    span = push.after if push.before == NO_COMMIT else f"{push.before}..{push.after}"
    lines = git(["log", "--first-parent", "--reverse", "--format=%H %s", span]).splitlines()
    return [tuple(line.split(" ", 1)) if " " in line else (line, "") for line in lines]


def commit_failure(sha: str, subject: str, forge: Forge) -> Finding | None:
    match = SQUASH_SUBJECT.search(subject)
    if match is None:
        return Finding(RULE, 3, sha[:7], f"{subject!r} reached trunk without a pull request's squash: it carries no (#N)")
    number = int(match.group("number"))
    pull = forge.get(f"pulls/{number}") or {}
    if pull.get("merge_commit_sha") == sha:
        return None
    return Finding(RULE, 3, sha[:7], f"the subject names #{number}, whose merge is not this commit")


def lands_through_pull_requests(forge: Forge, push: Push) -> tuple[list[Finding], list[Unchecked]]:
    findings = []
    for sha, subject in pushed(push):
        try:
            finding = commit_failure(sha, subject, forge)
        except Unreachable as error:
            return findings, [Unchecked(RULE, 3, str(error))]
        if finding is not None:
            findings.append(finding)
    return findings, []


def judge(event: dict, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    results = [merges_by_squash_only(forge), requires_pull_request(forge, trunk_of(event))]
    push = push_to_trunk(event)
    if push is not None:
        results.append(lands_through_pull_requests(forge, push))
    findings = [finding for found, _ in results for finding in found]
    unchecked = [skip for _, skipped in results for skip in skipped]
    return findings, unchecked


def main(argv: list[str]) -> int:
    event = load_event(argv)
    forge = from_environment((event.get("repository") or {}).get("full_name") or "")
    findings, unchecked = judge(event, forge)
    return report(findings, unchecked, f"trunk {trunk_of(event)}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
