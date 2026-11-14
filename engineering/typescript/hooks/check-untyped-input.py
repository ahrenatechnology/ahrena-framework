#!/usr/bin/env python3
"""Detector for condition 2 of the TypeScript runtime-validation rule.

Decides one of the conditions stated in
engineering/typescript/rules/runtime-validation.md:

    2. a value that enters untyped is not given a type by assertion: no
       `as T` or `<T>` applied to `JSON.parse(...)`, to a `.json()` body, or
       to a `process.env` read, unless `T` is `unknown`

These three are the entries whose untyped-ness is written in the standard
library's own declarations: `JSON.parse` returns `any` and `Body.json()`
returns `Promise<any>` in TypeScript's `lib.es5.d.ts` and `lib.dom.d.ts`, and
`process.env` is a record of `string | undefined` in `@types/node`. An
assertion on one of them is a claim about data nobody has looked at, and it
is the shape the rule replaces with a schema parse.

Condition 1, that every boundary parses what enters it, needs a reader: what
a boundary is depends on the program. This hook decides the shape that is
spelled the same way in every program.

Usage:
    python3 engineering/typescript/hooks/check-untyped-input.py [path ...]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import re  # noqa: E402
from pathlib import Path  # noqa: E402

from tssource import TYPESCRIPT, Finding, Source, closing, display, load, report, walk  # noqa: E402

RULE = "runtime-validation"

PARSE_CALL = re.compile(r"\bJSON\s*\.\s*parse\s*\(")
BODY_CALL = re.compile(r"\.\s*json\s*\(\s*\)")
ENV_READ = re.compile(r"\bprocess\s*\.\s*env\s*(?:\.\s*[A-Za-z_$][\w$]*|\[[^\]]*\])")
ANGLE_ON_PARSE = re.compile(r"<\s*(?!unknown\s*>)[A-Za-z_$][^<>]*>\s*JSON\s*\.\s*parse\s*\(")
ASSERTION = re.compile(r"\s*\)*\s*as\s+(?!unknown\b)(?!const\b)")


def asserted_after(code: str, end: int) -> bool:
    """Whether `as T` follows, through any closing parentheses, with T not unknown."""
    return ASSERTION.match(code, end) is not None


def flag(source: Source, offset: int, entry: str, findings: list[Finding]) -> None:
    line = source.line(offset)
    findings.append(
        Finding(RULE, f"{source.rel}:{line}", 2, f"{entry} is asserted to a type nobody checked; parse it with a schema, or assert to unknown and narrow")
    )


def check_source(source: Source, findings: list[Finding]) -> None:
    code = source.code
    for match in PARSE_CALL.finditer(code):
        close = closing(code, match.end() - 1)
        if close != -1 and asserted_after(code, close + 1):
            flag(source, match.start(), "JSON.parse", findings)
    for match in ANGLE_ON_PARSE.finditer(code):
        flag(source, match.start(), "JSON.parse", findings)
    for match in BODY_CALL.finditer(code):
        if asserted_after(code, match.end()):
            flag(source, match.start(), "a .json() body", findings)
    for match in ENV_READ.finditer(code):
        if asserted_after(code, match.end()):
            flag(source, match.start(), "process.env", findings)


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    files = walk(roots, TYPESCRIPT)
    for path in files:
        check_source(load(path, display(path, base)), findings)
    return report(findings, len(files))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
