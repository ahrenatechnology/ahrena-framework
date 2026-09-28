#!/usr/bin/env python3
"""Tests for check-stack.py.

Every condition is pinned by a pull request that fails it and one it must not
flag. Each case writes an event payload, serves the forge's answers from a local
server, runs the hook as a subprocess, and asserts on the exit code and the
message. The hook is pointed at the server through GITHUB_API_URL and
GITHUB_GRAPHQL_URL, the variables Actions sets, so it runs exactly as it runs
in CI.

The stack answers are shaped like the ones GitHub gave for stack #103, the
first stack in this repository, and the suite names #104's criteria beside the
cases that cover them.

Usage:
    python3 contributing/hooks/test-check-stack.py
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

HOOK = Path(__file__).resolve().parent / "check-stack.py"
REPO = "acme/widgets"
API = f"/repos/{REPO}"


def event(number: int = 90, base: str = "main") -> dict:
    return {
        "pull_request": {"number": number, "base": {"ref": base}},
        "repository": {"full_name": REPO, "default_branch": "main"},
    }


def pr(number: int, merged: bool = False) -> dict:
    return {"number": number, "merged_at": "2026-09-28T00:00:00Z" if merged else None}


def stack(number: int | None = 103, base: str = "main") -> dict:
    """The GraphQL answer for the pull request's `stack` field; None when it is in no stack."""
    found = None if number is None else {"number": number, "baseRefName": base}
    return {"/graphql": {"data": {"repository": {"pullRequest": {"stack": found}}}}}


def commits(number: int, owners: dict[str, list[dict]], page_two: dict[str, list[dict]] | None = None) -> dict:
    """The pull request's commits, and for each the pull requests it is associated with."""
    routes: dict[str, object] = {f"{API}/pulls/{number}/commits?per_page=100&page=1": [{"sha": s} for s in owners]}
    if page_two is not None:
        routes[f"{API}/pulls/{number}/commits?per_page=100&page=2"] = [{"sha": s} for s in page_two]
    routes.update({f"{API}/commits/{sha}/pulls": pulls for sha, pulls in {**owners, **(page_two or {})}.items()})
    return routes


def own(number: int = 90) -> dict:
    """One commit that belongs to this pull request and nothing else."""
    return commits(number, {"a" * 40: [pr(number)]})


def case(name: str, payload: dict, routes: dict | None, expect: list[str], ok: bool = False) -> tuple:
    return (name, payload, routes, expect, ok)


HUNDRED_OWN = {f"{i:040x}": [pr(90)] for i in range(100)}

CASES = [
    case("a pull request on trunk in no stack passes", event(), {**stack(None), **own()}, ["0 failure(s), 0 unchecked"], ok=True),
    case("an event with no pull request has nothing to decide", {"ref": "refs/heads/main"}, None, ["nothing to decide"], ok=True),
    # --- condition 1: off trunk means in a GitHub stack (#104/AC-2)
    case(
        "a layer in a GitHub stack on trunk passes, as #102 did in stack #103",
        event(base="feat/98-criteria"),
        {**stack(), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a pull request based off trunk and in no stack fails, and says how to stack it",
        event(base="feat/1-bottom"),
        {**stack(None), **own()},
        ["[stacked-pull-requests] condition 1", "in no GitHub stack", "gh stack link"],
    ),
    case(
        "the bottom of a stack is based on trunk and passes",
        event(),
        {**stack(), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    # --- condition 2: the stack lands on trunk (#104/AC-3)
    case(
        "a stack based on another branch fails",
        event(base="feat/1-bottom"),
        {**stack(base="develop"), **own()},
        ["[stacked-pull-requests] condition 2", "stack #103 is based on develop, not main"],
    ),
    # --- condition 3: nothing already landed rides along (#104/AC-4)
    case(
        "a branch still carrying a squashed pull request's commits fails",
        event(),
        {**stack(None), **commits(90, {"b" * 40: [pr(80, merged=True), pr(90)], "a" * 40: [pr(90)]})},
        ["[stacked-pull-requests] condition 3", "1 commit(s) of #80", "bbbbbbb", "gh stack sync"],
    ),
    case(
        "a commit shared with an open layer below is how a stack looks, and passes",
        event(base="feat/1-bottom"),
        {**stack(), **commits(90, {"b" * 40: [pr(80), pr(90)]})},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a landed commit on the second page of commits is found",
        event(),
        {**stack(None), **commits(90, HUNDRED_OWN, page_two={"c" * 40: [pr(80, merged=True)]})},
        ["[stacked-pull-requests] condition 3", "#80"],
    ),
    # --- the forge tier
    case(
        "without a token all three conditions are unchecked, not failed",
        event(base="feat/1-bottom"),
        {},
        ["condition 1: unchecked", "condition 2: unchecked", "condition 3: unchecked", "0 failure(s), 3 unchecked"],
        ok=True,
    ),
]


class Handler(BaseHTTPRequestHandler):
    routes: dict = {}

    def answer(self) -> None:
        if self.path not in self.routes:
            self.send_error(500, f"no route for {self.path}")
            return
        body = json.dumps(self.routes[self.path]).encode()
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


def run(payload: dict, routes: dict | None, server: ThreadingHTTPServer) -> tuple[int, str]:
    Handler.routes = routes or {}
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {**os.environ, "GITHUB_API_URL": url, "GITHUB_GRAPHQL_URL": f"{url}/graphql", "GITHUB_REPOSITORY": REPO}
    env["GITHUB_TOKEN"] = "test-token" if routes else ""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "event.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
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
    for name, payload, routes, expect, ok in CASES:
        code, output = run(payload, routes, server)
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
