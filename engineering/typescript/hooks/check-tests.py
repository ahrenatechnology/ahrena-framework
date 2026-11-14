#!/usr/bin/env python3
"""Detector for the conditions in the TypeScript colocated-tests rule.

Decides both conditions stated in engineering/typescript/rules/colocated-tests.md:

    1. a TypeScript source file that holds a unit - a function, an arrow
       function, a class - has a test file beside it: same directory, same
       stem, `.test.` or `.spec.` before a TypeScript extension
    2. a test file in a source directory has the unit it is named for beside it

A file holds a unit when its code, with comments, strings, interfaces and
type aliases blanked, still contains `function`, `class` or `=>`. A module of
types, constants or re-exports holds none and owes no test. A declaration
file, a configuration file (`*.config.ts`) and anything under a directory
named in `SUPPORT_DIRECTORIES` is test support or tooling, not a unit. A test
under such a directory exercises more than one unit by the rule's own
definition, and is neither required nor checked against a sibling.

Usage:
    python3 engineering/typescript/hooks/check-tests.py [path ...]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import re  # noqa: E402
from pathlib import Path  # noqa: E402

from tssource import TYPESCRIPT, Finding, closing, display, load, report, walk  # noqa: E402

RULE = "colocated-tests"

SUPPORT_DIRECTORIES = frozenset({"test", "tests", "__tests__", "__mocks__", "__fixtures__", "fixtures", "e2e", "mocks"})
TEST_MARK = re.compile(r"\.(test|spec)\.[cm]?tsx?$")
CONFIG_MARK = re.compile(r"\.config\.[cm]?tsx?$")
UNIT = re.compile(r"\bfunction\b|\bclass\b|=>")
INTERFACE = re.compile(r"\binterface\s+[A-Za-z_$][\w$]*[^{]*\{")
TYPE_ALIAS = re.compile(r"\btype\s+[A-Za-z_$][\w$]*\s*(<)?")
CONTINUES = set("|&?:=<>.,([{")
OPENERS, CLOSERS = set("([{<"), set(")]}>")


def in_support(relative: Path) -> bool:
    return any(part in SUPPORT_DIRECTORIES for part in relative.parts[:-1])


def without_types(code: str) -> str:
    """The code with every interface body and type alias blanked."""
    chars = list(code)
    for match in INTERFACE.finditer(code):
        close = closing(code, match.end() - 1)
        end = close + 1 if close != -1 else len(code)
        chars[match.start() : end] = " " * (end - match.start())
    for match in TYPE_ALIAS.finditer(code):
        start = closing(code, match.start(1)) + 1 if match.group(1) else match.end()
        equals = code.find("=", start)
        if equals == -1 or code[start:equals].strip():
            continue
        end = alias_end(code, equals + 1)
        chars[match.start() : end] = " " * (end - match.start())
    return "".join(chars)


def alias_end(code: str, at: int) -> int:
    """Where a type alias's body ends: a `;`, or a line break that does not continue it.

    The body continues across a line break when it is inside brackets, when
    the line ends on an operator, or when the next line opens with one, which
    is how a formatter that writes no semicolons breaks a long union.
    """
    depth = 0
    for index in range(at, len(code)):
        char = code[index]
        if char == "=" and code[index + 1 : index + 2] == ">":
            continue
        if char in OPENERS:
            depth += 1
        elif char in CLOSERS and not (char == ">" and code[index - 1] == "="):
            depth -= 1
        elif depth <= 0 and (char == ";" or (char == "\n" and not continued(code, index))):
            return index
    return len(code)


def continued(code: str, newline: int) -> bool:
    before = code[:newline].rstrip()
    after = code[newline:].lstrip()
    return bool(before) and before[-1] in CONTINUES or bool(after) and after[0] in "|&?:=."


def stem_of(path: Path) -> str:
    name = path.name
    for suffix in sorted(TYPESCRIPT, key=len, reverse=True):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def tests_beside(path: Path) -> list[Path]:
    stem = stem_of(path)
    return [path.with_name(f"{stem}.{mark}{suffix}") for mark in ("test", "spec") for suffix in TYPESCRIPT]


def unit_for(test: Path) -> list[Path]:
    stem = TEST_MARK.sub("", test.name)
    return [test.with_name(stem + suffix) for suffix in TYPESCRIPT]


def holds_unit(path: Path, base: Path) -> bool:
    return UNIT.search(without_types(load(path, display(path, base)).code)) is not None


def check_file(path: Path, root: Path, base: Path, findings: list[Finding]) -> None:
    relative = path.relative_to(root) if path.is_relative_to(root) else Path(path.name)
    if path.name.endswith(".d.ts") or CONFIG_MARK.search(path.name) or in_support(relative):
        return
    where = display(path, base)
    if TEST_MARK.search(path.name):
        if not any(candidate.is_file() for candidate in unit_for(path)):
            unit = TEST_MARK.sub("", path.name) + ".ts"
            findings.append(Finding(RULE, where, 2, f"tests a unit that is not beside it ({unit}); move the test with its unit, or delete it"))
        return
    if holds_unit(path, base) and not any(candidate.is_file() for candidate in tests_beside(path)):
        wanted = f"{stem_of(path)}.test{path.suffix}"
        findings.append(Finding(RULE, where, 1, f"holds a unit and has no test beside it; write {wanted} in the same folder"))


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    for root in roots:
        for path in walk([root], TYPESCRIPT):
            check_file(path, root if root.is_dir() else root.parent, base, findings)
            checked += 1
    return report(findings, checked)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
