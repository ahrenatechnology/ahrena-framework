#!/usr/bin/env python3
"""Tests for check-traceability.py.

Every condition is pinned by a pull request that fails it and one it must not
flag. Each case builds a scratch repository with a base and a head commit,
serves the forge's answers from a local server, runs the hook as a subprocess
from inside that repository, and asserts on the exit code and the message.

The suite names the criteria of #99, which built the detector, beside the
cases that cover them, so the rule it tests holds for its own issue.

Usage:
    python3 contributing/hooks/test-check-traceability.py
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

HOOK = Path(__file__).resolve().parent / "check-traceability.py"
REPO = "acme/widgets"
API = f"/repos/{REPO}"

def ac(issue: int, n: int) -> str:
    """A criterion token, built so the literal never appears in this file for the detector to read."""
    return f"#{issue}/AC-{n}"


CRITERIA = "## Acceptance criteria\n\n- AC-1: It works.\n- AC-2: It is documented. (checked by review)\n"
COVERED = {"tests/test_widget.py": "def test_it_works():  # covers " + ac(1, 1) + "\n    assert True\n"}


def closing(*numbers: int) -> dict:
    nodes = [{"number": n, "repository": {"nameWithOwner": REPO}} for n in numbers]
    return {"data": {"repository": {"pullRequest": {"closingIssuesReferences": {"nodes": nodes}}}}}


def forge(issues: dict[int, str | None], linked: tuple[int, ...] = ()) -> dict:
    """Issue bodies by number, None for one that does not exist, and the forge's own closing list."""
    routes: dict[str, object] = {"/graphql": closing(*linked)}
    routes.update({f"{API}/issues/{n}": None if body is None else {"number": n, "body": body} for n, body in issues.items()})
    return routes


def case(name: str, head: dict[str, str], routes: dict | None, expect: list[str], ok: bool = False, **extra: object) -> tuple:
    """`head` is the tree the pull request brings; `base` (in extra) is what it starts from."""
    return (name, extra.get("base", {}), head, routes, extra.get("body", "Closes #1"), expect, ok)


