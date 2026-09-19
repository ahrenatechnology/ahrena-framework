#!/usr/bin/env python3
"""Tests for check-structure.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing fixture and by the carve-out it must not
flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

Usage:
    python3 engineering/hooks/test-check-structure.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-structure.py"

CLEAN = '''
class Ledger:
    def __init__(self, rows):
        self.rows = rows

    def total(self):
        return sum(self.rows)

    def record(self, row):
        self.rows.append(row)
'''

# --- rules/solid.md condition 1: LCOM4 -------------------------------------

TWO_ACTORS = '''
class Order:
    def __init__(self, lines, printer):
        self.lines = lines
        self.printer = printer

    def total(self):
        return sum(self.lines)

    def render(self):
        return self.printer.emit()
'''

CONNECTED_BY_CALL = '''
class Report:
    def __init__(self, rows):
        self.rows = rows

    def body(self):
        return self.rows

    def render(self):
        return "".join(self.body())
'''

PROTOCOL = '''
from typing import Protocol


class Repository(Protocol):
    def load(self, key): ...

    def store(self, key, value): ...
'''

ALL_ABSTRACT = '''
from abc import ABC, abstractmethod


class Gateway(ABC):
    @abstractmethod
    def send(self, message):
        raise NotImplementedError

    @abstractmethod
    def receive(self):
        raise NotImplementedError
'''

ENUM = '''
from enum import Enum


class Colour(Enum):
    RED = 1
    BLUE = 2

    def warm(self):
        return self is Colour.RED

    def cool(self):
        return self is Colour.BLUE
'''

STATIC_ONLY = '''
class Tools:
    def __init__(self, seed):
        self.seed = seed

    def next(self):
        return self.seed + 1

    @staticmethod
    def helper(value):
        return value * 2
'''

# --- rules/solid.md condition 2: a member declared and not implemented -----

UNIMPLEMENTED = '''
class FileStore:
    def __init__(self, root):
        self.root = root

    def load(self, key):
        return self.root / key

    def store(self, key, value):
        """Write the value."""
        raise NotImplementedError
'''

GUARD_CLAUSE = '''
class Codec:
    def __init__(self, formats):
        self.formats = formats

    def decode(self, fmt, payload):
        if fmt not in self.formats:
            raise NotImplementedError(fmt)
        return payload
'''

OVERLOADED = '''
from typing import overload


@overload
def parse(value: int) -> int:
    raise NotImplementedError
'''

# --- rules/kiss.md condition 1: nesting depth ------------------------------

DEEP = '''
def sweep(groups):
    for group in groups:
        for item in group:
            for field in item:
                if field:
                    return field
    return None
'''

AT_THE_LIMIT = '''
def sweep(groups):
    for group in groups:
        for item in group:
            if item:
                return item
    return None
'''

LONG_ELIF = '''
def classify(code):
    if code == 1:
        return "a"
    elif code == 2:
        return "b"
    elif code == 3:
        return "c"
    elif code == 4:
        return "d"
    elif code == 5:
        return "e"
    return "z"
'''

NESTED_DEF = '''
def outer(rows):
    def inner(row):
        for cell in row:
            if cell:
                return cell
        return None

    for row in rows:
        if row:
            return inner(row)
    return None
'''

DEEP_IN_HANDLER = '''
def load(paths):
    for path in paths:
        try:
            return open(path)
        except OSError:
            for retry in range(3):
                if retry:
                    return None
    return None
'''

# --- rules/kiss.md condition 2: a flag argument ----------------------------

FLAG_DEFAULT = '''
def render(doc, pretty=False):
    if pretty:
        return doc.upper()
    return doc
'''

FLAG_ANNOTATED = '''
def render(doc, pretty: bool):
    if not pretty:
        return doc
    return doc.upper()
'''

FLAG_COMPARED = '''
def render(doc, pretty=False):
    if pretty is True:
        return doc.upper()
    return doc
'''

FLAG_STORED = '''
class Renderer:
    def __init__(self, pretty=False):
        self.pretty = pretty

    def render(self, doc):
        if self.pretty:
            return doc.upper()
        return doc
'''

FLAG_FORWARDED = '''
def render(doc, pretty=False):
    return doc.render(pretty=pretty)
'''

NON_BOOLEAN = '''
def render(doc, mode="plain"):
    if mode:
        return doc.upper()
    return doc
'''

# A single delegating hop is a facade, not a defect. The condition that would
# have flagged it was dropped when this fixture showed it firing on every
# collection wrapper; rules/kiss.md records why.
FACADE = '''
class Service:
    def __init__(self, repo):
        self.repo = repo

    def save(self, record):
        return self.repo.save(record)

    def load(self, key):
        return self.repo.load(key)
'''

BROKEN = "def unclosed(:\n"


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> tuple:
    return (name, files, expect, ok)


CASES = [
    case("a clean tree passes", {"a.py": CLEAN}, ["1 file(s), no failures"], ok=True),
    # --- solid, condition 1
    case(
        "a class whose methods share no state fails",
        {"a.py": TWO_ACTORS},
        ["[solid] condition 1", "class Order has LCOM4 = 2", "{render} | {total}"],
    ),
    case(
        "__init__ does not connect the components it touches",
        {"a.py": TWO_ACTORS},
        ["LCOM4 = 2"],
    ),
    case(
        "methods joined only by a sibling call pass",
        {"a.py": CONNECTED_BY_CALL},
        ["no failures"],
        ok=True,
    ),
    case("a Protocol is skipped", {"a.py": PROTOCOL}, ["no failures"], ok=True),
    case("an all-abstract base is skipped", {"a.py": ALL_ABSTRACT}, ["no failures"], ok=True),
    case("an Enum is skipped", {"a.py": ENUM}, ["no failures"], ok=True),
    case(
        "a static method does not form a component of its own",
        {"a.py": STATIC_ONLY},
        ["no failures"],
        ok=True,
    ),
    # --- solid, condition 2
    case(
        "a concrete member that raises NotImplementedError fails",
        {"a.py": UNIMPLEMENTED},
        ["[solid] condition 2", "store is declared and not implemented"],
    ),
    case(
        "an @abstractmethod raising NotImplementedError passes",
        {"a.py": ALL_ABSTRACT},
        ["no failures"],
        ok=True,
    ),
    case(
        "a guard clause raising NotImplementedError passes",
        {"a.py": GUARD_CLAUSE},
        ["no failures"],
        ok=True,
    ),
    case("an @overload stub passes", {"a.py": OVERLOADED}, ["no failures"], ok=True),
    # --- kiss, condition 1
    case(
        "control flow nested 4 deep fails",
        {"a.py": DEEP},
        ["[kiss] condition 1", "sweep nests control flow 4 deep", "the limit is 3"],
    ),
    case("control flow nested 3 deep passes", {"a.py": AT_THE_LIMIT}, ["no failures"], ok=True),
    case("a long elif chain stays at one level", {"a.py": LONG_ELIF}, ["no failures"], ok=True),
    case(
        "a nested def is measured on its own, not on its enclosure",
        {"a.py": NESTED_DEF},
        ["no failures"],
        ok=True,
    ),
    case(
        "depth inside an except handler counts",
        {"a.py": DEEP_IN_HANDLER},
        ["load nests control flow 4 deep"],
    ),
    # --- kiss, condition 2
    case(
        "branching on a boolean-defaulted parameter fails",
        {"a.py": FLAG_DEFAULT},
        ["[kiss] condition 2", "render branches on the boolean parameter 'pretty'"],
    ),
    case(
        "branching on a bool-annotated parameter fails",
        {"a.py": FLAG_ANNOTATED},
        ["branches on the boolean parameter 'pretty'"],
    ),
    case(
        "comparing a boolean parameter against a literal fails",
        {"a.py": FLAG_COMPARED},
        ["branches on the boolean parameter 'pretty'"],
    ),
    case(
        "a boolean stored as state and branched on later passes",
        {"a.py": FLAG_STORED},
        ["no failures"],
        ok=True,
    ),
    case(
        "a boolean passed through without branching passes",
        {"a.py": FLAG_FORWARDED},
        ["no failures"],
        ok=True,
    ),
    case(
        "an ordinary one-hop facade is not a finding",
        {"a.py": FACADE},
        ["no failures"],
        ok=True,
    ),
    case(
        "branching on a non-boolean parameter passes",
        {"a.py": NON_BOOLEAN},
        ["no failures"],
        ok=True,
    ),
    # --- the walk itself
    case(
        # An unimplemented member touches no state, so it is also always its own
        # LCOM4 component. The two findings co-occur by construction and both
        # are reported, because the fixes differ.
        "findings from every condition are reported in one pass",
        {"a.py": DEEP, "b.py": UNIMPLEMENTED},
        [
            "3 failure(s) across 2 file(s)",
            "[kiss] condition 1",
            "[solid] condition 1",
            "[solid] condition 2",
        ],
    ),
    case(
        "a file this interpreter cannot parse is skipped, not failed",
        {"a.py": CLEAN, "broken.py": BROKEN},
        ["1 file(s), no failures (1 skipped)"],
        ok=True,
    ),
    case(
        "generated and vendored trees are not walked",
        {"a.py": CLEAN, "node_modules/pkg/b.py": DEEP, "__pycache__/c.py": DEEP},
        ["1 file(s), no failures"],
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
