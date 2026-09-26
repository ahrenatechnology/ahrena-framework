#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/pr-quality.md.

Decides the five conditions the rule states:

    1. the body names the issue the branch carries
    2. a closing keyword is followed by one issue, not a list
    3. the title fits trunk as the squash commit's subject
    4. every issue the body closes exists, is an issue, and is open
    5. every issue the merge will close is one the body closes

Conditions 1 to 3 read the pull request as the event payload describes it and
need nothing else. Conditions 4 and 5 read the forge, so without a token they
are reported unchecked rather than failed.

Usage:
    python3 contributing/hooks/check-pull-request.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. An event that carries no pull request has nothing to decide.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, from_environment, load_event, report  # noqa: E402

RULE = "pr-quality"

# The subject conditions are commit-format's, read from its hook rather than
# restated, because the title becomes a trunk commit's subject and two
# statements of what a subject is would drift.
_spec = importlib.util.spec_from_file_location(
    "check_commit_message", Path(__file__).resolve().parent / "check-commit-message.py"
)
commit_format = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = commit_format  # a dataclass resolves its module by name
_spec.loader.exec_module(commit_format)

# The branch shape branch-naming.md decides. Only the issue number is read
# here; a branch that does not match is that rule's failure, not this one's.
BRANCH_ISSUE = re.compile(r"^[A-Za-z]+/(?P<issue>[1-9][0-9]*)-")

# A reference to an issue: `#12`, or `owner/name#12` for one in another
# repository. The lookbehind keeps `&#39;` and `abc#1` from reading as one.
REFERENCE = r"(?<![\w&/.-])(?:(?P<repo>[\w.-]+/[\w.-]+))?#(?P<number>[1-9][0-9]*)(?![0-9])"
REFERENCES = re.compile(REFERENCE)

# GitHub's nine closing keywords, matched as it matches them: any case, an
# optional colon, then the reference. The keyword binds to that reference and
# no further.
CLOSING = re.compile(
    r"\b(?P<keyword>close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+" + REFERENCE, re.IGNORECASE
)

# What follows a closing reference when the author meant a list: a comma, an
# `and` or an ampersand, then another reference. Only the first one closes.
LIST_TAIL = re.compile(r"\s*(?:,|\band\b|&)\s*(?:[\w.-]+/[\w.-]+)?#[1-9][0-9]*", re.IGNORECASE)

# GitHub appends ` (#<number>)` to the subject of a squash commit.
SQUASH_SUFFIX = " (#{number})"

CLOSING_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      closingIssuesReferences(first: 100) {
        nodes { number repository { nameWithOwner } }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    body: str
    branch: str
    repository: str

    @property
    def where(self) -> str:
        return f"pull request #{self.number}"


def from_event(event: dict) -> PullRequest | None:
    pull = event.get("pull_request")
    if not isinstance(pull, dict):
        return None
    return PullRequest(
        int(pull["number"]),
        pull.get("title") or "",
        pull.get("body") or "",
        (pull.get("head") or {}).get("ref") or "",
        (event.get("repository") or {}).get("full_name") or "",
    )


def ours(match: re.Match, pr: PullRequest) -> bool:
    return match.group("repo") in (None, pr.repository)


def closed_by_body(pr: PullRequest) -> list[int]:
    """The issues in this repository the body closes, in the order written."""
    return [int(m.group("number")) for m in CLOSING.finditer(pr.body) if ours(m, pr)]


def names_issue(pr: PullRequest) -> list[Finding]:
    match = BRANCH_ISSUE.match(pr.branch)
    if match is None:
        return []
    issue = int(match.group("issue"))
    named = {int(m.group("number")) for m in REFERENCES.finditer(pr.body) if ours(m, pr)}
    if issue in named:
        return []
    return [
        Finding(
            RULE,
            1,
            pr.where,
            f"the branch {pr.branch} answers #{issue} and the body never names it. Write "
            f"'Closes #{issue}' when the merge finishes it, or 'Part of #{issue}' when it does not",
        )
    ]


def one_issue_per_keyword(pr: PullRequest) -> list[Finding]:
    findings = []
    for match in CLOSING.finditer(pr.body):
        tail = LIST_TAIL.match(pr.body, match.end())
        if tail is None:
            continue
        findings.append(
            Finding(
                RULE,
                2,
                pr.where,
                f"'{pr.body[match.start():tail.end()].strip()}' closes #{match.group('number')} "
                "only. A closing keyword binds to the one reference after it, so every "
                "other issue in the list stays open; give each its own keyword",
            )
        )
    return findings


def title_fits_trunk(pr: PullRequest) -> list[Finding]:
    findings = [
        Finding(RULE, 3, pr.where, f"as a trunk subject the title fails commit-format condition {n}: {text}")
        for n, text in commit_format.subject_failures(pr.title)
        if n != 3
    ]
    subject = pr.title + SQUASH_SUFFIX.format(number=pr.number)
    if len(subject) > commit_format.SUBJECT_MAX:
        findings.append(
            Finding(
                RULE,
                3,
                pr.where,
                f"the squash will land as {subject!r}, {len(subject)} characters, over the "
                f"{commit_format.SUBJECT_MAX} commit-format allows; the title has "
                f"{commit_format.SUBJECT_MAX - len(SQUASH_SUFFIX.format(number=pr.number))}",
            )
        )
    return findings


def closed_issue_failure(pr: PullRequest, number: int, issue: dict | list | None) -> Finding | None:
    if issue is None:
        problem = "does not exist in this repository"
    elif isinstance(issue, dict) and "pull_request" in issue:
        problem = "is a pull request, not an issue"
    elif isinstance(issue, dict) and issue.get("state") != "open":
        problem = "is already closed"
    else:
        return None
    return Finding(RULE, 4, pr.where, f"the body closes #{number}, which {problem}")


def closes_real_issues(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    findings = []
    for number in dict.fromkeys(closed_by_body(pr)):
        try:
            issue = forge.get(f"issues/{number}")
        except Unreachable as error:
            return [], [Unchecked(RULE, 4, str(error))]
        finding = closed_issue_failure(pr, number, issue)
        if finding is not None:
            findings.append(finding)
    return findings, []


def closes_only_what_it_says(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    owner, _, name = pr.repository.partition("/")
    try:
        data = forge.graphql(CLOSING_QUERY, {"owner": owner, "name": name, "number": pr.number})
    except Unreachable as error:
        return [], [Unchecked(RULE, 5, str(error))]
    nodes = data["repository"]["pullRequest"]["closingIssuesReferences"]["nodes"]
    said = set(closed_by_body(pr))
    silent = [n["number"] for n in nodes if n["repository"]["nameWithOwner"] == pr.repository and n["number"] not in said]
    return [
        Finding(
            RULE,
            5,
            pr.where,
            f"merging this closes #{number}, and the body does not say so. The link comes "
            "from the sidebar or from a branch created with `gh issue develop`, which closes "
            f"the issue whatever the body says. Write 'Closes #{number}', or unlink it",
        )
        for number in silent
    ], []


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    findings = [*names_issue(pr), *one_issue_per_keyword(pr), *title_fits_trunk(pr)]
    unchecked: list[Unchecked] = []
    for condition in (closes_real_issues, closes_only_what_it_says):
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
