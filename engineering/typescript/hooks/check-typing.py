#!/usr/bin/env python3
"""Detector for the typing conditions in the TypeScript engineering rule.

Decides five of the seven conditions stated in
engineering/typescript/rules/typing.md:

    2. every tsconfig tsc runs from sets `strict: true`, turns no flag it
       governs off, and turns `noUncheckedIndexedAccess` on
    4. an explicit `any` carries a reason, on its line or the line above
    5. no `@ts-ignore` or `@ts-nocheck`, and a `@ts-expect-error` says why
    6. an assertion through `unknown` or `any` carries a reason
    7. an exported function declares its return type

Conditions 1 and 3 are not decided here and could not be. Whether the
program type-checks is `tsc`'s answer, and whether an `any` arrived by
inference from an untyped library is typescript-eslint's, because both need
the type of every expression. This hook decides the part that the source
spells, and it holds on a project that has installed nothing.

`STRICT_FAMILY` is `strict`, the eight flags `tsc --help --all` defaults to
"`true`, unless `strict` is `false`" in 6.0.3 and 7.0.2, and `alwaysStrict`,
which 5.x let a project turn off; turning one off under `strict: true` reopens
the hole `strict` was set to close, so each is read on its own. `ANY_BEFORE_*` is
what may stand before `any` when it is a type: an annotation colon, a type
argument, a union or intersection, an alias, a conditional, an arrow's return,
and the type operators that take one. `MINIMUM_DESCRIPTION` is
typescript-eslint's `ban-ts-comment` default, three characters; the figure
is theirs.

Usage:
    python3 engineering/typescript/hooks/check-typing.py [path ...]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

from tssource import TYPESCRIPT, Finding, Source, closing, display, load, reason_near, report, scan, walk  # noqa: E402

RULE = "typing"

STRICT_FAMILY = (
    "strict",
    "noImplicitAny",
    "noImplicitThis",
    "alwaysStrict",
    "strictNullChecks",
    "strictFunctionTypes",
    "strictBindCallApply",
    "strictPropertyInitialization",
    "strictBuiltinIteratorReturn",
    "useUnknownInCatchVariables",
)

ANY = re.compile(r"\bany\b")
ANY_BEFORE_CHARS = set(":<,|&(=[?")
ANY_BEFORE_WORDS = frozenset({"as", "extends", "keyof", "satisfies", "is", "readonly", "typeof"})

DOUBLE_ASSERTION = re.compile(r"\bas\s+(unknown|any)\s+as\b")

EXPORTED_FUNCTION = re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\b\s*\*?\s*([A-Za-z_$][\w$]*)?")
EXPORTED_CONST = re.compile(r"\bexport\s+(?:const|let)\s+([A-Za-z_$][\w$]*)\s*(:|=)")

MINIMUM_DESCRIPTION = 3


def read_jsonc(path: Path) -> dict[str, object] | None:
    """A tsconfig as tsc reads it: comments and trailing commas allowed.

    The scan blanks strings as well as comments, and a tsconfig's values are
    strings, so only the comments are blanked here, from their own offsets in
    the raw text.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    _, comments_found = scan(text)
    chars = list(text)
    for comment in comments_found:
        for index in range(comment.start, comment.end):
            if chars[index] != "\n":
                chars[index] = " "
    cleaned = re.sub(r",(\s*[}\]])", r"\1", "".join(chars))
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def resolve_extends(config: Path, specifier: str) -> Path | None:
    if specifier.startswith("."):
        target = (config.parent / specifier).resolve()
        for option in (target, target.with_name(target.name + ".json")):
            if option.is_file():
                return option
        return None
    for directory in [config.parent, *config.parent.parents]:
        candidate = directory / "node_modules" / specifier
        for option in (candidate, candidate.with_name(candidate.name + ".json"), candidate / "tsconfig.json"):
            if option.is_file():
                return option.resolve()
    return None


def extends_of(data: dict[str, object]) -> list[str]:
    value = data.get("extends")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def effective(config: Path, seen: set[Path], unresolved: list[str]) -> dict[str, object]:
    """The compiler options this tsconfig ends up with, bases first."""
    data = read_jsonc(config)
    if data is None or config in seen:
        return {}
    seen.add(config)
    options: dict[str, object] = {}
    for specifier in extends_of(data):
        base = resolve_extends(config, specifier)
        if base is None:
            unresolved.append(specifier)
            continue
        options.update(effective(base, seen, unresolved))
    own = data.get("compilerOptions")
    if isinstance(own, dict):
        options.update(own)
    return options


def tsconfigs(roots: list[Path]) -> list[Path]:
    return [path for path in walk(roots, (".json",)) if path.name.startswith("tsconfig")]


def leaves(configs: list[Path]) -> list[Path]:
    """The tsconfigs no other tsconfig extends: the ones tsc runs from."""
    extended: set[Path] = set()
    for config in configs:
        data = read_jsonc(config) or {}
        for specifier in extends_of(data):
            base = resolve_extends(config, specifier)
            if base is not None:
                extended.add(base)
    return [config for config in configs if config.resolve() not in extended]


