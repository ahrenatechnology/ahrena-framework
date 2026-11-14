#!/usr/bin/env python3
"""Detector for the context conditions in the Go engineering rule.

Decides the three conditions stated in engineering/go/rules/context.md:

    1. no struct field holds a context.Context
    2. a parameter of type context.Context is the first parameter
    3. a function with a context.Context parameter does not call
       context.Background or context.TODO inside its body

All three are taken from the documentation of the context package, which says
not to store a Context inside a struct type and to pass it as the first
parameter, and from Go 1.21's context.WithoutCancel (accepted proposal
golang/go#40221), which is the reason condition 3 has no legitimate exception
left on a module that can call it.

It reads Go through golex.py, beside it, and needs nothing but the Python
standard library. A parameter is a context when it is spelled through the name
the file imports "context" under; the rule's boundary section says what that
costs.

Usage:
    python3 engineering/go/hooks/check-context.py [path ...]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from golex import (  # noqa: E402
    Finding,
    GoFile,
    Signature,
    Token,
    imports,
    module_version,
    run,
    signatures,
    split_top,
    strip_newlines,
    struct_fields,
    texts,
    type_name_before,
)

@dataclass
class Context:
    rel: str
    tokens: list[Token]
    alias: str


WITHOUT_CANCEL = (1, 21)

TESTING_HANDLES = (("*", "testing", ".", "T"), ("*", "testing", ".", "B"), ("*", "testing", ".", "F"), ("testing", ".", "TB"))


def is_context(type_tokens: list[Token], alias: str) -> bool:
    return texts(type_tokens) == (alias, ".", "Context")


def field_names(prefix: list[Token]) -> str | None:
    """The names a field declares, or None when the prefix is not a name list."""
    names = [token.text for token in prefix if token.text != ","]
    if all(token.kind == "ident" or token.text == "," for token in prefix):
        return ", ".join(names)
    return None


def check_fields(source: Context, findings: list[Finding]) -> None:
    tokens = source.tokens
    for index, token in enumerate(tokens[:-1]):
        if token.text != "struct" or tokens[index + 1].text != "{":
            continue
        owner = type_name_before(tokens, index) or "an anonymous struct"
        for field in struct_fields(tokens, index + 1):
            field = strip_newlines(field)
            if len(field) < 3 or not is_context(field[-3:], source.alias):
                continue
            names = field_names(field[:-3])
            where = f"{source.rel}:{field[0].line}"
            if names:
                findings.append(Finding(where, "context", 1, f"{owner} stores a context.Context in field {names}; pass it to each method as its first parameter instead"))


def context_positions(signature: Signature, alias: str) -> list[int]:
    return [index for index, kind in enumerate(signature.params) if is_context(kind, alias)]


def check_position(source: Context, signature: Signature, findings: list[Finding]) -> None:
    positions = context_positions(signature, source.alias)
    if not positions or positions[0] == 0:
        return
    before = signature.params[: positions[0]]
    if all(texts(kind) in TESTING_HANDLES for kind in before):
        return
    findings.append(
        Finding(
            f"{source.rel}:{signature.line}",
            "context",
            2,
            f"{signature.name} takes its context.Context as parameter {positions[0] + 1}; it goes first",
        )
    )


def fresh_contexts(tokens: list[Token], body: tuple[int, int], alias: str) -> list[int]:
    """Indices of `alias.Background(` and `alias.TODO(` inside a body."""
    start, end = body
    return [
        index
        for index in range(start, end - 3)
        if tokens[index].text == alias
        and tokens[index + 1].text == "."
        and tokens[index + 2].text in ("Background", "TODO")
        and tokens[index + 3].text == "("
    ]


def check_fresh(source: Context, signature: Signature, reported: set[int], findings: list[Finding]) -> None:
    if signature.body is None or not context_positions(signature, source.alias):
        return
    for index in fresh_contexts(source.tokens, signature.body, source.alias):
        if index in reported:
            continue
        reported.add(index)
        call = source.tokens[index + 2].text
        findings.append(
            Finding(
                f"{source.rel}:{source.tokens[index].line}",
                "context",
                3,
                f"{signature.name} has a context.Context in scope and calls context.{call}; "
                "pass the context down, or detach with context.WithoutCancel",
            )
        )


def check(source: GoFile, findings: list[Finding]) -> None:
    alias = imports(source.tokens).get("context", "")
    if not alias:
        return
    version = module_version(source.root)
    context = Context(source.rel, source.tokens, alias)
    check_fields(context, findings)
    reported: set[int] = set()
    for signature in signatures(source.tokens):
        check_position(context, signature, findings)
        if version is None or version >= WITHOUT_CANCEL:
            check_fresh(context, signature, reported, findings)


if __name__ == "__main__":
    sys.exit(run(sys.argv, check))
