#!/usr/bin/env python3
"""Tests for check-pull-request.py.

A detector that never accepts is as broken as one that never rejects, so every
condition is pinned by a pull request that fails it and one it must not flag.
Each case writes an event payload, serves the forge's answers from a local
server, runs the hook as a subprocess, and asserts on the exit code and the
message. The hook is pointed at the server through GITHUB_API_URL and
GITHUB_GRAPHQL_URL, the variables Actions sets, so it runs exactly as it runs
in CI.

Three cases are this repository's own pull requests, because each condition
was written against a defect that happened here: #33's list of closing
references, #77's title, and #77 closing the epic it said it would not.

Usage:
    python3 contributing/hooks/test-check-pull-request.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-pull-request.py"
REPO = "acme/widgets"

OPEN_ISSUE = {"number": 1, "state": "open"}


def pull(number: int = 90, title: str = "feat: add the widget", body: str = "Closes #1", branch: str = "feat/1-widget") -> dict:
    return {
        "pull_request": {"number": number, "title": title, "body": body, "head": {"ref": branch}},
        "repository": {"full_name": REPO, "default_branch": "main"},
    }


def closing(*numbers: int) -> dict:
    nodes = [{"number": n, "repository": {"nameWithOwner": REPO}} for n in numbers]
    return {"data": {"repository": {"pullRequest": {"closingIssuesReferences": {"nodes": nodes}}}}}


def forge(issues: dict[int, dict | None] | None = None, closes: tuple[int, ...] = (1,)) -> dict:
    """The routes the local server answers: issue lookups and the closing-references query."""
    routes: dict[str, object] = {f"/repos/{REPO}/issues/{n}": issue for n, issue in (issues or {1: OPEN_ISSUE}).items()}
    routes["/graphql"] = closing(*closes)
    return routes


def case(name: str, event: dict, routes: dict | None, expect: list[str], ok: bool = False) -> tuple:
    return (name, event, routes, expect, ok)


CASES = [
    case("a pull request that closes its branch's issue passes", pull(), forge(), ["0 failure(s), 0 unchecked"], ok=True),
    case(
        "'Part of' names an epic without closing it, and passes",
        pull(body="Part of #1.", branch="docs/1-notes"),
        forge(closes=()),
        ["0 failure(s)"],
        ok=True,
    ),
    case("an event with no pull request has nothing to decide", {"ref": "refs/heads/main"}, None, ["nothing to decide"], ok=True),
    # --- condition 1: the branch's issue is named
    case(
        "a body that never names the branch's issue fails",
        pull(body="Adds the widget.", branch="feat/1-widget"),
        forge(closes=()),
        ["[pr-quality] condition 1", "answers #1 and the body never names it"],
    ),
    case(
        "a reference to another repository's #1 does not count",
        pull(body="Like other/repo#1.", branch="feat/1-widget"),
        forge(closes=()),
        ["[pr-quality] condition 1"],
    ),
    case(
        "an HTML entity is not a reference",
        pull(body="It&#1;s done.", branch="feat/1-widget"),
        forge(closes=()),
        ["[pr-quality] condition 1"],
    ),
    case(
        "a branch without an issue number is branch-naming's failure, not this one's",
        pull(body="Adds the widget.", branch="feat/widget"),
        forge(closes=()),
        ["0 failure(s)"],
        ok=True,
    ),
    # --- condition 2: one issue per keyword
    case(
        "#33's list closes only the first issue, and fails",
        pull(body="Closes #1, #2, #3", branch="feat/1-core"),
        forge(issues={1: OPEN_ISSUE}),
        ["[pr-quality] condition 2", "'Closes #1, #2' closes #1 only"],
    ),
    case(
        "'and' makes the same list",
        pull(body="Fixes #1 and #2"),
        forge(),
        ["[pr-quality] condition 2"],
    ),
    case(
        "a keyword per issue passes",
        pull(body="Closes #1\nCloses #2"),
        forge(issues={1: OPEN_ISSUE, 2: {"number": 2, "state": "open"}}, closes=(1, 2)),
        ["0 failure(s)"],
        ok=True,
    ),
    # --- condition 3: the title fits trunk
    case(
        "#77's title lands at 73 characters once the squash suffix is added, and fails",
        pull(number=77, title="docs(adr): record the decisions that shape issue-driven development"),
        forge(),
        ["[pr-quality] condition 3", "73 characters", "the title has 66"],
    ),
    case(
        "a title of exactly 66 lands at 72 and passes",
        pull(number=77, title="feat: " + "x" * 60),
        forge(),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a three-digit pull request leaves the title 65",
        pull(number=100, title="feat: " + "x" * 60),
        forge(),
        ["[pr-quality] condition 3", "the title has 65"],
    ),
    case(
        "a title that is not a conventional subject fails",
        pull(title="Add the widget"),
        forge(),
        ["[pr-quality] condition 3", "commit-format condition 1"],
    ),
    # --- condition 4: what the body closes is real
    case(
        "closing an issue that does not exist fails",
        pull(body="Closes #1"),
        forge(issues={1: None}),
        ["[pr-quality] condition 4", "does not exist"],
    ),
    case(
        "closing a pull request fails",
        pull(body="Closes #1"),
        forge(issues={1: {"number": 1, "state": "open", "pull_request": {}}}),
        ["[pr-quality] condition 4", "is a pull request"],
    ),
    case(
        "closing an issue that is already closed fails",
        pull(body="Closes #1"),
        forge(issues={1: {"number": 1, "state": "closed"}}),
        ["[pr-quality] condition 4", "already closed"],
    ),
    # --- condition 5: nothing closes silently
    case(
        "#77 closed the epic through its linked branch, and fails",
        pull(number=77, body="Part of #45. Does not close it.", branch="docs/45-decisions"),
        {"/graphql": closing(45)},
        ["[pr-quality] condition 5", "merging this closes #45, and the body does not say so"],
    ),
    # --- the forge tier
    case(
        "without a token the forge conditions are unchecked, not failed",
        pull(),
        {},
        ["[pr-quality] condition 4: unchecked", "[pr-quality] condition 5: unchecked", "0 failure(s), 2 unchecked"],
        ok=True,
    ),
    case(
        "without a token the text conditions are still decided",
        pull(body="Closes #1, #2"),
        {},
        ["[pr-quality] condition 2", "2 unchecked"],
    ),
]


class Handler(BaseHTTPRequestHandler):
    routes: dict = {}

    def answer(self) -> None:
        if self.path not in self.routes:
            self.send_error(500, f"no route for {self.path}")
            return
        data = self.routes[self.path]
        if data is None:
            self.send_error(404)
            return
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.answer()

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.answer()

    def log_message(self, *args: object) -> None:
        pass


def run(event: dict, routes: dict | None, server: ThreadingHTTPServer) -> tuple[int, str]:
    Handler.routes = routes or {}
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {**os.environ, "GITHUB_API_URL": url, "GITHUB_GRAPHQL_URL": f"{url}/graphql", "GITHUB_REPOSITORY": REPO}
    env["GITHUB_TOKEN"] = "test-token" if routes else ""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "event.json"
        path.write_text(json.dumps(event), encoding="utf-8")
        result = subprocess.run([sys.executable, str(HOOK), str(path)], capture_output=True, text=True, env=env)
    return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    found = []
    if ok and code != 0:
        found.append("expected the hook to pass, it failed")
    if not ok and code == 0:
        found.append("expected the hook to fail, it passed")
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    failed = 0
    for name, event, routes, expect, ok in CASES:
        code, output = run(event, routes, server)
        problems = problems_for(expect, ok, code, output)
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
        print("      --- hook output ---")
        for line in output.splitlines():
            print(f"      {line}")
    server.shutdown()

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
