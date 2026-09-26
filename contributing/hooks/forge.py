"""Read-only access to the forge, shared by this plugin's forge-tier hooks.

A forge-tier hook decides a condition exactly, but the state it reads is the
forge's rather than the tree's, so it runs in CI with the default
GITHUB_TOKEN. Without a token, or when the forge cannot be reached, it reports
the condition unchecked rather than failed: an offline checkout cannot see what
it would have to judge, and a failure there would be a claim about the forge
made without asking it. The repository's ADR-002 records the tier.

Everything is read from the variables GitHub Actions sets. GITHUB_API_URL and
GITHUB_GRAPHQL_URL point at a GitHub Enterprise host when there is one, and
the test suites point them at a local server; nothing in here knows it is
being tested.

Standard library only. This is a module the two hooks beside it import, not a
detector, and it decides no condition of its own.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_API = "https://api.github.com"
DEFAULT_GRAPHQL = "https://api.github.com/graphql"
TIMEOUT_SECONDS = 30


class Unreachable(Exception):
    """The forge could not be asked, so the condition that needed it is unchecked."""


@dataclass(frozen=True)
class Finding:
    rule: str
    condition: int
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass(frozen=True)
class Unchecked:
    rule: str
    condition: int
    reason: str

    def __str__(self) -> str:
        return f"[{self.rule}] condition {self.condition}: unchecked, {self.reason}"


@dataclass(frozen=True)
class Forge:
    api: str
    graphql_url: str
    token: str
    repository: str  # owner/name

    def get(self, path: str) -> dict | list | None:
        """One REST resource under this repository, or None when it does not exist."""
        url = f"{self.api}/repos/{self.repository}/{path}".rstrip("/")
        try:
            return self._send(urllib.request.Request(url))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise Unreachable(f"the forge answered {error.code} for {path or 'the repository'}") from error

    def graphql(self, query: str, variables: dict) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode()
        request = urllib.request.Request(self.graphql_url, data=body, method="POST")
        try:
            answer = self._send(request)
        except urllib.error.HTTPError as error:
            raise Unreachable(f"the forge answered {error.code} to a GraphQL query") from error
        if not isinstance(answer, dict) or answer.get("errors") or "data" not in answer:
            raise Unreachable("the forge returned GraphQL errors")
        return answer["data"]

    def _send(self, request: urllib.request.Request) -> dict | list:
        if not self.token:
            raise Unreachable("no GITHUB_TOKEN, so the forge was not asked")
        if not self.repository:
            raise Unreachable("no GITHUB_REPOSITORY, so there is no repository to ask about")
        request.add_header("Authorization", f"Bearer {self.token}")
        request.add_header("Accept", "application/vnd.github+json")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            if isinstance(error, urllib.error.HTTPError):
                raise
            raise Unreachable(f"the forge could not be reached: {error}") from error


def from_environment(repository: str) -> Forge:
    """The forge Actions describes; `repository` stands in when GITHUB_REPOSITORY is unset."""
    return Forge(
        os.environ.get("GITHUB_API_URL", DEFAULT_API).rstrip("/"),
        os.environ.get("GITHUB_GRAPHQL_URL", DEFAULT_GRAPHQL),
        os.environ.get("GITHUB_TOKEN", ""),
        os.environ.get("GITHUB_REPOSITORY") or repository,
    )


def load_event(argv: list[str]) -> dict:
    """The webhook payload: the path given, or the one Actions names in GITHUB_EVENT_PATH."""
    path = argv[1] if len(argv) > 1 else os.environ.get("GITHUB_EVENT_PATH", "")
    if not path:
        raise SystemExit("no event: pass a payload path or set GITHUB_EVENT_PATH")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"cannot read the event at {path}: {error}") from error


def report(findings: list[Finding], unchecked: list[Unchecked], subject: str) -> int:
    for line in [*findings, *unchecked]:
        print(line)
    print(f"{subject}: {len(findings)} failure(s), {len(unchecked)} unchecked.")
    return 1 if findings else 0
