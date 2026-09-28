#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/traceability.md.

Decides the three conditions the rule states:

    1. every issue the pull request closes lists its criteria, numbered without gaps
    2. every live criterion of those issues is named by a test in the tree
    3. every criterion a changed test names exists and is live

The criteria are read from each issue's body, which is their only home
(ADR-007), and the tests from the checkout. A test names a criterion with the
token `#<issue>/AC-<n>`, in any language. All three conditions need the
forge, so without a token they are reported unchecked rather than failed.

Usage:
    python3 contributing/hooks/check-traceability.py [event.json]

With no argument the payload is the one GitHub Actions names in
GITHUB_EVENT_PATH. Run from the root of a checkout of the pull request's head
with full history, which is what the workflow has.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import Finding, Forge, Unchecked, Unreachable, run_on_pull_request  # noqa: E402

RULE = "traceability"

# The closing keywords are pr-quality's, read from its hook rather than
# restated. The body is what lands on trunk (protected-trunk condition 1), so
# it is the record of what a pull request closes. GitHub's own list is empty
# until the pull request is based on the default branch, which a layer of a
# stack is not.
_spec = importlib.util.spec_from_file_location(
    "check_pull_request", Path(__file__).resolve().parent / "check-pull-request.py"
)
pr_quality = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = pr_quality  # a dataclass resolves its module by name
_spec.loader.exec_module(pr_quality)

# Code and comments are not where criteria are written. A fenced example in an
# issue body is an example, not the issue's criteria.
NOT_PROSE = re.compile(r"^(```|~~~).*?^\1[^\n]*$|<!--.*?-->", re.DOTALL | re.MULTILINE)

HEADING = re.compile(r"^#{1,6}\s*Acceptance criteria\s*$", re.IGNORECASE | re.MULTILINE)
ANY_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)
ITEM = re.compile(r"^\s*[-*+]\s+(?:\[[ xX]\]\s+)?AC-(?P<n>[0-9]+):\s*(?P<text>.*)$", re.MULTILINE)
REMOVED = "(removed"
BY_REVIEW = "(checked by review)"

# `#98/AC-2`, not preceded by a word character or a slash, so that a path or
# `owner/repo#98/AC-2` is not read as a bare reference to this repository.
TOKEN = re.compile(r"(?<![\w/])#(?P<issue>[1-9][0-9]*)/AC-(?P<n>[1-9][0-9]*)(?![0-9])")

# A file is a test by the conventions the common runners share: a directory
# named for tests anywhere in its path, or a name that marks it as one.
TEST_DIRS = frozenset({"test", "tests", "spec", "specs", "__tests__"})
TEST_NAME = re.compile(r"^(?:test[_-].+|.+[_-]test|.+\.(?:test|spec))\.[A-Za-z0-9]+$")

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
class Criterion:
    issue: int
    number: int
    text: str

    @property
    def live(self) -> bool:
        """Neither removed nor declared as decided by a reader, so a test must name it."""
        return not self.text.startswith(REMOVED) and not self.text.rstrip().endswith(BY_REVIEW)


@dataclass(frozen=True)
class PullRequest:
    number: int
    repository: str
    body: str
    base_sha: str
    head_sha: str

    @property
    def where(self) -> str:
        return f"pull request #{self.number}"


def from_event(event: dict) -> PullRequest | None:
    pull = event.get("pull_request")
    if not isinstance(pull, dict):
        return None
    return PullRequest(
        int(pull["number"]),
        (event.get("repository") or {}).get("full_name") or "",
        pull.get("body") or "",
        (pull.get("base") or {}).get("sha") or "",
        (pull.get("head") or {}).get("sha") or "",
    )


def criteria_section(body: str) -> str | None:
    prose = NOT_PROSE.sub("", body)
    heading = HEADING.search(prose)
    if heading is None:
        return None
    rest = prose[heading.end():]
    following = ANY_HEADING.search(rest)
    return rest[: following.start()] if following else rest


def parse(issue: int, body: str) -> list[Criterion] | None:
    """The issue's criteria in the order written, or None when it has no section."""
    section = criteria_section(body)
    if section is None:
        return None
    return [Criterion(issue, int(m.group("n")), m.group("text").strip()) for m in ITEM.finditer(section)]


def numbering_problem(criteria: list[Criterion]) -> str | None:
    numbers = [c.number for c in criteria]
    if not numbers:
        return "has an Acceptance criteria heading and no AC-n items under it"
    repeated = sorted({n for n in numbers if numbers.count(n) > 1})
    if repeated:
        return f"numbers {', '.join(f'AC-{n}' for n in repeated)} more than once"
    missing = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
    if missing:
        return f"skips {', '.join(f'AC-{n}' for n in missing)}; a dropped criterion stays, marked (removed: why)"
    return None


