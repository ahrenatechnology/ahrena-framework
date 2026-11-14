#!/usr/bin/env python3
"""Detector for engineering/python/rules/test-placement.md.

Decides its one condition: a Python module that holds a unit has its test
beside it, as `<stem>_test.py` in the same directory.

A unit is a function, a coroutine or a class defined at the module's top
level. A class that subclasses `Protocol` is not one: it declares a contract
and has no behaviour to test, and its implementations are tested where they
are written. A module with no unit — constants, re-exports, protocols — owes
no test.

These are not read as modules that owe a test, each for a reason the rule
states: a package initialiser (`__init__.py`), an entry module
(`__main__.py`), a `conftest.py`, a test itself (`*_test.py`, `test_*.py`),
anything under a directory named `test` or `tests`, and a file whose stem is
not an identifier, which no `import` statement can name and so no test beside
it can import.

Like its siblings it takes the standard library and nothing else.

Usage:
    python3 engineering/python/hooks/check-test-placement.py [path ...]
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

from sources import MissingPath, display, sources

RULE = "test-placement"
NOT_MODULES = frozenset({"__init__.py", "__main__.py", "conftest.py"})
TEST_DIRECTORIES = frozenset({"test", "tests"})
UNIT_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclass
class Finding:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition 1: {self.message}"


def is_test(path: Path) -> bool:
    return path.stem.endswith("_test") or path.stem.startswith("test_")


def owes_a_test(path: Path) -> bool:
    """Whether this file is a module the condition reads at all."""
    if path.name in NOT_MODULES or is_test(path) or not path.stem.isidentifier():
        return False
    return not any(part in TEST_DIRECTORIES for part in path.parent.parts)


def _is_protocol(node: ast.ClassDef) -> bool:
    for base in node.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
        if name == "Protocol":
            return True
    return False


def units(tree: ast.Module) -> list[str]:
    """The names of the units the module defines at its top level."""
    found: list[str] = []
    for node in tree.body:
        if not isinstance(node, UNIT_TYPES):
            continue
        if isinstance(node, ast.ClassDef) and _is_protocol(node):
            continue
        found.append(node.name)
    return found


def check(path: Path, rel: str, findings: list[Finding]) -> bool:
    """Read one file; return False when it cannot be parsed."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
        print(f"{rel}\n    skipped, this interpreter cannot parse it: {exc}", file=sys.stderr)
        return False
    defined = units(tree)
    sibling = path.with_name(f"{path.stem}_test.py")
    if defined and not sibling.exists():
        listed = ", ".join(defined[:3]) + (", ..." if len(defined) > 3 else "")
        findings.append(
            Finding(
                f"{rel}:1",
                f"this module defines {listed} and has no `{sibling.name}` beside it, so a "
                "reader who opens the unit cannot find what checks it. Write the unit's test "
                f"in `{sibling.name}`, in the same folder",
            )
        )
    return True


def report(findings: list[Finding], checked: int, unparsed: int) -> int:
    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if not findings:
        print(f"{checked} file(s), no failures{suffix}.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
    for finding in sorted(findings, key=lambda item: item.where):
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    unparsed = 0
    try:
        paths = sources(roots)
    except MissingPath as missing:
        print(missing, file=sys.stderr)
        return 2
    for path in paths:
        rel = display(path, base)
        if not owes_a_test(Path(rel)):
            checked += 1
            continue
        if check(path, rel, findings):
            checked += 1
        else:
            unparsed += 1
    return report(findings, checked, unparsed)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