def check_compiler_options(roots: list[Path], base: Path, findings: list[Finding]) -> int:
    configs = tsconfigs(roots)
    for config in leaves(configs):
        unresolved: list[str] = []
        options = effective(config.resolve(), set(), unresolved)
        where = display(config, base)
        for flag in STRICT_FAMILY:
            if options.get(flag) is False:
                findings.append(Finding(RULE, where, 2, f"turns {flag} off; delete the line, and fix what the compiler then reports"))
        missing = f" (its base {', '.join(unresolved)} is not installed, so this hook cannot read it)" if unresolved else ""
        if "strict" not in options:
            findings.append(Finding(RULE, where, 2, f"does not set strict{missing}; the default changed in 6.0, so write strict: true"))
        if options.get("noUncheckedIndexedAccess") is not True:
            findings.append(Finding(RULE, where, 2, f"does not turn noUncheckedIndexedAccess on{missing}; set it in compilerOptions"))
    return len(configs)


def previous_token(code: str, offset: int) -> str:
    index = offset - 1
    while index >= 0 and code[index].isspace():
        index -= 1
    if index < 0:
        return ""
    if code[index].isalnum() or code[index] in "_$":
        end = index + 1
        while index >= 0 and (code[index].isalnum() or code[index] in "_$"):
            index -= 1
        return code[index + 1 : end]
    if code[index] == ">" and index > 0 and code[index - 1] == "=":
        return "=>"
    return code[index]


def next_char(code: str, offset: int) -> tuple[str, int]:
    index = offset
    while index < len(code) and code[index].isspace():
        index += 1
    return (code[index], index) if index < len(code) else ("", index)


def is_type_any(code: str, match: re.Match[str]) -> bool:
    before = previous_token(code, match.start())
    after, at = next_char(code, match.end())
    if after in ("(", ".", ":") or (after == "=" and code[at + 1 : at + 2] != ">"):
        return False
    return before in ANY_BEFORE_CHARS or before in ANY_BEFORE_WORDS or before == "=>"


def check_any(source: Source, findings: list[Finding]) -> None:
    """One finding per line: three `any` in one signature are one decision to justify."""
    lines = sorted({source.line(match.start()) for match in ANY.finditer(source.code) if is_type_any(source.code, match)})
    for line in lines:
        if not reason_near(source, line):
            findings.append(
                Finding(RULE, f"{source.rel}:{line}", 4, "an explicit any with no reason beside it; write the type, unknown, or why it cannot be")
            )


def check_directives(source: Source, findings: list[Finding]) -> None:
    for comment in source.comments:
        text = comment.text.strip().lstrip("*").strip()
        where = f"{source.rel}:{comment.start}"
        for banned in ("@ts-ignore", "@ts-nocheck"):
            if re.match(re.escape(banned) + r"\b", text):
                findings.append(Finding(RULE, where, 5, f"{banned} silences every error the line ever has; fix the type, or use a described @ts-expect-error"))
        if re.match(r"@ts-expect-error\b", text):
            description = text[len("@ts-expect-error") :].lstrip(" :-").strip()
            if len(description) < MINIMUM_DESCRIPTION:
                findings.append(Finding(RULE, where, 5, "@ts-expect-error says nothing about the error it expects; describe it after the directive"))


def check_double_assertions(source: Source, findings: list[Finding]) -> None:
    for match in DOUBLE_ASSERTION.finditer(source.code):
        line = source.line(match.start())
        if not reason_near(source, line):
            findings.append(
                Finding(RULE, f"{source.rel}:{line}", 6, f"as {match.group(1)} as discards what the compiler knows; narrow, parse, or say why")
            )


def after_parameters(code: str, at: int) -> tuple[str, int]:
    """From a function's name, skip type parameters and parameters."""
    char, at = next_char(code, at)
    if char == "<":
        close = closing(code, at)
        if close == -1:
            return "", at
        char, at = next_char(code, close + 1)
    if char != "(":
        return "", at
    close = closing(code, at)
    if close == -1:
        return "", at
    return next_char(code, close + 1)


def missing_return(source: Source, name: str, offset: int, findings: list[Finding]) -> None:
    line = source.line(offset)
    findings.append(
        Finding(RULE, f"{source.rel}:{line}", 7, f"exported {name} declares no return type; the inferred one becomes the public contract")
    )


def check_exported_functions(source: Source, findings: list[Finding]) -> None:
    code = source.code
    for match in EXPORTED_FUNCTION.finditer(code):
        after, _ = after_parameters(code, match.end())
        if after == "{":
            missing_return(source, match.group(1) or "default", match.start(), findings)
    for match in EXPORTED_CONST.finditer(code):
        if match.group(2) == ":":
            continue
        rest = code[match.end() :]
        start = match.end() + len(rest) - len(rest.lstrip())
        if code.startswith("async", start) and not (code[start + 5 : start + 6].isalnum()):
            start += 5
        char, at = next_char(code, start)
        if code.startswith("function", at):
            after, _ = after_parameters(code, at + len("function"))
            if after == "{":
                missing_return(source, match.group(1), match.start(), findings)
            continue
        if char in "<(":
            after, at = after_parameters(code, at)
            if after == "=" and code[at + 1 : at + 2] == ">":
                missing_return(source, match.group(1), match.start(), findings)
            continue
        word = re.match(r"[A-Za-z_$][\w$]*\s*=>", code[at:])
        if word:
            missing_return(source, match.group(1), match.start(), findings)


SOURCE_CHECKS = (check_any, check_directives, check_double_assertions, check_exported_functions)


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = check_compiler_options(roots, base, findings)
    for path in walk(roots, TYPESCRIPT):
        source = load(path, display(path, base))
        for check in SOURCE_CHECKS:
            check(source, findings)
        checked += 1
    return report(findings, checked)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
