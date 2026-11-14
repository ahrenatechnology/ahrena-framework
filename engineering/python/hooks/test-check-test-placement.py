#!/usr/bin/env python3
"""Tests for check-test-placement.py.

The condition is one sentence: a Python module that holds a unit has its test
beside it, as `<stem>_test.py` in the same folder. The cases pin it, and pin
what is not a unit: a module of protocols only, of constants only, a package
initialiser, an entry module, a `conftest.py`, a script whose name cannot be
imported, and anything under a `tests` directory.

The criteria of the issue this suite was written for:

    #286/AC-3 the hook's condition has a case here that failed against an
              accepting stub before the hook existed, and passes

Usage:
    python3 engineering/python/hooks/test-check-test-placement.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-test-placement.py"

FUNCTION_UNIT = '''
def fee(amount: int) -> int:
    return amount // 100
'''

ASYNC_UNIT = '''
async def fetch(key: str) -> bytes:
    return key.encode()
'''

CLASS_UNIT = '''
class Ledger:
    pass
'''

UNIT_TEST = '''
from billing.domain.fees import fee


def test_fee_is_a_hundredth() -> None:
    assert fee(500) == 5
'''

PORTS_ONLY = '''
from typing import Protocol


class Clock(Protocol):
    def now(self) -> int: ...
'''

PORTS_AND_A_FUNCTION = '''
from typing import Protocol


class Clock(Protocol):
    def now(self) -> int: ...


def tomorrow(clock: Clock) -> int:
    return clock.now() + 86400
'''

CONSTANTS_ONLY = '''
LIMIT = 10
NAMES = ("a", "b")
'''

BROKEN = "def unclosed(:\n"


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case(
        "a module with a function and no test beside it fails",
        {"billing/domain/fees.py": FUNCTION_UNIT},
        ["[test-placement] condition 1", "billing/domain/fees.py:1", "fees_test.py"],
    ),
    case(
        "a module with a coroutine and no test beside it fails",
        {"billing/infra/client.py": ASYNC_UNIT},
        ["[test-placement] condition 1", "client_test.py"],
    ),
    case(
        "a module with a class and no test beside it fails",
        {"billing/domain/ledger.py": CLASS_UNIT},
        ["[test-placement] condition 1", "ledger_test.py"],
    ),
    case(
        "a module with its test beside it passes",
        {"billing/domain/fees.py": FUNCTION_UNIT, "billing/domain/fees_test.py": UNIT_TEST},
        ["2 file(s), no failures"],
        ok=True,
    ),
    case(
        "a test in another folder does not count",
        {"billing/domain/fees.py": FUNCTION_UNIT, "tests/unit/fees_test.py": UNIT_TEST},
        ["[test-placement] condition 1", "fees_test.py"],
    ),
    case(
        "a test_ prefix beside it is not the form",
        {"billing/domain/fees.py": FUNCTION_UNIT, "billing/domain/test_fees.py": UNIT_TEST},
        ["[test-placement] condition 1"],
    ),
    case(
        "a module of protocols only is not a unit",
        {"billing/application/ports.py": PORTS_ONLY},
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "a protocol beside a function does not exempt the function",
        {"billing/application/ports.py": PORTS_AND_A_FUNCTION},
        ["[test-placement] condition 1"],
    ),
    case(
        "constants, initialisers, entry modules, conftest and unimportable scripts are not units",
        {
            "billing/settings.py": CONSTANTS_ONLY,
            "billing/__init__.py": FUNCTION_UNIT,
            "billing/__main__.py": FUNCTION_UNIT,
            "billing/conftest.py": FUNCTION_UNIT,
            "scripts/check-fees.py": FUNCTION_UNIT,
        },
        ["5 file(s), no failures"],
        ok=True,
    ),
    case(
        "a file under a tests directory is not a unit",
        {"tests/integration/helpers.py": FUNCTION_UNIT},
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "a file this interpreter cannot parse is skipped, not failed",
        {"billing/settings.py": CONSTANTS_ONLY, "billing/broken.py": BROKEN},
        ["1 file(s), no failures (1 skipped)"],
        ok=True,
    ),
    case(
        "generated, vendored and dot-prefixed trees are not walked",
        {
            "billing/settings.py": CONSTANTS_ONLY,
            "node_modules/vendor/b.py": FUNCTION_UNIT,
            ".venv/lib/c.py": CLASS_UNIT,
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
