#!/usr/bin/env python3
"""Detector for condition 2 of the Go exported-surface rule.

Decides condition 2 of engineering/go/rules/api-surface.md: no identifier
exported from a package outside an internal/ tree carries, in its signature,
fields or embedded types, a type declared in an internal/ package.

The condition comes from the go command's own rule that code under internal/
is importable only from beneath its parent, so a type from there on a public
signature is a type the importer cannot name. No linter in golangci-lint's
catalogue reports it, which is why the plugin ships this one.

It reads Go through golex.py, beside it, and needs nothing but the Python
standard library. A type is internal when it is spelled through the name the
file imports an internal/ path under; the rule's boundary section says what
that costs.

Usage:
    python3 engineering/go/hooks/check-surface.py [path ...]
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
    brace_depths,
    imports,
    is_exported,
    is_internal,
    run,
    signatures,
    strip_newlines,
    struct_fields,
    type_name_before,
)

@dataclass
class Surface:
    rel: str
    tokens: list[Token]
    internal: dict[str, str]
    depths: list[int]


def internal_types(tokens: list[Token], internal: dict[str, str]) -> list[tuple[str, str]]:
    """Each `name.Type` in a run of tokens whose package is internal, with its path."""
    by_name = {name: path for path, name in internal.items()}
    return [
        (f"{tokens[i].text}.{tokens[i + 2].text}", by_name[tokens[i].text])
        for i in range(len(tokens) - 2)
        if tokens[i].text in by_name and tokens[i + 1].text == "." and tokens[i + 2].kind == "ident"
    ]


def leak(source: Surface, line: int, subject: str, found: tuple[str, str]) -> Finding:
    kind, path = found
    return Finding(
        f"{source.rel}:{line}",
        "api-surface",
        2,
        f"{subject} {kind}, from internal package {path}, which an importer outside it cannot name",
    )


def check_signature_surface(source: Surface, signature: Signature, findings: list[Finding]) -> None:
    if source.depths[signature.start] != 0 or not is_exported(signature.name):
        return
    if signature.receiver is not None and not is_exported(signature.receiver):
        return
    header = source.tokens[signature.start : signature.header_end]
    for found in internal_types(header, source.internal):
        findings.append(leak(source, signature.line, f"{signature.name} exposes", found))


def member_surface(member: list[Token]) -> tuple[str, list[Token]] | None:
    """A field or method's exported name and the tokens of its type, or None."""
    if len(member) > 1 and member[0].kind == "ident" and member[1].text not in (".", "\n"):
        names = [token.text for token in member if token.kind == "ident"][:1] + [
            member[i + 1].text for i, token in enumerate(member[:-1]) if token.text == ","
        ]
        exported = [name for name in names if is_exported(name)]
        return (exported[0], member[1:]) if exported else None
    return ("", member)


def check_type_surface(source: Surface, index: int, findings: list[Finding]) -> None:
    tokens = source.tokens
    owner = type_name_before(tokens, index)
    if source.depths[index] != 0 or not is_exported(owner):
        return
    word = "field" if tokens[index].text == "struct" else "method"
    for member in struct_fields(tokens, index + 1):
        member = strip_newlines(member)
        surface = member_surface(member) if member else None
        if surface is None:
            continue
        name, kind_tokens = surface
        subject = f"{owner} embeds" if not name else f"{owner} exposes"
        for kind, path in internal_types(kind_tokens, source.internal):
            where = f"{kind}" if not name else f"{kind} in {word} {name}"
            findings.append(leak(source, member[0].line, subject, (where, path)))


def on_surface(path: Path, root: Path | None, tokens: list[Token]) -> bool:
    """Whether the file's exported identifiers reach importers outside internal/."""
    if path.name.endswith("_test.go"):
        return False
    package = next((tokens[i + 1].text for i, t in enumerate(tokens[:-1]) if t.text == "package"), "")
    inside = path.parent.relative_to(root).parts if root is not None else path.parent.parts
    return package != "main" and "internal" not in inside


def check(source: GoFile, findings: list[Finding]) -> None:
    if not on_surface(source.path, source.root, source.tokens):
        return
    internal = {path: name for path, name in imports(source.tokens).items() if is_internal(path)}
    if not internal:
        return
    surface = Surface(source.rel, source.tokens, internal, brace_depths(source.tokens))
    for signature in signatures(source.tokens):
        check_signature_surface(surface, signature, findings)
    for index, token in enumerate(source.tokens[:-1]):
        if token.text in ("struct", "interface") and source.tokens[index + 1].text == "{":
            check_type_surface(surface, index, findings)


if __name__ == "__main__":
    sys.exit(run(sys.argv, check))
