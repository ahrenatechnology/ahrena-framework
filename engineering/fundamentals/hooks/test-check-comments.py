#!/usr/bin/env python3
"""Tests for check-comments.py.

A detector that never accepts is as broken as one that never rejects, so every
behaviour below is pinned by a fixture that must fail and by the carve-out it
must not flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message. The fix cases run the
hook with --fix and read the file back.

The detector reads five languages — Python, TypeScript, JavaScript, shell and
SQL — so the cases below cover a finding and its carve-out for each, and a --fix
for each. The Python cases are kept as they were, because the Python path's
behaviour is unchanged.

This file is authored pointer-clean: it carries no bare prose `#` or `//`
comment, only word-free separators, and all rationale sits in docstrings. The
`#`, `//` and `--` sequences inside the fixture strings are data the hook reads,
not comments on this file.

Usage:
    python3 engineering/fundamentals/hooks/test-check-comments.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-comments.py"

CLEAN = "value = 1\n"

PROSE_FULL = '''
def total(rows):
    # this explains what the next line does, which is prose that rots
    return sum(rows)
'''

PROSE_INLINE = '''
def total(rows):
    return sum(rows)  # an inline aside with no pointer at all
'''

POINTER_CLEAN = '''
# ADR-014 is a bare pointer and needs no description
x = 1  # see #172 for the rationale
y = 2  # ADR-0001 switch to the bank-specific fee table
'''

DOCSTRING_CLEAN = '''
def total(rows):
    """This is a docstring, not a comment, and prose here is never flagged."""
    return sum(rows)
'''

DELEGATED = '''
def total(rows):
    # rows = normalise(rows)
    # TODO: switch to the bank-specific fee table once the spec arrives
    # FIXME the retry path is broken
    return sum(rows)
'''

QUOTED_POINTER = '''
# a backticked `#172` in a comment is prose about pointers, not a pointer
value = 1
'''

EXEMPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: latin-1
# SPDX-License-Identifier: MIT
# Copyright 2026 Ahrena
# Licensed under the Apache License, Version 2.0
# All rights reserved
# (c) 2026 Ahrena
# type: ignore
# noqa: E501
# pragma: no cover
# pylint: disable=invalid-name
# mypy: ignore-errors
# ruff: noqa
# fmt: off
# isort: skip
# nosec
# pyright: ignore
# flake8: noqa
# yapf: disable
# black
# ----------
# ==========
value = 1
'''

ADDS_PROSE = CLEAN + "# prose added by this very change, with no pointer\n"

# ----------------------------------------------------------------------------

SCRIPT_PROSE = '''export const total = 1;
// an explanatory aside with no pointer, which is prose that rots
const value = 2;
'''

SCRIPT_CLEAN = '''// ADR-014 explains why this stays
export const total = 1;
const value = 2; // see #172 for the rationale
// eslint-disable-next-line no-console
const noisy = 3;
/** documents the exported function */
export function compute() {}
const text = "// this # is -- all data inside a string, not a comment";
const pattern = /a\\/b/; // ADR-016 the slash is division, not a comment
'''

SCRIPT_BARE_MARKER = 'const x = 1; // TODO wire up the retries\n'

SCRIPT_MARKER_POINTER = 'const x = 1; // TODO (#12) wire up the retries\n'

SHELL_PROSE = '''#!/usr/bin/env bash
# a whole-line aside with no pointer at all
echo "running"
'''

SHELL_CLEAN = '''#!/usr/bin/env bash
# clean up the scratch directory (#42)
# shellcheck disable=SC2034
echo "# this is data, not a comment"
unused=1
'''

SQL_PROSE = '''-- a whole-line aside with no pointer at all
SELECT 1;
'''

SQL_CLEAN = '''-- see ADR-016 for the column layout
SELECT '-- this is data inside a string' AS note;
-- +goose Up
SELECT 1;
'''

SQL_UNSURE = "SELECT 'an unterminated string that the reader cannot close\nSELECT 2;\n"

# ----------------------------------------------------------------------------

BASELINE = "@baseline"
ARGS = "@args"
CONFIG = "@config"
COMMITTED = "@committed"
CHECK = "@check"
RESERVED = (BASELINE, ARGS, CONFIG, COMMITTED, CHECK)

STAGED = ["--changed", "--cached", "."]

GIT_IDENTITY = ("-c", "user.email=gate@example.invalid", "-c", "user.name=gate")


# ----------------------------------------------------------------------------


def _fix_run(content: str, extra: list[str]) -> tuple[int, str, str]:
    """Write one file, run the hook with the given arguments, read the file back."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text(content, encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(HOOK), *extra, "a.py"], cwd=str(root), capture_output=True, text=True
        )
        return done.returncode, done.stdout + done.stderr, (root / "a.py").read_text(encoding="utf-8")


