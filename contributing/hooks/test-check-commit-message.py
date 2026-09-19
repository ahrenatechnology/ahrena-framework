#!/usr/bin/env python3
"""Tests for check-commit-message.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing commit and by the commit it must not
flag. Each case writes commit objects into a throwaway repository, runs the
hook against it as a subprocess, and asserts on the exit code and the message.

The objects are written with `git hash-object` rather than `git commit`,
because the signature is the subject of condition 6 and a test that needed a
real signing key would need key material in CI to run at all. Writing the
object directly puts the header under the test's control and needs nothing
beyond git.

Usage:
    python3 contributing/hooks/test-check-commit-message.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-commit-message.py"

SSH_SIGNATURE = (
    "gpgsig -----BEGIN SSH SIGNATURE-----\n"
    " U1NIU0lHAAAAAQAAADMAAAALc3NoLWVkMjU1MTkAAAAgrLzsfFISF4by8Q+FKz27\n"
    " -----END SSH SIGNATURE-----"
)

PGP_SIGNATURE = (
    "gpgsig -----BEGIN PGP SIGNATURE-----\n"
    " \n"
    " iJEEABYKADkWIQQDvhvmuUKzL1CUmyRlvOWKPIosBgUCaqytmxsUgAAAAAAEAA5t\n"
    " -----END PGP SIGNATURE-----"
)

UNSIGNED = ""

SEVENTY_TWO = "feat: " + "a" * 66
SEVENTY_THREE = "feat: " + "a" * 67


@dataclass
class Spec:
    """One commit object to write. `parents` above 1 makes it a merge."""

    message: str
    signature: str = SSH_SIGNATURE
    parents: int = 1


def case(name: str, specs: list[Spec], expect: list[str], ok: bool = False) -> tuple:
    return (name, specs, expect, ok, None)


def ranged(name: str, specs: list[Spec], args: list[str], expect: list[str]) -> tuple:
    return (name, specs, expect, False, args)


CASES = [
    case(
        "a conventional, signed, short subject passes",
        [Spec("feat: add the branch-name detector\n")],
        ["1 commit(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "a scope passes, because 13 of this repository's 24 commits carry one",
        [Spec("feat(foundation): cap the body\n")],
        ["1 commit(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "a breaking-change marker passes",
        [Spec("feat(api)!: move the auth endpoint\n")],
        ["1 commit(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "a body after one blank line passes",
        [Spec("fix: stop the gate walking build trees\n\nThe walk followed dist/.\n")],
        ["1 commit(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "an OpenPGP signature satisfies condition 6 as an SSH one does",
        [Spec("chore: initial commit\n", signature=PGP_SIGNATURE)],
        ["1 commit(s), 0 failure(s)"],
        ok=True,
    ),
    # --- condition 1: the subject parses
    case(
        "a subject with no type fails",
        [Spec("updated the login page\n")],
        ["[commit-format] condition 1", "is not 'type(scope): description'"],
    ),
    case(
        "a missing space after the colon fails",
        [Spec("feat:add the detector\n")],
        ["[commit-format] condition 1"],
    ),
    case(
        "an empty description fails",
        [Spec("feat: \n")],
        ["[commit-format] condition 1"],
    ),
    case(
        "an unclosed scope fails",
        [Spec("feat(auth: add the detector\n")],
        ["[commit-format] condition 1"],
    ),
    # --- condition 2: the type
    case(
        "a type outside the eleven fails, and says which eleven",
        [Spec("feature: add a new button\n")],
        ["[commit-format] condition 2", "'feature' is not one of the eleven", "build, chore, ci"],
    ),
    case(
        "a capitalised type fails condition 2 rather than condition 1",
        [Spec("Feat: add the detector\n")],
        ["[commit-format] condition 2", "'Feat' is not one of the eleven"],
    ),
    # --- condition 3: the length
    case(
        "a subject of exactly 72 characters passes",
        [Spec(SEVENTY_TWO + "\n")],
        ["1 commit(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "a subject of 73 characters fails, and says how long it is",
        [Spec(SEVENTY_THREE + "\n")],
        ["[commit-format] condition 3", "73 characters, over the 72"],
    ),
    # --- condition 4: the trailing period
    case(
        "a subject ending in a period fails",
        [Spec("fix: resolve the null pointer.\n")],
        ["[commit-format] condition 4"],
    ),
    # --- condition 5: the blank line
    case(
        "a body on the line after the subject fails",
        [Spec("fix: resolve the null pointer\nIt came from the cache.\n")],
        ["[commit-format] condition 5"],
    ),
    # --- condition 6: the signature
    case(
        "an unsigned commit fails",
        [Spec("feat: add the detector\n", signature=UNSIGNED)],
        ["[commit-format] condition 6", "carries no signature header"],
    ),
    case(
        "an unsigned commit with a bad subject reports both",
        [Spec("added things\n", signature=UNSIGNED)],
        ["1 commit(s), 2 failure(s)", "condition 1", "condition 6"],
    ),
    # --- what the rule does not reach
    case(
        "a merge commit is skipped rather than judged",
        [
            Spec("feat: first\n"),
            Spec("feat: second\n"),
            Spec("Merge pull request #12 from a/b\n", parents=2),
        ],
        ["0 commit(s), 0 failure(s), 1 merge commit(s) skipped"],
        ok=True,
    ),
    # --- the arguments reach git rev-list
    ranged(
        "a walk over several commits judges each one",
        [
            Spec("feat: first\n"),
            Spec("nope: second\n"),
            Spec("feat: third.\n"),
        ],
        ["HEAD"],
        ["3 commit(s), 2 failure(s)", "condition 2", "condition 4"],
    ),
]


def git(root: Path, args: list[str], stdin: str = "") -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, input=stdin, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def write_commit(root: Path, tree: str, parents: list[str], spec: Spec) -> str:
    lines = [f"tree {tree}"]
    lines.extend(f"parent {parent}" for parent in parents)
    lines.append("author A <a@example.test> 1700000000 +0000")
    lines.append("committer A <a@example.test> 1700000000 +0000")
    if spec.signature:
        lines.append(spec.signature)
    raw = "\n".join(lines) + "\n\n" + spec.message
    return git(root, ["hash-object", "-t", "commit", "-w", "--stdin"], raw).strip()


def build(root: Path, specs: list[Spec]) -> None:
    git(root, ["init", "-q", "."])
    git(root, ["symbolic-ref", "HEAD", "refs/heads/main"])
    tree = git(root, ["hash-object", "-t", "tree", "-w", "--stdin"]).strip()
    written: list[str] = []
    for spec in specs:
        parents = written[-spec.parents:] if written else []
        written.append(write_commit(root, tree, parents, spec))
    git(root, ["update-ref", "refs/heads/main", written[-1]])


def run(specs: list[Spec], args: list[str] | None) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build(root, specs)
        result = subprocess.run(
            [sys.executable, str(HOOK), *(args or [])], cwd=tmp, capture_output=True, text=True
        )
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
    failed = 0
    for name, specs, expect, ok, args in CASES:
        code, output = run(specs, args)
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

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