def git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def is_test(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(part in TEST_DIRS for part in parts[:-1]) or TEST_NAME.match(parts[-1]) is not None


def tokens_in(paths: list[str]) -> dict[str, set[tuple[int, int]]]:
    """For each test file that exists in the tree, the criteria it names."""
    found: dict[str, set[tuple[int, int]]] = {}
    for path in filter(is_test, paths):
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found[path] = {(int(m.group("issue")), int(m.group("n"))) for m in TOKEN.finditer(text)}
    return found


class Issues:
    """Issue bodies, each fetched once per run."""

    def __init__(self, forge: Forge) -> None:
        self.forge = forge
        self.bodies: dict[int, str | None] = {}

    def criteria(self, number: int) -> list[Criterion] | None:
        if number not in self.bodies:
            issue = self.forge.get(f"issues/{number}")
            self.bodies[number] = None if issue is None or "pull_request" in issue else issue.get("body") or ""
        body = self.bodies[number]
        return None if body is None else parse(number, body)


def closed_by_body(pr: PullRequest) -> set[int]:
    prose = pr_quality.NOT_PROSE.sub(" ", pr.body)
    return {
        int(m.group("number"))
        for m in pr_quality.CLOSING.finditer(prose)
        if m.group("repo") in (None, pr.repository)
    }


def closed_issues(pr: PullRequest, forge: Forge) -> list[int]:
    """What the body closes, and whatever else the forge will close on merge."""
    owner, _, name = pr.repository.partition("/")
    data = forge.graphql(CLOSING_QUERY, {"owner": owner, "name": name, "number": pr.number})
    nodes = data["repository"]["pullRequest"]["closingIssuesReferences"]["nodes"]
    linked = {n["number"] for n in nodes if n["repository"]["nameWithOwner"] == pr.repository}
    return sorted(linked | closed_by_body(pr))


def shape_failures(pr: PullRequest, closed: dict[int, list[Criterion] | None]) -> list[Finding]:
    findings = []
    for issue, criteria in closed.items():
        problem = "has no Acceptance criteria section" if criteria is None else numbering_problem(criteria)
        if problem:
            findings.append(Finding(RULE, 1, pr.where, f"#{issue}, which this closes, {problem}"))
    return findings


def untraced(pr: PullRequest, closed: dict[int, list[Criterion] | None], named: set[tuple[int, int]]) -> list[Finding]:
    live = [c for criteria in closed.values() for c in criteria or [] if c.live]
    return [
        Finding(
            RULE,
            2,
            pr.where,
            f"#{c.issue}/AC-{c.number} is named by no test: {c.text!r}. Put `#{c.issue}/AC-{c.number}` beside the test that covers "
            "it, or end the criterion with (checked by review) if no test can decide it",
        )
        for c in live
        if (c.issue, c.number) not in named
    ]


def dangling(pr: PullRequest, changed: dict[str, set[tuple[int, int]]], issues: Issues) -> list[Finding]:
    findings = []
    for path, tokens in sorted(changed.items()):
        for issue, number in sorted(tokens):
            criteria = issues.criteria(issue)
            match = [c for c in criteria or [] if c.number == number]
            if not match or match[0].text.startswith(REMOVED):
                findings.append(
                    Finding(RULE, 3, path, f"names #{issue}/AC-{number}, which #{issue} does not list as a criterion")
                )
    return findings


def judge(pr: PullRequest, forge: Forge) -> tuple[list[Finding], list[Unchecked]]:
    issues = Issues(forge)
    everything = tokens_in(git(["ls-files"]).splitlines())
    changed_paths = git(["diff", "--name-only", f"{pr.base_sha}...{pr.head_sha}"]).splitlines()
    try:
        closed = {n: issues.criteria(n) for n in closed_issues(pr, forge)}
        named = set().union(*everything.values()) if everything else set()
        findings = [*shape_failures(pr, closed), *untraced(pr, closed, named)]
        findings.extend(dangling(pr, {p: t for p, t in everything.items() if p in changed_paths}, issues))
    except Unreachable as error:
        return [], [Unchecked(RULE, n, str(error)) for n in (1, 2, 3)]
    return findings, []


def main(argv: list[str]) -> int:
    return run_on_pull_request(argv, from_event, judge)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