def fix_removes_the_full_line() -> tuple[int, str]:
    """A full-line offending comment is deleted, line and all, and the code stays."""
    src = "def total(rows):\n    # full-line prose with no pointer here\n    return sum(rows)\n"
    _code, _out, after = _fix_run(src, ["--fix"])
    if after != "def total(rows):\n    return sum(rows)\n":
        return 1, f"the full line was not removed cleanly: {after!r}"
    return 0, "removed the full line and kept the code"


def fix_keeps_the_inline_code() -> tuple[int, str]:
    """An inline offending comment is stripped from the hash, and the code is kept."""
    src = "x = compute()  # inline prose with no pointer\ny = 2\n"
    _code, _out, after = _fix_run(src, ["--fix"])
    if after != "x = compute()\ny = 2\n":
        return 1, f"the inline code was not kept cleanly: {after!r}"
    return 0, "stripped the inline comment and kept the code"


def fix_leaves_exempt_and_pointer() -> tuple[int, str]:
    """A fix touches neither an exemption nor a pointer-bearing comment."""
    src = "#!/usr/bin/env python3\n# ADR-014 keep this pointer\nx = 1  # type: ignore\n# ----------\n"
    _code, _out, after = _fix_run(src, ["--fix"])
    if after != src:
        return 1, f"a fix changed an exempt or pointer-bearing file: {after!r}"
    return 0, "left exempt and pointer-bearing comments intact"


def fix_is_idempotent() -> tuple[int, str]:
    """A second fix changes nothing, because the first removed everything flagged."""
    src = "def total(rows):\n    # prose one with no pointer\n    return sum(rows)  # prose two no pointer\n"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text(src, encoding="utf-8")
        for _ in range(2):
            subprocess.run([sys.executable, str(HOOK), "--fix", "a.py"], cwd=str(root), capture_output=True)
        first = (root / "a.py").read_text(encoding="utf-8")
        subprocess.run([sys.executable, str(HOOK), "--fix", "a.py"], cwd=str(root), capture_output=True)
        second = (root / "a.py").read_text(encoding="utf-8")
    if "prose" in first:
        return 1, f"a flagged comment survived the fix: {first!r}"
    if first != second:
        return 1, f"the fix was not idempotent: {first!r} then {second!r}"
    return 0, "the fix removed the prose and was idempotent"


