#!/usr/bin/env python3
"""Tests for check-boundaries.py.

A cycle detector that never accepts is as broken as one that never rejects, so
every condition below is pinned by a failing fixture and by the carve-out it
must not flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

The four cases that make an import graph hard each get a pair: a relative
import, an `__init__.py` re-export, a `TYPE_CHECKING` guard and a deferred
function-level import, one fixture where the hook must fire and one where it
must stay quiet.

Usage:
    python3 engineering-python/hooks/test-check-boundaries.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-boundaries.py"

# --- condition 1: the graph is acyclic -------------------------------------

STRAIGHT_A = '''
from pkg.b import helper


def run():
    return helper()
'''

STRAIGHT_B = '''
def helper():
    return 1
'''

CYCLE_A = '''
from pkg.b import helper


def run():
    return helper()
'''

CYCLE_B = '''
from pkg.a import run


def helper():
    return run()
'''

THREE_A = "from pkg.b import second\n"
THREE_B = "from pkg.c import third\n"
THREE_C = "from pkg.a import first\n"

# One component, two loops through it: a <-> b and a <-> c.
TWO_LOOPS_A = "from pkg.b import second\nfrom pkg.c import third\n"
BACK_TO_A = "from pkg.a import first\n"

# --- condition 3: a deferred import is the same edge -----------------------

# The workaround this rule exists to reject: the import moved inside the
# function, the coupling untouched, and a naive detector satisfied.
DEFERRED_BACK = '''
def helper():
    from pkg.a import run

    return run()
'''

# A deferred import that closes no cycle is nobody's business. Pinned so the
# condition is not read as a ban on function-level imports.
DEFERRED_CLEAN = '''
def helper():
    from pkg.c import third

    return third()
'''

# --- condition 4: TYPE_CHECKING ---------------------------------------------

TYPING_ANNOTATION = '''
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.a import Runner


def helper(runner: Runner) -> Runner:
    return runner
'''

TYPING_RUNTIME = '''
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.a import Runner


def helper(runner):
    return isinstance(runner, Runner)
'''

TYPING_HOST = '''
from pkg.b import helper


class Runner:
    def go(self):
        return helper(self)
'''

# --- the __init__.py re-export ----------------------------------------------

REEXPORT_INIT = "from pkg.a import Thing\n"
REEXPORT_A = '''
from pkg import helper


class Thing:
    pass
'''

# Importing a submodule of another package runs that package's initializer
# first, so the initializer is on the path and belongs in the graph.
OUTSIDE_A = "import pkg.x\n"
OUTSIDE_INIT = "from other.b import B\n"
OUTSIDE_B = "from other.a import A\n"
OUTSIDE_X = "VALUE = 1\n"

# A module does not get an implicit edge to its own package initializer: by the
# time it runs, that initializer has already run. Without the carve-out every
# package whose __init__ re-exports its own submodules would be reported.
OWN_INIT = "from .a import A\n"
OWN_A = "from .b import B\n"
OWN_B = "B = 1\n"

# --- relative imports -------------------------------------------------------

RELATIVE_A = "from . import b\n"
RELATIVE_B = "from .a import thing\n"

# --- condition 2: a layer imports only downward -----------------------------

PYPROJECT = '[project]\nname = "layer"\nversion = "0.1.0"\n'

DOWNWARD = "from components.billing.domain.invoice import Invoice\n"
UPWARD = "from components.billing.infra.repository import Repository\n"
LEAF = "class Invoice:\n    pass\n"
REPOSITORY = "class Repository:\n    pass\n"


def layered(extra: dict[str, str]) -> dict[str, str]:
    """A components/ tree that satisfies conditions 5 and 6, plus the case."""
    files = {
        "components/billing/domain/pyproject.toml": PYPROJECT,
        "components/billing/domain/invoice.py": LEAF,
        "components/billing/application/pyproject.toml": PYPROJECT,
        "components/billing/infra/pyproject.toml": PYPROJECT,
        "components/billing/infra/repository.py": REPOSITORY,
    }
    files.update(extra)
    return files


# --- the walk itself ---------------------------------------------------------

THIRD_PARTY = '''
import json

import requests

from collections.abc import Iterator
'''

BROKEN = "def unclosed(:\n"


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case(
        "a tree with no cycle passes",
        {"pkg/a.py": STRAIGHT_A, "pkg/b.py": STRAIGHT_B},
        ["2 file(s), no failures"],
        ok=True,
    ),
    case(
        "an import of a package that is not in the tree is not a node",
        {"pkg/a.py": THIRD_PARTY},
        ["no failures"],
        ok=True,
    ),
    # --- condition 1
    case(
        "a two-module cycle fails",
        {"pkg/a.py": CYCLE_A, "pkg/b.py": CYCLE_B},
        [
            "[module-boundaries] condition 1",
            "import cycle through 2 module(s)",
            "pkg/a.py",
            "pkg/b.py",
        ],
    ),
    case(
        "a cycle is reported as the cycle, naming every module in it",
        {"pkg/a.py": THREE_A, "pkg/b.py": THREE_B, "pkg/c.py": THREE_C},
        [
            "import cycle through 3 module(s)",
            "pkg/a.py:1 -> pkg/b.py:1 -> pkg/c.py:1 -> pkg/a.py",
        ],
    ),
    case(
        "one cycle is reported per strongly connected component",
        # a <-> b and a <-> c are one component; two findings for one knot is
        # noise, and breaking it re-runs the detector. The rule says so.
        {"pkg/a.py": TWO_LOOPS_A, "pkg/b.py": BACK_TO_A, "pkg/c.py": BACK_TO_A},
        ["1 failure(s)"],
    ),
    # --- condition 3: the deferred-import workaround
    case(
        "an import moved inside a function does not break the cycle",
        {"pkg/a.py": CYCLE_A, "pkg/b.py": DEFERRED_BACK},
        [
            "[module-boundaries] condition 1",
            "(deferred)",
            "an import moved inside a function is the same edge",
        ],
    ),
    case(
        "a deferred import that closes no cycle passes",
        {"pkg/a.py": CYCLE_A, "pkg/b.py": DEFERRED_CLEAN, "pkg/c.py": STRAIGHT_B},
        ["no failures"],
        ok=True,
    ),
    # --- condition 4: TYPE_CHECKING
    case(
        "a TYPE_CHECKING import used only in an annotation is not an edge",
        {"pkg/a.py": TYPING_HOST, "pkg/b.py": TYPING_ANNOTATION},
        ["no failures"],
        ok=True,
    ),
    case(
        "a TYPE_CHECKING import used at runtime is an edge like any other",
        {"pkg/a.py": TYPING_HOST, "pkg/b.py": TYPING_RUNTIME},
        ["[module-boundaries] condition 1", "import cycle through 2 module(s)"],
    ),
    # --- __init__.py
    case(
        "an __init__ re-export that closes a loop with its own submodule fails",
        {"pkg/__init__.py": REEXPORT_INIT, "pkg/a.py": REEXPORT_A},
        ["import cycle through 2 module(s)", "pkg/__init__.py"],
    ),
    case(
        "importing another package's submodule puts its initializer on the path",
        {
            "other/a.py": OUTSIDE_A,
            "other/b.py": OUTSIDE_B,
            "pkg/__init__.py": OUTSIDE_INIT,
            "pkg/x.py": OUTSIDE_X,
        },
        ["import cycle through 3 module(s)", "pkg/__init__.py"],
    ),
    case(
        "a module gets no implicit edge to its own package initializer",
        {"pkg/__init__.py": OWN_INIT, "pkg/a.py": OWN_A, "pkg/b.py": OWN_B},
        ["no failures"],
        ok=True,
    ),
    # --- relative imports
    case(
        "a relative import is resolved and can close a cycle",
        {"pkg/a.py": RELATIVE_A, "pkg/b.py": RELATIVE_B},
        ["import cycle through 2 module(s)", "pkg/a.py", "pkg/b.py"],
    ),
    # --- condition 2: direction
    case(
        "an application module importing infra fails",
        layered({"components/billing/application/service.py": UPWARD}),
        [
            "[module-boundaries] condition 2",
            "application",
            "infra",
            "components/billing/application/service.py",
        ],
    ),
    case(
        "an infra module importing domain passes",
        layered({"components/billing/infra/adapter.py": DOWNWARD}),
        ["no failures"],
        ok=True,
    ),
    case(
        "a deferred import across a layer boundary is still the wrong direction",
        layered(
            {
                "components/billing/application/service.py": (
                    "def run():\n"
                    "    from components.billing.infra.repository import Repository\n\n"
                    "    return Repository\n"
                )
            }
        ),
        ["[module-boundaries] condition 2", "deferred"],
    ),
    # --- condition 5: the namespace root
    case(
        "an __init__.py at the namespace root fails",
        layered({"components/__init__.py": "", "components/billing/infra/adapter.py": DOWNWARD}),
        ["[module-boundaries] condition 5", "components/__init__.py"],
    ),
    case(
        "an __init__.py at a context root fails",
        layered({"components/billing/__init__.py": ""}),
        ["[module-boundaries] condition 5", "components/billing/__init__.py"],
    ),
    # --- condition 6: a distribution per layer
    case(
        "a layer with no pyproject.toml fails",
        {
            "components/billing/domain/pyproject.toml": PYPROJECT,
            "components/billing/domain/invoice.py": LEAF,
            "components/billing/infra/repository.py": REPOSITORY,
        },
        ["[module-boundaries] condition 6", "components/billing/infra", "pyproject.toml"],
    ),
    # --- the walk itself
    case(
        "findings from every condition are reported in one pass",
        layered(
            {
                "components/__init__.py": "",
                "components/billing/application/service.py": UPWARD,
                "pkg/a.py": CYCLE_A,
                "pkg/b.py": CYCLE_B,
            }
        ),
        [
            "[module-boundaries] condition 1",
            "[module-boundaries] condition 2",
            "[module-boundaries] condition 5",
        ],
    ),
    case(
        "a file this interpreter cannot parse is skipped, not failed",
        {"pkg/a.py": STRAIGHT_A, "pkg/b.py": STRAIGHT_B, "pkg/broken.py": BROKEN},
        ["2 file(s), no failures (1 skipped)"],
        ok=True,
    ),
    case(
        "generated and vendored trees are not walked",
        {
            "pkg/a.py": STRAIGHT_A,
            "pkg/b.py": STRAIGHT_B,
            "node_modules/vendor/a.py": CYCLE_A,
            "node_modules/vendor/b.py": CYCLE_B,
            "__pycache__/c.py": CYCLE_A,
        },
        ["2 file(s), no failures"],
        ok=True,
    ),
]


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(HOOK), "."], cwd=tmp, capture_output=True, text=True
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
