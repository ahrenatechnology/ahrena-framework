#!/usr/bin/env python3
"""Tests for check-stack.py.

Every condition is pinned by a stack that fails it and one it must not flag.
Each case writes an event payload, serves the forge's answers from a local
server, runs the hook as a subprocess, and asserts on the exit code and the
message. The hook is pointed at the server through GITHUB_API_URL, the variable
Actions sets, so it runs exactly as it runs in CI.

This repository had no stacked pull request when the rule was written, so the
cases are built from GitHub's mechanics rather than from its history. The one
exception was measured live: a commit on a branch that landed by squash stays
associated with that pull request, which is what condition 3 reads.

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


def pr(number: int, base: str, state: str = "open", merged: bool = False) -> dict:
    return {"number": number, "state": state, "base": {"ref": base}, "merged_at": "2026-09-27T00:00:00Z" if merged else None}


def heads(branch: str, *pulls: dict) -> dict:
    return {f"{API}/pulls?head=acme:{branch}&state=all&per_page=100": list(pulls)}


def commits(number: int, owners: dict[str, list[dict]], page_two: dict[str, list[dict]] | None = None) -> dict:
    """The pull request's commits, and for each the pull requests it is associated with."""
    first = [{"sha": sha} for sha in owners]
    routes: dict[str, object] = {f"{API}/pulls/{number}/commits?per_page=100&page=1": first}
    if page_two is not None:
        routes[f"{API}/pulls/{number}/commits?per_page=100&page=2"] = [{"sha": sha} for sha in page_two]
    routes.update({f"{API}/commits/{sha}/pulls": pulls for sha, pulls in {**owners, **(page_two or {})}.items()})
    return routes


def own(number: int = 90) -> dict:
    """One commit that belongs to this pull request and nothing else."""
    return commits(number, {"a" * 40: [pr(number, "main")]})


def case(name: str, payload: dict, routes: dict | None, expect: list[str], ok: bool = False) -> tuple:
    return (name, payload, routes, expect, ok)


HUNDRED_OWN = {f"{i:040x}": [pr(90, "main")] for i in range(100)}

CASES = [
    case("a pull request on trunk with its own commits passes", event(), own(), ["0 failure(s), 0 unchecked"], ok=True),
    case("an event with no pull request has nothing to decide", {"ref": "refs/heads/main"}, None, ["nothing to decide"], ok=True),
    # --- condition 1: a base off trunk is an open pull request's branch
    case(
        "a layer on an open parent passes",
        event(base="feat/1-bottom"),
        {**heads("feat/1-bottom", pr(80, "main")), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a layer whose parent already landed fails, and says to restack",
        event(base="feat/1-bottom"),
        {**heads("feat/1-bottom", pr(80, "main", "closed", merged=True)), **own()},
        ["[stacked-pull-requests] condition 1", "#80, which has already landed", "Retarget it to main"],
    ),
    case(
        "a layer whose parent was abandoned fails",
        event(base="feat/1-bottom"),
        {**heads("feat/1-bottom", pr(80, "main", "closed")), **own()},
        ["[stacked-pull-requests] condition 1", "closed without merging"],
    ),
    case(
        "a base that is no pull request's branch is a wrong base, not a stack",
        event(base="develop"),
        {**heads("develop"), **own()},
        ["[stacked-pull-requests] condition 1", "opened against the wrong base"],
    ),
    # --- condition 2: the chain reaches trunk
    case(
        "a three-layer chain that reaches trunk passes",
        event(base="feat/2-middle"),
        {**heads("feat/2-middle", pr(81, "feat/1-bottom")), **heads("feat/1-bottom", pr(80, "main")), **own()},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a chain that closes into a cycle fails",
        event(base="feat/1-a"),
        {**heads("feat/1-a", pr(80, "feat/2-b")), **heads("feat/2-b", pr(81, "feat/1-a")), **own()},
        ["[stacked-pull-requests] condition 2", "is a cycle", "feat/1-a -> feat/2-b -> feat/1-a"],
    ),
    # --- condition 3: nothing already landed rides along
    case(
        "a branch still carrying a squashed parent's commits fails",
        event(),
        commits(90, {"b" * 40: [pr(80, "main", "closed", merged=True), pr(90, "main")], "a" * 40: [pr(90, "main")]}),
        ["[stacked-pull-requests] condition 3", "1 commit(s) of #80", "bbbbbbb", "Restack"],
    ),
    case(
        "a commit shared with an open parent is how a stack looks, and passes",
        event(base="feat/1-bottom"),
        {**heads("feat/1-bottom", pr(80, "main")), **commits(90, {"b" * 40: [pr(80, "main"), pr(90, "feat/1-bottom")]})},
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a landed commit on the second page of commits is found",
        event(),
        commits(90, HUNDRED_OWN, page_two={"c" * 40: [pr(80, "main", "closed", merged=True)]}),
        ["[stacked-pull-requests] condition 3", "#80"],
    ),
    # --- the forge tier
    case(
        "without a token a layer's three conditions are unchecked, not failed",
        event(base="feat/1-bottom"),
        {},
        ["condition 1: unchecked", "condition 2: unchecked", "condition 3: unchecked", "0 failure(s), 3 unchecked"],
        ok=True,
    ),
    case(
        "without a token a pull request on trunk has only condition 3 to leave unchecked",
        event(),
        {},
        ["condition 3: unchecked", "0 failure(s), 1 unchecked"],
        ok=True,
    ),
]


class Handler(BaseHTTPRequestHandler):
    routes: dict = {}

    def do_GET(self) -> None:
        if self.path not in self.routes:
            self.send_error(500, f"no route for {self.path}")
            return
        body = json.dumps(self.routes[self.path]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


def run(payload: dict, routes: dict | None, server: ThreadingHTTPServer) -> tuple[int, str]:
    Handler.routes = routes or {}
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {**os.environ, "GITHUB_API_URL": url, "GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": "test-token" if routes else ""}
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
