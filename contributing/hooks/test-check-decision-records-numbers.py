#!/usr/bin/env python3
"""Tests for check-decision-records-numbers.py.

Every condition is pinned by a pull request that fails it and one it must not
flag. Each case writes an event payload, serves the forge's answers from a
local server, runs the hook as a subprocess, and asserts on the exit code and
the message. The hook is pointed at the server through GITHUB_API_URL, the
variable Actions sets.

The cases name #188's acceptance criteria beside what they cover:

    #188/AC-1 a number already on trunk fails, and the finding names the renumber fix
    #188/AC-2 a number another open pull request also adds fails, naming that pull request
    #188/AC-3 a free number passes
    #188/AC-4 without a token the conditions are unchecked, not failed
    #188/AC-5 an event with no pull request has nothing to decide

Usage:
    python3 contributing/hooks/test-check-decision-records-numbers.py
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

HOOK = Path(__file__).resolve().parent / "check-decision-records-numbers.py"
REPO = "acme/widgets"
API = f"/repos/{REPO}"


def event(number: int = 90, pull: bool = True) -> dict:
    if not pull:
        return {"ref": "refs/heads/main"}
    return {
        "pull_request": {"number": number, "base": {"ref": "main"}},
        "repository": {"full_name": REPO, "default_branch": "main"},
    }


def fentry(name: str, status: str = "added") -> dict:
    return {"status": status, "filename": f"docs/adr/{name}"}


def files(number: int, *entries: dict) -> dict:
    return {f"{API}/pulls/{number}/files?per_page=100&page=1": list(entries)}


def contents(*names: str) -> dict:
    return {f"{API}/contents/docs/adr?ref=main": [{"name": name, "type": "file"} for name in names]}


def open_pulls(*numbers: int) -> dict:
    return {f"{API}/pulls?state=open&per_page=100&page=1": [{"number": n} for n in numbers]}


def case(name: str, payload: dict, routes: dict | None, expect: list[str], ok: bool = False) -> tuple:
    return (name, payload, routes, expect, ok)


CASES = [
    case(
        "a number already on trunk fails and the finding names the renumber fix (#188/AC-1)",
        event(),
        {**files(90, fentry("ADR-015-new-thing.md")), **contents("ADR-014-x.md", "ADR-015-real-thing.md"), **open_pulls()},
        [
            "[concurrent-decision-records] condition 1",
            "ADR-015 already exists on trunk",
            "renumber-decision-record.py docs/adr/ADR-015-new-thing.md",
        ],
    ),
    case(
        "a number another open pull request also adds fails, naming that pull request (#188/AC-2)",
        event(90),
        {
            **files(90, fentry("ADR-015-new-thing.md")),
            **contents("ADR-014-x.md"),
            **open_pulls(91),
            **files(91, fentry("ADR-015-other-thing.md")),
        },
        ["[concurrent-decision-records] condition 2", "ADR-015 is also introduced by #91", "renumber-decision-record.py docs/adr/ADR-015-new-thing.md"],
    ),
    case(
        "a free number passes (#188/AC-3)",
        event(90),
        {
            **files(90, fentry("ADR-016-new-thing.md")),
            **contents("ADR-014-x.md", "ADR-015-real-thing.md"),
            **open_pulls(91),
            **files(91, fentry("ADR-017-other-thing.md")),
        },
        ["0 failure(s), 0 unchecked"],
        ok=True,
    ),
    case(
        "a pull request that modifies a record introduces no number and passes",
        event(90),
        {**files(90, fentry("ADR-015-real-thing.md", status="modified")), **contents("ADR-015-real-thing.md"), **open_pulls()},
        ["0 failure(s), 0 unchecked"],
        ok=True,
    ),
    case(
        "without a token the conditions are unchecked, not failed (#188/AC-4)",
        event(90),
        {},
        ["condition 1: unchecked", "condition 2: unchecked", "0 failure(s), 2 unchecked"],
        ok=True,
    ),
    case(
        "an event with no pull request has nothing to decide (#188/AC-5)",
        event(pull=False),
        None,
        ["nothing to decide"],
        ok=True,
    ),
]


class Handler(BaseHTTPRequestHandler):
    routes: dict = {}

    def reply(self, key: str) -> None:
        if key not in self.routes:
            self.send_error(404, f"no route for {key}")
            return
        body = json.dumps(self.routes[key]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.reply(self.path)

    def log_message(self, *args: object) -> None:
        pass


def run(payload: dict, routes: dict | None, server: ThreadingHTTPServer) -> tuple[int, str]:
    Handler.routes = routes or {}
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {**os.environ, "GITHUB_API_URL": url, "GITHUB_REPOSITORY": REPO}
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
