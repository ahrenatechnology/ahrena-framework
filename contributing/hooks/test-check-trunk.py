#!/usr/bin/env python3
"""Tests for check-trunk.py.

Every condition is pinned by a forge state that fails it and one it must not
flag. Each case serves the forge's answers from a local server, runs the hook
as a subprocess inside a scratch repository, and asserts on the exit code and
the message. The hook is pointed at the server through GITHUB_API_URL, the
variable Actions sets, so it runs exactly as it runs in CI.

This repository's own settings are a case: on the day the rule was written they
offered all three merge methods, which is how #74, #77 and #78 reached trunk by
rebase after ADR-001 had decided on the squash.

Usage:
    python3 contributing/hooks/test-check-trunk.py
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

HOOK = Path(__file__).resolve().parent / "check-trunk.py"
REPO = "acme/widgets"

SQUASH_ONLY = {
    "allow_squash_merge": True,
    "allow_rebase_merge": False,
    "allow_merge_commit": False,
    "squash_merge_commit_title": "PR_TITLE",
}
REQUIRES_PR = [{"type": "pull_request"}, {"type": "non_fast_forward"}]


def forge(settings: dict | None = None, rules: list | None = None, branch: dict | None = None, pulls: dict | None = None) -> dict:
    routes: dict[str, object] = {
        f"/repos/{REPO}": SQUASH_ONLY if settings is None else settings,
        f"/repos/{REPO}/rules/branches/main": REQUIRES_PR if rules is None else rules,
        f"/repos/{REPO}/branches/main": branch or {"name": "main", "protected": False},
    }
    routes.update({f"/repos/{REPO}/pulls/{n}": p for n, p in (pulls or {}).items()})
    return routes


def pull_event() -> dict:
    return {"pull_request": {"number": 9}, "repository": {"full_name": REPO, "default_branch": "main"}}


def push_event(before: str, after: str, ref: str = "refs/heads/main") -> dict:
    return {"ref": ref, "before": before, "after": after, "repository": {"full_name": REPO, "default_branch": "main"}}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    result = subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, capture_output=True, text=True, env=env, check=True)
    return result.stdout.strip()


def scratch_repository(root: Path) -> dict[str, str]:
    """base, then a squash of #5, then a commit pushed straight to trunk."""
    git(root, "init", "-q", "-b", "main")
    shas = {}
    for key, subject in (("base", "chore: start"), ("squash", "feat: the widget (#5)"), ("direct", "fix: straight to trunk")):
        git(root, "commit", "-q", "--allow-empty", "-m", subject)
        shas[key] = git(root, "rev-parse", "HEAD")
    return shas


def cases(shas: dict[str, str]) -> list[tuple]:
    merged_5 = {5: {"number": 5, "merge_commit_sha": shas["squash"]}}
    squash_push = push_event(shas["base"], shas["squash"])
    return [
        ("a squash-only forge that requires a pull request passes", pull_event(), forge(), ["0 failure(s), 0 unchecked"], True),
        # --- condition 1
        (
            "this repository's settings on the day the rule was written fail",
            pull_event(),
            forge(settings={**SQUASH_ONLY, "allow_rebase_merge": True, "allow_merge_commit": True, "squash_merge_commit_title": "COMMIT_OR_PR_TITLE"}),
            ["allow_rebase_merge is True", "allow_merge_commit is True", "squash_merge_commit_title is 'COMMIT_OR_PR_TITLE'", "3 failure(s)"],
            False,
        ),
        (
            "a forge with the squash turned off fails",
            pull_event(),
            forge(settings={**SQUASH_ONLY, "allow_squash_merge": False}),
            ["[protected-trunk] condition 1", "allow_squash_merge is False"],
            False,
        ),
        (
            "settings the token cannot see are unchecked",
            pull_event(),
            forge(settings={"name": "widgets"}),
            ["[protected-trunk] condition 1: unchecked", "cannot see allow_squash_merge"],
            True,
        ),
        # --- condition 2
        (
            "a trunk nothing protects fails",
            pull_event(),
            forge(rules=[]),
            ["[protected-trunk] condition 2", "nothing on the forge requires a pull request"],
            False,
        ),
        (
            "a ruleset without a pull_request rule is not enough",
            pull_event(),
            forge(rules=[{"type": "deletion"}]),
            ["[protected-trunk] condition 2"],
            False,
        ),
        (
            "classic protection is unchecked, because only an admin can read it",
            pull_event(),
            forge(rules=[], branch={"name": "main", "protected": True}),
            ["[protected-trunk] condition 2: unchecked", "classic branch protection"],
            True,
        ),
        # --- condition 3
        (
            "a push that lands a pull request's squash passes",
            squash_push,
            forge(pulls=merged_5),
            ["0 failure(s), 0 unchecked"],
            True,
        ),
        (
            "a commit pushed straight to trunk fails",
            push_event(shas["squash"], shas["direct"]),
            forge(),
            ["[protected-trunk] condition 3", "reached trunk without a pull request's squash"],
            False,
        ),
        (
            "a subject naming a pull request that merged as something else fails",
            squash_push,
            forge(pulls={5: {"number": 5, "merge_commit_sha": shas["base"]}}),
            ["[protected-trunk] condition 3", "names #5, whose merge is not this commit"],
            False,
        ),
        (
            "a push to another branch is not trunk's business",
            push_event(shas["squash"], shas["direct"], ref="refs/heads/feat/1-x"),
            forge(),
            ["0 failure(s)"],
            True,
        ),
        # --- the forge tier
        (
            "without a token every condition is unchecked, not failed",
            squash_push,
            {},
            ["condition 1: unchecked", "condition 2: unchecked", "condition 3: unchecked", "0 failure(s), 3 unchecked"],
            True,
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


def run(event: dict, routes: dict, server: ThreadingHTTPServer, repo: Path) -> tuple[int, str]:
    Handler.routes = routes
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {**os.environ, "GITHUB_API_URL": url, "GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": "test-token" if routes else ""}
    path = repo.parent / "event.json"
    path.write_text(json.dumps(event), encoding="utf-8")
    result = subprocess.run([sys.executable, str(HOOK), str(path)], capture_output=True, text=True, env=env, cwd=repo)
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
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        all_cases = cases(scratch_repository(repo))
        for name, event, routes, expect, ok in all_cases:
            code, output = run(event, routes, server, repo)
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
        print(f"{failed} of {len(all_cases)} cases failed.")
        return 1
    print(f"{len(all_cases)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
