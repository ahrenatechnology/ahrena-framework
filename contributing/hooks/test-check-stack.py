#!/usr/bin/env python3
"""Tests for check-stack.py.

Every condition is pinned on both kinds of stack, the forge's native one and
the one the framework runs where the forge has none, by a pull request that
fails it and one it must not flag. Each case writes an event payload, serves
the forge's answers from a local server, runs the hook as a subprocess, and
asserts on the exit code and the message. The hook is pointed at the server
through GITHUB_API_URL and GITHUB_GRAPHQL_URL, the variables Actions sets.

The native answers are shaped like the ones GitHub gave for stack #103, and
the suite names #104's criteria beside the cases that cover them.

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
SCHEMA = "/graphql#schema"


def event(number: int = 90, base: str = "main") -> dict:
    return {
        "pull_request": {"number": number, "base": {"ref": base}},
        "repository": {"full_name": REPO, "default_branch": "main"},
    }


def pr(number: int, base: str = "main", state: str = "open", merged: bool = False) -> dict:
    return {"number": number, "state": state, "base": {"ref": base}, "merged_at": "2026-09-28T00:00:00Z" if merged else None}


def native(number: int | None = 103, base: str = "main") -> dict:
    """A forge with native stacks; the pull request is in stack `number`, or in none."""
    found = None if number is None else {"number": number, "baseRefName": base}
    return {
        SCHEMA: {"data": {"__type": {"name": "PullRequestStack"}}},
        "/graphql": {"data": {"repository": {"pullRequest": {"stack": found}}}},
    }


def no_native(*chains: dict) -> dict:
    """A forge with no native stacks, and the pull requests whose heads form the chain."""
    routes: dict[str, object] = {SCHEMA: {"data": {"__type": None}}}
    for chain in chains:
        routes.update(chain)
    return routes


def heads(branch: str, *pulls: dict) -> dict:
    return {f"{API}/pulls?head=acme:{branch}&state=all&per_page=100": list(pulls)}


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
    case("a pull request on trunk in no stack passes", event(), {**native(None), **own()}, ["0 failure(s), 0 unchecked"], ok=True),
    case("an event with no pull request has nothing to decide", {"ref": "refs/heads/main"}, None, ["nothing to decide"], ok=True),
    # --- native stacks: condition 1 (#104/AC-2) and condition 2 (#104/AC-3)
    case(
        "a layer in a native stack on trunk passes, as #102 did in stack #103",
        event(base="feat/98-criteria"),
        {**native(), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "off trunk and in no stack, on a forge that has them, fails and says how to stack it",
        event(base="feat/1-bottom"),
        {**native(None), **own()},
        ["[stacked-pull-requests] condition 1", "in no stack although the forge has them", "gh stack link"],
    ),
    case(
        "a native stack based on another branch fails",
        event(base="feat/1-bottom"),
        {**native(base="develop"), **own()},
        ["[stacked-pull-requests] condition 2", "stack #103 is based on develop, not main"],
    ),
    # --- a forge with no native stacks, where the framework runs it (#104/AC-7)
    case(
        "a layer on an open parent passes",
        event(base="feat/1-bottom"),
        {**no_native(heads("feat/1-bottom", pr(80))), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a layer whose parent already landed fails, and says to restack",
        event(base="feat/1-bottom"),
        {**no_native(heads("feat/1-bottom", pr(80, state="closed", merged=True))), **own()},
        ["[stacked-pull-requests] condition 1", "#80, which has already landed", "Restack it onto main"],
    ),
    case(
        "a layer whose parent was abandoned fails",
        event(base="feat/1-bottom"),
        {**no_native(heads("feat/1-bottom", pr(80, state="closed"))), **own()},
        ["[stacked-pull-requests] condition 1", "closed without merging"],
    ),
    case(
        "a base that is no pull request's branch is a wrong base, not a stack",
        event(base="develop"),
        {**no_native(heads("develop")), **own()},
        ["[stacked-pull-requests] condition 1", "opened against the wrong base"],
    ),
    case(
        "a three-layer chain that reaches trunk passes",
        event(base="feat/2-middle"),
        {**no_native(heads("feat/2-middle", pr(81, "feat/1-bottom")), heads("feat/1-bottom", pr(80))), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a chain that closes into a cycle fails",
        event(base="feat/1-a"),
        {**no_native(heads("feat/1-a", pr(80, "feat/2-b")), heads("feat/2-b", pr(81, "feat/1-a"))), **own()},
        ["[stacked-pull-requests] condition 2", "is a cycle", "feat/1-a -> feat/2-b -> feat/1-a"],
    ),
    # --- condition 3, on either kind (#104/AC-4)
    case(
        "a branch still carrying a squashed pull request's commits fails",
        event(),
        {**native(None), **commits(90, {"b" * 40: [pr(80, merged=True), pr(90)], "a" * 40: [pr(90)]})},
        ["[stacked-pull-requests] condition 3", "1 commit(s) of #80", "bbbbbbb", "Restack"],
    ),
    case(
        "a commit shared with an open layer below is how a stack looks, and passes",
        event(base="feat/1-bottom"),
        {**no_native(heads("feat/1-bottom", pr(80))), **commits(90, {"b" * 40: [pr(80), pr(90, "feat/1-bottom")]})},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a landed commit on the second page of commits is found",
        event(),
        {**native(None), **commits(90, HUNDRED_OWN, page_two={"c" * 40: [pr(80, merged=True)]})},
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

    def reply(self, key: str) -> None:
        if key not in self.routes:
            self.send_error(500, f"no route for {key}")
            return
        body = json.dumps(self.routes[key]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.reply(self.path)

    def do_POST(self) -> None:
        query = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.reply(SCHEMA if b"__type" in query else self.path)

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
