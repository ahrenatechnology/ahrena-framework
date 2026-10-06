#!/usr/bin/env python3
"""Tests for guard-push.py.

A guard that never refuses is as broken as one that refuses everything, so each
case pins either a push that must be stopped or a command that must run
untouched. Each case pipes a Claude Code PreToolUse payload into the guard, run
as a subprocess inside a scratch repository checked out on a named branch, and
asserts on the exit code (0 runs the command, 2 refuses it) and on stderr.

The harness-generated names that reached barte-ai-services/gatekeeper on
2026-09-28 (#222 to #224) are cases, because they are why the guard exists.

The suite is the one #113/AC-4 asks for, and CI runs it.

Usage:
    python3 contributing/hooks/test-guard-push.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "guard-push.py"

HARNESS = "claude/inspiring-lederberg-d27283"
GOOD = "feat/113-branch-name-before-push"


def case(name: str, branch: str, command: str, *refused_with: str) -> tuple:
    """A command is expected to be refused exactly when the case names what the refusal says."""
    return (name, branch, command, bool(refused_with), refused_with)


CASES = [
    # #113/AC-1: a push from a failing branch is refused, naming the branch
    case("a harness-generated name is refused", HARNESS, "git push -u origin",
         HARNESS, "[branch-naming] condition 1", "git branch -m"),
    case("a bare push reads the current branch", HARNESS, "git push", HARNESS),
    case("a push later in a chain is still seen", HARNESS,
         "git add -A && git commit -m x && git push -u origin", HARNESS),
    case("a push on its own line is seen", HARNESS, "git status\ngit push", HARNESS),
    case("a redirected push is not read as carrying a refspec", GOOD,
         "git push -u origin 2>&1 > /dev/null"),
    case("the refspec's destination is judged, not the local branch", HARNESS,
         f"git push origin HEAD:{GOOD}"),
    case("a bad destination is refused from a good branch", GOOD,
         "git push origin HEAD:claude/x-1a2b3c", "claude/x-1a2b3c"),
    case("a named branch is judged", GOOD, "git push origin wip/42-oauth2",
         "[branch-naming] condition 2"),
    case("refs/heads/ is stripped from the destination", GOOD,
         f"git push origin +HEAD:refs/heads/{GOOD}"),
    # #113/AC-3: a passing branch pushes, and the commands below that are not a push run untouched
    case("a passing branch pushes", GOOD, "git push -u origin"),
    case("git -C reads the branch in that directory", GOOD, "git -C {repo} push"),
    # #113/AC-2: trunk, release/ and HEAD sit outside the rule through check-branch-name's own outside()
    case("trunk is outside the rule", "main", "git push origin main"),
    case("a release branch is outside the rule", "release/1.4", "git push"),
    case("a delete creates no branch", HARNESS, "git push origin --delete old-name"),
    case("tags alone create no branch", HARNESS, "git push --tags"),
    case("a tag refspec creates no branch", HARNESS, "git push origin refs/tags/v1.0"),
    case("git push inside a quoted message is not a push", HARNESS,
         "git commit -m 'then git push'"),
    case("echoing the words is not a push", HARNESS, 'echo "git push origin"'),
    case("another git subcommand is not a push", HARNESS, "git log --grep push"),
    case("an unbalanced quote is not guessed at", HARNESS, "git push 'oops"),
]


def scratch_repo(root: Path, branch: str) -> Path:
    repo = root / "repo"
    subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True)
    return repo


def run(payload: dict, repo: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=repo,
    )
    return result.returncode, result.stdout + result.stderr


def bash(command: str) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}


def problems_for(refused: bool, expect: tuple, code: int, output: str) -> list[str]:
    found = []
    if refused and code != 2:
        found.append(f"expected the push to be refused (exit 2), got exit {code}")
    if not refused and code != 0:
        found.append(f"expected the command to run (exit 0), got exit {code}")
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def check(name: str, problems: list[str], output: str) -> bool:
    if not problems:
        print(f"ok    {name}")
        return True
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")
    return False


def outcomes() -> list[bool]:
    results = []
    for name, branch, command, refused, expect in CASES:
        with tempfile.TemporaryDirectory() as root:
            repo = scratch_repo(Path(root), branch)
            code, output = run(bash(command.format(repo=repo)), repo)
        results.append(check(name, problems_for(refused, expect, code, output), output))
    with tempfile.TemporaryDirectory() as root:
        repo = scratch_repo(Path(root), HARNESS)
        payload = {"tool_name": "Read", "tool_input": {"file_path": "git push"}}
        code, output = run(payload, repo)
    results.append(check("a tool other than Bash is not judged", problems_for(False, (), code, output), output))
    return results


def main() -> int:
    results = outcomes()
    failed = results.count(False)
    print()
    if failed:
        print(f"{failed} of {len(results)} cases failed.")
        return 1
    print(f"{len(results)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