CASES = [
    case("a closed issue whose live criterion a test names passes", COVERED, forge({1: CRITERIA}), ["0 failure(s), 0 unchecked"], ok=True),
    # --- condition 1: the criteria are there and numbered (#99/AC-5)
    case(
        "an issue with no Acceptance criteria section fails",
        COVERED,
        forge({1: "Just a description."}),
        ["[traceability] condition 1", "#1, which this closes, has no Acceptance criteria section"],
    ),
    case(
        "a gap in the numbering fails, and says a dropped criterion stays",
        COVERED,
        forge({1: "## Acceptance criteria\n\n- AC-1: It works.\n- AC-3: It is fast. (checked by review)\n"}),
        ["[traceability] condition 1", "skips AC-2", "marked (removed: why)"],
    ),
    case(
        "a repeated number fails",
        COVERED,
        forge({1: "## Acceptance criteria\n\n- AC-1: It works.\n- AC-1: It also works. (checked by review)\n"}),
        ["[traceability] condition 1", "numbers AC-1 more than once"],
    ),
    case(
        "a heading with nothing under it fails",
        COVERED,
        forge({1: "## Acceptance criteria\n\nTo be written.\n\n## Notes\n"}),
        ["[traceability] condition 1", "no AC-n items under it"],
    ),
    case(
        "criteria written out of order but without gaps pass, as a late AC-5 does",
        {"tests/test_widget.py": "# covers " + ac(1, 1) + " and " + ac(1, 3) + "\n"},
        forge({1: "## Acceptance criteria\n\n- AC-1: a\n- AC-3: c\n- AC-2: b (checked by review)\n"}),
        ["0 failure(s)"],
        ok=True,
    ),
    # --- condition 2: every live criterion is named by a test (#99/AC-1)
    case(
        "a live criterion no test names fails",
        {"tests/test_widget.py": "def test_other():\n    pass\n"},
        forge({1: CRITERIA}),
        ["[traceability] condition 2", ac(1, 1) + " is named by no test", "(checked by review) if no test can decide it"],
    ),
    case(
        "a name in a document is not a test",
        {"docs/widget.md": "This covers " + ac(1, 1) + ".\n"},
        forge({1: CRITERIA}),
        ["[traceability] condition 2", ac(1, 1) + " is named by no test"],
    ),
    case(
        "a removed criterion needs no test",
        COVERED,
        forge({1: CRITERIA + "- AC-3: (removed: out of scope)\n"}),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "a fenced example in the issue is not its criteria",
        COVERED,
        forge({1: CRITERIA + "\n```markdown\n## Acceptance criteria\n- AC-9: an example\n```\n"}),
        ["0 failure(s)"],
        ok=True,
    ),
    case(
        "the test conventions of several languages all count",
        {
            "contributing/hooks/test-check-widget.py": "# " + ac(1, 1) + "\n",
            "pkg/widget_test.go": "// " + ac(1, 3) + "\n",
            "web/widget.spec.ts": "// " + ac(1, 4) + "\n",
        },
        forge({1: "## Acceptance criteria\n\n- AC-1: a\n- AC-2: b (checked by review)\n- AC-3: c\n- AC-4: d\n"}),
        ["0 failure(s)"],
        ok=True,
    ),
    # --- condition 3: what a changed test names exists (#99/AC-2)
    case(
        "a changed test naming a criterion the issue does not list fails",
        {**COVERED, "tests/test_extra.py": "# covers " + ac(1, 9) + "\n"},
        forge({1: CRITERIA}),
        ["[traceability] condition 3", "tests/test_extra.py", "names " + ac(1, 9) + ", which #1 does not list"],
    ),
    case(
        "a changed test naming a removed criterion fails",
        {**COVERED, "tests/test_extra.py": "# covers " + ac(1, 3) + "\n"},
        forge({1: CRITERIA + "- AC-3: (removed: out of scope)\n"}),
        ["[traceability] condition 3", "names " + ac(1, 3)],
    ),
    case(
        "a changed test naming an issue that does not exist fails",
        {**COVERED, "tests/test_extra.py": "# covers " + ac(7, 1) + "\n"},
        forge({1: CRITERIA, 7: None}),
        ["[traceability] condition 3", "names " + ac(7, 1)],
    ),
    case(
        "a dangling name in a test this pull request did not touch is not its business",
        COVERED,
        forge({1: CRITERIA}),
        ["0 failure(s)"],
        ok=True,
        base={"tests/test_old.py": "# covers " + ac(7, 1) + "\n"},
    ),
    # --- what counts as closed (#99/AC-1)
    case(
        "a layer of a stack is read from its body, since GitHub lists nothing to close",
        {"tests/test_widget.py": "def test_other():\n    pass\n"},
        forge({1: CRITERIA}, linked=()),
        ["[traceability] condition 2", ac(1, 1)],
    ),
    case(
        "an issue the forge will close through a linked branch is read too",
        {"tests/test_widget.py": "def test_other():\n    pass\n"},
        forge({2: CRITERIA.replace("It works", "It links")}, linked=(2,)),
        ["[traceability] condition 2", ac(2, 1)],
        body="Part of #9",
    ),
    case(
        "a closing keyword inside code closes nothing, so it is not traced",
        {},
        forge({}),
        ["0 failure(s)"],
        ok=True,
        body="The rule reads `Closes #1`.",
    ),
    case("an event with no pull request has nothing to decide", {}, None, ["nothing to decide"], ok=True, body=None),
    # --- the forge tier
    case(
        "without a token all three conditions are unchecked, not failed",
        COVERED,
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
        if self.routes[self.path] is None:
            self.send_error(404)
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


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    result = subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, capture_output=True, text=True, env=env, check=True)
    return result.stdout.strip()


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def run(entry: tuple, server: ThreadingHTTPServer, tmp: Path) -> tuple[int, str]:
    _, base, head, routes, body, _, _ = entry
    repo = tmp / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    base_sha, head_sha = commit(repo, base, "base"), commit(repo, head, "head")
    event = {"ref": "refs/heads/main"} if body is None else {
        "pull_request": {"number": 90, "body": body, "base": {"sha": base_sha}, "head": {"sha": head_sha}},
        "repository": {"full_name": REPO, "default_branch": "main"},
    }
    (tmp / "event.json").write_text(json.dumps(event), encoding="utf-8")
    Handler.routes = routes or {}
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {**os.environ, "GITHUB_API_URL": url, "GITHUB_GRAPHQL_URL": f"{url}/graphql", "GITHUB_REPOSITORY": REPO}
    env["GITHUB_TOKEN"] = "test-token" if routes else ""
    result = subprocess.run([sys.executable, str(HOOK), str(tmp / "event.json")], capture_output=True, text=True, env=env, cwd=repo)
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
    for entry in CASES:
        name, expect, ok = entry[0], entry[5], entry[6]
        with tempfile.TemporaryDirectory() as tmp:
            code, output = run(entry, server, Path(tmp))
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
