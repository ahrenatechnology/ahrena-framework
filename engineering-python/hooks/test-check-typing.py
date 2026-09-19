#!/usr/bin/env python3
"""Tests for check-typing.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing fixture and by the carve-out it must not
flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

The carve-outs are where the work is. Condition 2 must not ask a method to
annotate its receiver and must not ask an `__init__` for the return type mypy
itself does not ask for. Condition 3 must accept a reason and refuse a tool
directive. Condition 4 must let an immutable default and an unrelated call
through. Condition 5 must stay quiet on a handler that names the exception it
caught, that logs it, that re-raises it, or that names the failure it absorbs.

Usage:
    python3 engineering-python/hooks/test-check-typing.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-typing.py"

CLEAN = '''
def add(left: int, right: int) -> int:
    return left + right
'''

# --- condition 2: every parameter and every return is annotated -------------

UNANNOTATED_PARAMETER = '''
def add(left, right: int) -> int:
    return left + right
'''

NO_RETURN = '''
def add(left: int, right: int):
    return left + right
'''

# The receiver is positional, not named: a method that calls it something else
# still has one, and a staticmethod has none.
RECEIVERS = '''
class Ledger:
    def total(self) -> int:
        return 0

    @classmethod
    def empty(cls) -> "Ledger":
        return cls()
'''

STATIC_HAS_NO_RECEIVER = '''
class Ledger:
    @staticmethod
    def total(rows) -> int:
        return len(rows)
'''

# mypy's own exemption: an __init__ with an annotated parameter needs no
# return type. A hook that disagreed with the checker the rule requires would
# be reporting a state that checker calls correct.
INIT_WITH_ANNOTATION = '''
class Ledger:
    def __init__(self, rows: int):
        self.rows = rows
'''

INIT_WITH_NOTHING = '''
class Ledger:
    def __init__(self):
        self.rows = 0
'''

VARIADIC = '''
def collect(*rows, **options) -> int:
    return len(rows) + len(options)
'''

# A lambda has nowhere to put an annotation, so condition 2 does not reach it.
LAMBDA = '''
double = lambda value: value * 2
'''

# --- condition 3: an `Any` carries its reason -------------------------------

BARE_ANY = '''
from typing import Any


def parse(payload: Any) -> None:
    return None
'''

REASON_ON_THE_LINE = '''
from typing import Any


def parse(payload: Any) -> None:  # the upstream client hands back an untyped dict
    return None
'''

REASON_ABOVE = '''
from typing import Any


# the upstream client hands back an untyped dict
def parse(payload: Any) -> None:
    return None
'''

DIRECTIVE_IS_NOT_A_REASON = '''
from typing import Any


def parse(payload: Any) -> None:  # type: ignore[misc]
    return None
'''

DOTTED_ANY = '''
import typing


def parse(payload: typing.Any) -> None:
    return None
'''

# --- condition 4: no default is mutable -------------------------------------

LIST_DEFAULT = '''
def collect(rows: list[int] = []) -> int:
    return len(rows)
'''

BUILDER_DEFAULT = '''
def collect(rows: dict[str, int] = dict()) -> int:
    return len(rows)
'''

KEYWORD_ONLY_DEFAULT = '''
def collect(*, rows: set[int] = set()) -> int:
    return len(rows)
'''

# A tuple is immutable and Decimal is not in Ruff's B006 list. Both pass, and
# that is the closed list doing its job.
IMMUTABLE_DEFAULTS = '''
from decimal import Decimal


def collect(rows: tuple[int, ...] = (), price: Decimal = Decimal("0")) -> int:
    return len(rows) + int(price)
'''

LAMBDA_DEFAULT = '''
collect = lambda rows=[]: len(rows)
'''

# --- condition 5: no handler discards what it caught ------------------------

SWALLOWED = '''
def load(path: str) -> str:
    try:
        return open(path).read()
    except Exception:
        return ""
'''

BARE_AND_SILENT = '''
def load(path: str) -> None:
    try:
        open(path).close()
    except:
        pass
'''

RE_RAISED = '''
class LoadFailed(Exception):
    pass


def load(path: str) -> str:
    try:
        return open(path).read()
    except Exception as error:
        raise LoadFailed(path) from error
'''

LOGGED = '''
import logging


def load(path: str) -> str:
    try:
        return open(path).read()
    except Exception:
        logging.exception("could not read %s", path)
        return ""
'''

NAMES_THE_EXCEPTION = '''
def load(path: str) -> str:
    try:
        return open(path).read()
    except Exception as error:
        return str(error)
'''

# A handler naming the failure it absorbs is a decision, and this condition
# does not read decisions. Only `except:` and `except Exception:` are read.
NAMES_THE_FAILURE = '''
def load(path: str) -> str:
    try:
        return open(path).read()
    except OSError:
        return ""
'''

# A bare handler has no name to bind, so sys.exc_info() is how it takes hold
# of what it caught.
REACHES_FOR_IT = '''
import sys


def load(path: str) -> str:
    try:
        return open(path).read()
    except:
        caught = sys.exc_info()[0]
        return str(caught)
'''

# --- the walk itself ---------------------------------------------------------

BROKEN = "def unclosed(:\n"

EVERYTHING = '''
from typing import Any


def collect(rows, payload: Any, seen: list[int] = []):
    try:
        return len(rows) + len(payload) + len(seen)
    except Exception:
        return 0
'''


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case("an annotated module passes", {"a.py": CLEAN}, ["1 file(s), no failures"], ok=True),
    # --- condition 2
    case(
        "an unannotated parameter fails",
        {"a.py": UNANNOTATED_PARAMETER},
        ["[typing] condition 2", "add does not annotate left", "a.py:2"],
    ),
    case(
        "a missing return type fails",
        {"a.py": NO_RETURN},
        ["[typing] condition 2", "add declares no return type"],
    ),
    case(
        "self and cls are not parameters a method annotates",
        {"a.py": RECEIVERS},
        ["no failures"],
        ok=True,
    ),
    case(
        "a staticmethod has no receiver, so its first parameter is annotated",
        {"a.py": STATIC_HAS_NO_RECEIVER},
        ["[typing] condition 2", "total does not annotate rows"],
    ),
    case(
        "an __init__ with an annotated parameter needs no return type",
        {"a.py": INIT_WITH_ANNOTATION},
        ["no failures"],
        ok=True,
    ),
    case(
        "an __init__ with nothing annotated still owes -> None",
        {"a.py": INIT_WITH_NOTHING},
        ["[typing] condition 2", "__init__ declares no return type"],
    ),
    case(
        "*args and **kwargs are annotated like any other parameter",
        {"a.py": VARIADIC},
        ["[typing] condition 2", "collect does not annotate rows, options"],
    ),
    case("a lambda is not reported", {"a.py": LAMBDA}, ["no failures"], ok=True),
    # --- condition 3
    case(
        "an Any with no comment fails",
        {"a.py": BARE_ANY},
        ["[typing] condition 3", "no comment says why", "a.py:5"],
    ),
    case(
        "a reason on the same line satisfies it",
        {"a.py": REASON_ON_THE_LINE},
        ["no failures"],
        ok=True,
    ),
    case("a reason on the line above satisfies it", {"a.py": REASON_ABOVE}, ["no failures"], ok=True),
    case(
        "a tool directive is not a reason",
        {"a.py": DIRECTIVE_IS_NOT_A_REASON},
        ["[typing] condition 3"],
    ),
    case("typing.Any is the same Any", {"a.py": DOTTED_ANY}, ["[typing] condition 3"]),
    # --- condition 4
    case(
        "a list literal default fails",
        {"a.py": LIST_DEFAULT},
        ["[typing] condition 4", "a mutable literal", "evaluated once when the `def` runs"],
    ),
    case(
        "a call to a builder default fails",
        {"a.py": BUILDER_DEFAULT},
        ["[typing] condition 4", "a call to dict()"],
    ),
    case(
        "a keyword-only default is read too",
        {"a.py": KEYWORD_ONLY_DEFAULT},
        ["[typing] condition 4", "a call to set()"],
    ),
    case(
        "an immutable default and an unrelated call both pass",
        {"a.py": IMMUTABLE_DEFAULTS},
        ["no failures"],
        ok=True,
    ),
    case(
        "a lambda's mutable default is the same defect",
        {"a.py": LAMBDA_DEFAULT},
        ["[typing] condition 4", "a mutable literal"],
    ),
    # --- condition 5
    case(
        "except Exception with a silent body fails",
        {"a.py": SWALLOWED},
        ["[typing] condition 5", "`except Exception:`", "leaves no trace"],
    ),
    case(
        "a bare except that passes fails",
        {"a.py": BARE_AND_SILENT},
        ["[typing] condition 5", "`except:`"],
    ),
    case("a handler that re-raises passes", {"a.py": RE_RAISED}, ["no failures"], ok=True),
    case("a handler that logs passes", {"a.py": LOGGED}, ["no failures"], ok=True),
    case(
        "a handler that names the exception it bound passes",
        {"a.py": NAMES_THE_EXCEPTION},
        ["no failures"],
        ok=True,
    ),
    case(
        "a handler naming the failure it absorbs is not read",
        {"a.py": NAMES_THE_FAILURE},
        ["no failures"],
        ok=True,
    ),
    case(
        "a bare handler reaching for sys.exc_info passes",
        {"a.py": REACHES_FOR_IT},
        ["no failures"],
        ok=True,
    ),
    # --- the walk itself
    case(
        "findings from every condition are reported in one pass",
        {"a.py": EVERYTHING},
        [
            "[typing] condition 2",
            "[typing] condition 3",
            "[typing] condition 4",
            "[typing] condition 5",
        ],
    ),
    case(
        "a file this interpreter cannot parse is skipped, not failed",
        {"a.py": CLEAN, "broken.py": BROKEN},
        ["1 file(s), no failures (1 skipped)"],
        ok=True,
    ),
    case(
        "generated, vendored and dot-prefixed trees are not walked",
        {
            "a.py": CLEAN,
            "node_modules/vendor/b.py": UNANNOTATED_PARAMETER,
            "__pycache__/c.py": BARE_ANY,
            ".venv/lib/d.py": SWALLOWED,
        },
        ["1 file(s), no failures"],
        ok=True,
    ),
]


def write(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp), files)
        result = subprocess.run([sys.executable, str(HOOK), "."], cwd=tmp, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    """What went wrong with this case, or nothing."""
    wanted = "pass" if ok else "fail"
    found = [] if ok == (code == 0) else [f"expected the hook to {wanted}, it did the other"]
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def report_failure(name: str, problems: list[str], output: str) -> None:
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")


def summarise(failed: int, total: int) -> int:
    print()
    if failed:
        print(f"{failed} of {total} cases failed.")
        return 1
    print(f"{total} cases passed.")
    return 0


def main() -> int:
    failed = 0
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            report_failure(name, problems, output)
        else:
            print(f"ok    {name}")
    return summarise(failed, len(CASES))


if __name__ == "__main__":
    sys.exit(main())
