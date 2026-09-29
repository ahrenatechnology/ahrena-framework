#!/usr/bin/env python3
"""Tests for check-plan.py.

Every condition is pinned by a pull request that fails it and one it must not
flag. Each case writes an event payload, serves the forge's answers from a local
server, runs the hook as a subprocess, and asserts on the exit code and the
message. GraphQL questions are told apart by what they ask for, so one server
answers the closing references, the stack schema, a pull request's stack and
an issue's plan.

The suite names #93's criteria beside the cases that cover them.

Usage:
    python3 contributing/hooks/test-check-plan.py
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

HOOK = Path(__file__).resolve().parent / "check-plan.py"
REPO = "acme/widgets"


def event(body: str = "Closes #1", base: str = "main") -> dict:
    return {
        "pull_request": {"number": 90, "body": body, "base": {"ref": base, "sha": "b"}, "head": {"sha": "h"}},
        "repository": {"full_name": REPO, "default_branch": "main"},
    }


def nodes(**states: str) -> dict:
    """`nodes(n2="OPEN")` is a connection holding issue #2, open."""
    return {"nodes": [{"number": int(k[1:]), "state": v} for k, v in states.items()]}


def plan(number: int, units: dict | None = None, blockers: dict | None = None) -> dict:
    issue = {"subIssues": units or nodes(), "blockedBy": blockers or nodes()}
    return {f"plan#{number}": {"data": {"repository": {"issue": issue}}}}


def forge(*plans: dict, stacked: bool = False, native: bool = True) -> dict:
    routes: dict[str, object] = {
        "closing": {"data": {"repository": {"pullRequest": {"closingIssuesReferences": {"nodes": []}}}}},
        "schema": {"data": {"__type": {"name": "PullRequestStack"} if native else None}},
        "stack": {"data": {"repository": {"pullRequest": {"stack": {"number": 7, "baseRefName": "main"} if stacked else None}}}},
    }
    for p in plans:
        routes.update(p)
    return routes


def case(name: str, payload: dict, routes: dict | None, expect: list[str], ok: bool = False) -> tuple:
    return (name, payload, routes, expect, ok)


CASES = [
    case("closing an issue whose units have all closed passes", event(), forge(plan(1, units=nodes(n2="CLOSED"))), ["0 failure(s), 0 unchecked"], ok=True),
    case("an event with no pull request has nothing to decide", {"ref": "refs/heads/main"}, None, ["nothing to decide"], ok=True),
    # --- condition 1: a plan closes when its units have (#93/AC-2)
    case(
        "closing an issue with an open sub-issue fails, as closing #45 would",
        event(),
        forge(plan(1, units=nodes(n2="CLOSED", n3="OPEN", n4="OPEN"))),
        ["[planning] condition 1", "#1, which this closes, still has open sub-issues #3, #4", "Part of"],
    ),
    case(
        "Part of an issue closes nothing, so its open units are not this pull request's business",
        event(body="Part of #1"),
        forge(plan(1, units=nodes(n3="OPEN"))),
        ["0 failure(s)"],
        ok=True,
    ),
    # --- condition 2: the order is kept (#93/AC-3)
    case(
        "closing an issue blocked by an open one fails",
        event(),
        forge(plan(1, blockers=nodes(n5="OPEN"))),
        ["[planning] condition 2", "#1, which this closes, is blocked by #5, still open"],
    ),
    case(
        "a blocker that has closed no longer blocks",
        event(),
        forge(plan(1, blockers=nodes(n5="CLOSED"))),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a layer based on its parent's branch is ordered by the stack, and passes",
        event(base="feat/5-below"),
        forge(plan(1, blockers=nodes(n5="OPEN"))),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "the bottom of a native stack on trunk is ordered by the stack too",
        event(),
        forge(plan(1, blockers=nodes(n5="OPEN")), stacked=True),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "on a forge with no native stacks, a pull request on trunk is not a layer",
        event(),
        forge(plan(1, blockers=nodes(n5="OPEN")), native=False),
        ["[planning] condition 2"],
    ),
    # --- what is not an issue, and the forge tier
    case(
        "a number that is not an issue is not judged here",
        event(),
        forge({"plan#1": {"data": {"repository": {"issue": None}}}}),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a forge whose schema has no sub-issues answers with errors, and both conditions are unchecked",
        event(),
        forge({"plan#1": {"errors": [{"message": "Field 'subIssues' doesn't exist on type 'Issue'"}]}}),
        ["condition 1: unchecked", "condition 2: unchecked", "0 failure(s), 2 unchecked"],
        ok=True,
    ),
    case(
        "without a token both conditions are unchecked, not failed",
        event(),
        {},
        ["condition 1: unchecked", "condition 2: unchecked", "0 failure(s), 2 unchecked"],
        ok=True,
    ),
]


def route_for(query: dict) -> str:
    text = query.get("query", "")
    if "__type" in text:
        return "schema"
    if "closingIssuesReferences" in text:
        return "closing"
    if "subIssues" in text:
        return f"plan#{query.get('variables', {}).get('number')}"
    return "stack"


class Handler(BaseHTTPRequestHandler):
    routes: dict = {}

    def do_POST(self) -> None:
        key = route_for(json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)))))
        if key not in self.routes:
            self.send_error(500, f"no route for {key}")
            return
        body = json.dumps(self.routes[key]).encode()
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
