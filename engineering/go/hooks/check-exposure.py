#!/usr/bin/env python3
"""Detector for the Go exposure rule.

Decides three conditions of engineering/go/rules/exposure.md, the Go form of
the security plugin's rule that nothing sensitive leaves the layer that owns
it (#294):

    1. no format string outside a test uses %+v or %#v, which print every
       field of a struct, and %#v past the type's own String method
    2. no error is written into an HTTP or gRPC response: http.Error and the
       gRPC status constructors are not given err or err.Error()
    3. a struct with a field named for a secret has String and LogValue
       methods in its package, so fmt and log/slog print what the type allows

Condition 2's first failing fixture is the incident that opened #294: a
handler that wrote a cloud provider's access-denied error to the client as it
came. It reads Go through golex.py, beside it, and needs nothing but the
Python standard library; a call is recognised by the name the file imports
"net/http" or the gRPC status package under, and a secret by its field name.

Usage:
    python3 engineering/go/hooks/check-exposure.py [path ...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from golex import (  # noqa: E402
    Finding,
    GoFile,
    Token,
    brace_depths,
    closing,
    imports,
    load,
    run,
    signatures,
    split_top,
    strip_newlines,
    struct_fields,
    type_name_before,
)

WHOLE_VALUE_VERB = re.compile(r"%[ \-0]*([+#])[ \-0+#]*(?:\[\d+\])?\d*(?:\.\d*)?(?:\[\d+\])?v")

RESPONSE_CALLS = {"net/http": ("Error",), "google.golang.org/grpc/status": ("Error", "Errorf")}

SECRET_SUFFIXES = (
    "password", "passwd", "passphrase", "secret", "privatekey", "apikey", "accesskey", "credential",
    "credentials", "accesstoken", "refreshtoken", "sessiontoken", "bearertoken", "authtoken", "idtoken",
)

REDACTING_METHODS = ("String", "LogValue")

_methods: dict[Path, set[tuple[str, str]]] = {}


def check_verbs(source: GoFile, findings: list[Finding]) -> None:
    for token in source.tokens:
        if token.kind not in ("string", "raw"):
            continue
        for match in WHOLE_VALUE_VERB.finditer(token.text.replace("%%", "")):
            findings.append(
                Finding(
                    f"{source.rel}:{token.line}",
                    "exposure",
                    1,
                    f"%{match.group(1)}v prints every field of a struct, past what the type chooses to show; "
                    "name the fields to print, or give the type a String method and use %v",
                )
            )


def carries_error(argument: list[Token]) -> bool:
    texts = [token.text for token in argument]
    named = any(token.kind == "ident" and (token.text == "err" or token.text.endswith("Err")) for token in argument)
    called = any(texts[i : i + 3] == [".", "Error", "("] for i in range(len(texts)))
    return named or called


def check_responses(source: GoFile, findings: list[Finding]) -> None:
    bound = imports(source.tokens)
    calls = {(bound[path], name) for path, names in RESPONSE_CALLS.items() if path in bound for name in names}
    tokens = source.tokens
    for index in range(len(tokens) - 3):
        key = (tokens[index].text, tokens[index + 2].text)
        if tokens[index + 1].text != "." or key not in calls or tokens[index + 3].text != "(":
            continue
        arguments = [strip_newlines(a) for a in split_top(tokens[index + 4 : closing(tokens, index + 3)], frozenset({","}))]
        if any(carries_error(argument) for argument in arguments[1:]):
            findings.append(
                Finding(
                    f"{source.rel}:{tokens[index].line}",
                    "exposure",
                    2,
                    f"{key[0]}.{key[1]} writes err to the response; send a generic message and a correlation id, "
                    "and log the detail inside",
                )
            )


def methods_in(directory: Path) -> set[tuple[str, str]]:
    """Every (receiver type, method name) declared by the package in a directory."""
    if directory not in _methods:
        found: set[tuple[str, str]] = set()
        for path in directory.glob("*.go"):
            source = None if path.name.endswith("_test.go") else load(path, directory)
            if source is not None:
                found.update((s.receiver, s.name) for s in signatures(source.tokens) if s.receiver)
        _methods[directory] = found
    return _methods[directory]


def field_names(field: list[Token]) -> list[str]:
    """The names a field declaration declares: its leading identifiers, before the type."""
    names, cursor = [field[0].text], 1
    while cursor + 1 < len(field) and field[cursor].text == ",":
        names.append(field[cursor + 1].text)
        cursor += 2
    return names


def secret_fields(tokens: list[Token], start: int) -> list[str]:
    """The fields of the struct whose `{` is at `start` that are named for a secret."""
    names: list[str] = []
    for field in struct_fields(tokens, start):
        field = strip_newlines(field)
        if len(field) > 1 and field[0].kind == "ident" and field[1].text != ".":
            names += [name for name in field_names(field) if name.lower().endswith(SECRET_SUFFIXES)][:1]
    return names


def check_secrets(source: GoFile, findings: list[Finding]) -> None:
    tokens, depths = source.tokens, brace_depths(source.tokens)
    for index in range(1, len(tokens) - 1):
        if tokens[index].text != "struct" or tokens[index + 1].text != "{" or depths[index] != 0:
            continue
        owner = type_name_before(tokens, index)
        secrets = secret_fields(tokens, index + 1) if owner else []
        declared = methods_in(source.path.parent)
        missing = [m for m in REDACTING_METHODS if (owner, m) not in declared]
        if secrets and missing:
            findings.append(
                Finding(
                    f"{source.rel}:{tokens[index].line}",
                    "exposure",
                    3,
                    f"{owner} carries {secrets[0]} and declares no {', '.join(missing)}; "
                    "give it methods that redact, so fmt and log/slog print only what the type allows",
                )
            )


def check(source: GoFile, findings: list[Finding]) -> None:
    if source.path.name.endswith("_test.go"):
        return
    check_verbs(source, findings)
    check_responses(source, findings)
    check_secrets(source, findings)


if __name__ == "__main__":
    sys.exit(run(sys.argv, check))