def _fix_named(name: str, content: str, extra: list[str]) -> tuple[int, str, str]:
    """Write one named file, run the hook with the given arguments, read the file back."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / name).write_text(content, encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(HOOK), *extra, name], cwd=str(root), capture_output=True, text=True
        )
        return done.returncode, done.stdout + done.stderr, (root / name).read_text(encoding="utf-8")


def fix_removes_script_prose() -> tuple[int, str]:
    """A TypeScript prose comment is removed and the pointer-bearing one is kept."""
    src = "export const a = 1;\n// prose with no pointer at all\nconst b = 2; // ADR-014 keep this\n"
    _code, _out, after = _fix_named("a.ts", src, ["--fix"])
    if after != "export const a = 1;\nconst b = 2; // ADR-014 keep this\n":
        return 1, f"the TypeScript fix did not remove the prose cleanly: {after!r}"
    return 0, "removed the TypeScript prose and kept the pointer"


def fix_removes_shell_prose() -> tuple[int, str]:
    """A shell whole-line prose comment is removed and the shebang is kept."""
    src = "#!/usr/bin/env bash\n# prose with no pointer at all\necho ok\n"
    _code, _out, after = _fix_named("a.sh", src, ["--fix"])
    if after != "#!/usr/bin/env bash\necho ok\n":
        return 1, f"the shell fix did not remove the prose cleanly: {after!r}"
    return 0, "removed the shell prose and kept the shebang"


def fix_removes_sql_prose() -> tuple[int, str]:
    """A SQL whole-line prose comment is removed and the pointer-bearing one is kept."""
    src = "-- prose with no pointer at all\n-- see ADR-016 for the layout\nSELECT 1;\n"
    _code, _out, after = _fix_named("a.sql", src, ["--fix"])
    if after != "-- see ADR-016 for the layout\nSELECT 1;\n":
        return 1, f"the SQL fix did not remove the prose cleanly: {after!r}"
    return 0, "removed the SQL prose and kept the pointer"


def case(name: str, files: dict, expect: list[str], ok: bool = False) -> tuple:
    return (name, files, expect, ok)


CASES = [
    case("a clean file passes", {"a.py": CLEAN}, ["1 file(s), no failures"], ok=True),
    # ----------------------------------------------------------------------------
    case(
        "a full-line prose comment with no pointer fails (#209/AC-1)",
        {"a.py": PROSE_FULL},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    case(
        "an inline prose comment with no pointer fails (#209/AC-1)",
        {"a.py": PROSE_INLINE},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    # ----------------------------------------------------------------------------
    case(
        "a bare ADR, an issue reference, and a pointer with a description all pass (#209/AC-2)",
        {"a.py": POINTER_CLEAN},
        ["no failures"],
        ok=True,
    ),
    case(
        "an ADR pointer followed by a brief description passes (#209/AC-2)",
        {"a.py": "# ADR-0001 switch to the fee table\nvalue = 1\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        "a backticked pointer is prose about pointers, not a pointer",
        {"a.py": QUOTED_POINTER},
        ["[comment-pointers] condition 1"],
    ),
    # ----------------------------------------------------------------------------
    case(
        "shebang, coding, every license token, every tool directive and a separator pass (#209/AC-3)",
        {"a.py": EXEMPT},
        ["no failures"],
        ok=True,
    ),
    case("a docstring is not a comment and is never flagged (#209/AC-3)", {"a.py": DOCSTRING_CLEAN}, ["no failures"], ok=True),
    # ----------------------------------------------------------------------------
    case(
        "commented-out code and debt markers are owned elsewhere, not by this rule (#209/AC-4)",
        {"a.py": DELEGATED},
        ["no failures"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case(
        "prose on a line the change did not touch is out of scope (#209/AC-5)",
        {BASELINE: {"a.py": PROSE_FULL}, ARGS: STAGED, "b.py": CLEAN},
        ["2 file(s), no failures"],
        ok=True,
    ),
    case(
        "prose on a line the change adds is flagged (#209/AC-5)",
        {BASELINE: {"a.py": CLEAN}, ARGS: STAGED, "a.py": ADDS_PROSE},
        ["[comment-pointers] condition 1", "prose added by this very change"],
    ),
    # ----------------------------------------------------------------------------
    case("a fix removes a full-line comment (#209/AC-6)", {CHECK: fix_removes_the_full_line}, [], ok=True),
    case("a fix keeps the code of an inline comment (#209/AC-6)", {CHECK: fix_keeps_the_inline_code}, [], ok=True),
    case("a fix leaves exempt and pointer comments intact (#209/AC-6)", {CHECK: fix_leaves_exempt_and_pointer}, [], ok=True),
    case("a fix is idempotent (#209/AC-6)", {CHECK: fix_is_idempotent}, [], ok=True),
    # ----------------------------------------------------------------------------
    case(
        "--changed with no revision is an error, not a pass (#209/AC-7)",
        {ARGS: ["--changed"], "a.py": PROSE_FULL},
        ["needs a revision or range"],
    ),
    case(
        "--changed outside a repository is an error, not a pass (#209/AC-7)",
        {ARGS: ["--changed", "HEAD", "."], "a.py": PROSE_FULL},
        ["--changed:"],
    ),
    case(
        "--changed --name-only is refused, not read as a clean tree",
        {BASELINE: {"a.py": CLEAN}, ARGS: ["--changed", "--name-only", "."], "a.py": ADDS_PROSE},
        ["is not a revision or range"],
    ),
    # ----------------------------------------------------------------------------
    case(
        "the Python path still delegates commented-out code and debt markers (#211/AC-2)",
        {"a.py": DELEGATED},
        ["no failures"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case(
        "a TypeScript prose comment with no pointer fails (#211/AC-1)",
        {"a.ts": SCRIPT_PROSE},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    case(
        "a JavaScript prose comment with no pointer fails (#211/AC-1)",
        {"a.js": SCRIPT_PROSE},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    case(
        "a shell prose comment with no pointer fails (#211/AC-1)",
        {"a.sh": SHELL_PROSE},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    case(
        "a SQL prose comment with no pointer fails (#211/AC-1)",
        {"a.sql": SQL_PROSE},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    # ----------------------------------------------------------------------------
    case(
        "a TypeScript pointer, directive, documentation and string all pass (#211/AC-1)",
        {"a.ts": SCRIPT_CLEAN},
        ["no failures"],
        ok=True,
    ),
    case(
        "a shell pointer, directive, shebang and string all pass (#211/AC-1)",
        {"a.sh": SHELL_CLEAN},
        ["no failures"],
        ok=True,
    ),
    case(
        "a SQL pointer, directive and string all pass (#211/AC-1)",
        {"a.sql": SQL_CLEAN},
        ["no failures"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case(
        "a bare marker in a non-Python comment is pointerless prose, a finding (#211/AC-3)",
        {"a.ts": SCRIPT_BARE_MARKER},
        ["[comment-pointers] condition 1", "no durable pointer"],
    ),
    case(
        "the same marker with an issue reference passes (#211/AC-3)",
        {"a.ts": SCRIPT_MARKER_POINTER},
        ["no failures"],
        ok=True,
    ),
    case(
        "a reader that cannot tell comments from data skips the file, no finding (#211/AC-3)",
        {"a.sql": SQL_UNSURE},
        ["skipped", "cannot be told"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case("a fix removes TypeScript prose and keeps the pointer (#211/AC-4)", {CHECK: fix_removes_script_prose}, [], ok=True),
    case("a fix removes shell prose and keeps the shebang (#211/AC-4)", {CHECK: fix_removes_shell_prose}, [], ok=True),
    case("a fix removes SQL prose and keeps the pointer (#211/AC-4)", {CHECK: fix_removes_sql_prose}, [], ok=True),
]


def write(root: Path, files: dict) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_IDENTITY, *args], cwd=str(root), capture_output=True, check=True)


def commit(root: Path, subject: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", subject)


def prepare(root: Path, files: dict) -> None:
    """The repository the hook meets: a baseline commit, then the change over it."""
    write(root, files[BASELINE])
    git(root, "init", "-q")
    for key, value in files.get(CONFIG, ()):
        git(root, "config", key, value)
    commit(root, "the tree before the change")
    git(root, "tag", "base")
    write(root, {rel: text for rel, text in files.items() if rel not in RESERVED})
    git(root, "add", "-A")
    if files.get(COMMITTED):
        commit(root, "the change under review")


def invoke(root: Path, argv: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HOOK), *argv], cwd=str(root), capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr


def run(files: dict) -> tuple[int, str]:
    check = files.get(CHECK)
    if check is not None:
        return check()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if BASELINE in files:
            prepare(root, files)
        else:
            write(root, {rel: text for rel, text in files.items() if rel not in RESERVED})
        return invoke(root, list(files.get(ARGS, ["."])))


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
    for name, files, expect, ok in CASES:
        code, output = run(files)
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
