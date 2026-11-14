#!/usr/bin/env python3
"""Detector for the context conditions in the Go engineering rule.

Decides the three conditions stated in engineering/go/rules/context.md:

    1. no struct field holds a context.Context
    2. a parameter of type context.Context is the first parameter
    3. a function with a context.Context parameter does not call
       context.Background or context.TODO inside its body

All three are taken from the documentation of the context package, which says
not to store a Context inside a struct type and to pass it as the first
parameter, and from Go 1.21's context.WithoutCancel, which is the reason
condition 3 has no legitimate exception left on a module that can call it.

The hook takes nothing but the Python standard library, because a consumer has
to be able to run exactly what CI runs. It does not need Go installed: it reads
Go source through a lexer that knows Go's comments, interpreted strings, raw
strings and runes, so a context named inside any of them is not code. It does
not type-check. A parameter is a context when it is spelled through the name
the file imports "context" under; that is what makes the three conditions
decidable from one file, and the rule's boundary section says what it costs.

Usage:
    python3 engineering/go/hooks/check-context.py [path ...]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RULE = "context"

SKIP_NAMES = frozenset({"vendor", "testdata", "node_modules"})

GENERATED = re.compile(r"^// Code generated .* DO NOT EDIT\.$", re.MULTILINE)

GO_DIRECTIVE = re.compile(r"^go\s+(\d+)\.(\d+)", re.MULTILINE)

WITHOUT_CANCEL = (1, 21)

LEXEME = re.compile(
    r"""
    (?P<space>[ \t\r\f]+)
    | (?P<newline>\n)
    | (?P<line_comment>//[^\n]*)
    | (?P<block_comment>/\*.*?\*/)
    | (?P<raw>`[^`]*`)
    | (?P<string>"(?:\\.|[^"\\\n])*")
    | (?P<rune>'(?:\\.|[^'\\\n])+')
    | (?P<ident>[^\W\d]\w*)
    | (?P<number>\.?\d[\w.]*)
    | (?P<op>\.\.\.|[^\s\w])
    """,
    re.VERBOSE | re.DOTALL,
)

TYPE_KEYWORDS = frozenset({"func", "map", "chan", "struct", "interface"})

TESTING_HANDLES = (("*", "testing", ".", "T"), ("*", "testing", ".", "B"), ("*", "testing", ".", "F"), ("testing", ".", "TB"))

OPENERS = {"(": ")", "[": "]", "{": "}"}

SIGNATURE_ENDS = frozenset({"\n", ",", ")", "]", ";", "}", "=", ":"})


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int


@dataclass
class Finding:
    where: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    rel: str
    tokens: list[Token]
    alias: str
    detach_available: bool


@dataclass
class Signature:
    name: str
    line: int
    params: list[list[Token]]
    body: tuple[int, int] | None


def lex(text: str) -> list[Token]:
    """Go source as tokens; comments dropped, a newline kept as a token."""
    tokens: list[Token] = []
    line = 1
    for match in LEXEME.finditer(text):
        kind, value = match.lastgroup or "op", match.group()
        if kind == "newline" or (kind == "block_comment" and "\n" in value):
            tokens.append(Token("newline", "\n", line))
        elif kind not in ("space", "line_comment", "block_comment"):
            tokens.append(Token(kind, value, line))
        line += value.count("\n")
    return tokens


def context_alias(tokens: list[Token]) -> str:
    """The name this file imports "context" under, or nothing."""
    for index, token in enumerate(tokens):
        if token.kind != "string" or token.text != '"context"':
            continue
        before = tokens[index - 1] if index else None
        if before is not None and before.kind == "ident" and before.text != "import":
            return before.text if before.text not in ("_", ".") else ""
        return "context"
    return ""


def module_version(path: Path) -> tuple[int, int] | None:
    """The `go` directive of the nearest go.mod above a file."""
    for directory in path.parents:
        go_mod = directory / "go.mod"
        if go_mod.is_file():
            found = GO_DIRECTIVE.search(go_mod.read_text(encoding="utf-8", errors="replace"))
            return (int(found.group(1)), int(found.group(2))) if found else None
    return None


def closing(tokens: list[Token], start: int) -> int:
    """The index of the bracket that closes the one at `start`."""
    want, depth = OPENERS[tokens[start].text], 0
    for index in range(start, len(tokens)):
        text = tokens[index].text
        if text == tokens[start].text:
            depth += 1
        elif text == want:
            depth -= 1
            if depth == 0:
                return index
    return len(tokens) - 1


def texts(tokens: list[Token]) -> tuple[str, ...]:
    return tuple(token.text for token in tokens)


def split_top(tokens: list[Token], separators: frozenset[str]) -> list[list[Token]]:
    """Split a bracketed run at its top level, dropping empty pieces."""
    pieces: list[list[Token]] = [[]]
    depth = 0
    for token in tokens:
        if token.text in OPENERS:
            depth += 1
        elif token.text in OPENERS.values():
            depth -= 1
        if depth == 0 and token.text in separators:
            pieces.append([])
        else:
            pieces[-1].append(token)
    return [piece for piece in pieces if any(token.kind != "newline" for token in piece)]


def is_context(type_tokens: list[Token], alias: str) -> bool:
    return texts(type_tokens) == (alias, ".", "Context")


def strip_newlines(tokens: list[Token]) -> list[Token]:
    return [token for token in tokens if token.kind != "newline"]


def struct_fields(tokens: list[Token], start: int) -> list[list[Token]]:
    """The field declarations of the struct whose `{` is at `start`."""
    end = closing(tokens, start)
    fields = split_top(tokens[start + 1 : end], frozenset({"\n", ";"}))
    return [field[:-1] if field[-1].kind in ("string", "raw") else field for field in fields]


def field_names(prefix: list[Token]) -> str | None:
    """The names a field declares, or None when the prefix is not a name list."""
    names = [token.text for token in prefix if token.text != ","]
    if all(token.kind == "ident" or token.text == "," for token in prefix):
        return ", ".join(names)
    return None


def check_fields(source: Source, findings: list[Finding]) -> None:
    tokens = source.tokens
    for index, token in enumerate(tokens[:-1]):
        if token.text != "struct" or tokens[index + 1].text != "{":
            continue
        owner = tokens[index - 1].text if index and tokens[index - 1].kind == "ident" else "an anonymous struct"
        for field in struct_fields(tokens, index + 1):
            field = strip_newlines(field)
            if len(field) < 3 or not is_context(field[-3:], source.alias):
                continue
            names = field_names(field[:-3])
            where = f"{source.rel}:{field[0].line}"
            if names == "":
                findings.append(Finding(where, 1, f"{owner} embeds context.Context; pass it to each method as its first parameter instead"))
            elif names is not None:
                findings.append(Finding(where, 1, f"{owner} stores a context.Context in field {names}; pass it to each method as its first parameter instead"))


def is_named_entry(entry: list[Token]) -> bool:
    return len(entry) >= 2 and entry[0].kind == "ident" and entry[0].text not in TYPE_KEYWORDS and entry[1].text != "."


def parameter_types(group: list[Token]) -> list[list[Token]]:
    """The type of each parameter in a parenthesised list, grouping resolved."""
    entries = [strip_newlines(entry) for entry in split_top(group, frozenset({","}))]
    if not any(is_named_entry(entry) for entry in entries):
        return entries
    types: list[list[Token]] = []
    pending = 0
    for entry in entries:
        if len(entry) == 1:
            pending += 1
            continue
        types.extend([entry[1:]] * (pending + 1))
        pending = 0
    return types


def skip_type_braces(tokens: list[Token], index: int) -> int:
    """Past a `struct{...}` or `interface{...}` that sits in a result type."""
    if tokens[index].text in ("struct", "interface") and index + 1 < len(tokens) and tokens[index + 1].text == "{":
        return closing(tokens, index + 1) + 1
    return index + 1


def find_body(tokens: list[Token], index: int) -> tuple[int, int] | None:
    """The body that follows a signature's results, or None for a func type."""
    depth = 0
    while index < len(tokens):
        text = tokens[index].text
        if depth == 0 and text == "{":
            return index, closing(tokens, index)
        if depth == 0 and text in SIGNATURE_ENDS:
            return None
        depth += 1 if text in ("(", "[") else -1 if text in (")", "]") else 0
        index = skip_type_braces(tokens, index)
    return None


def after_type_parameters(tokens: list[Token], index: int) -> int:
    if index < len(tokens) and tokens[index].text == "[":
        return closing(tokens, index) + 1
    return index


def signature_at(tokens: list[Token], index: int) -> Signature | None:
    """The signature that the `func` keyword at `index` opens."""
    name, cursor = "func literal", index + 1
    if cursor < len(tokens) and tokens[cursor].text == "(":
        after = closing(tokens, cursor) + 1
        if after + 1 < len(tokens) and tokens[after].kind == "ident" and tokens[after + 1].text in ("(", "["):
            cursor = after
    if cursor < len(tokens) and tokens[cursor].kind == "ident":
        name, cursor = tokens[cursor].text, after_type_parameters(tokens, cursor + 1)
    if cursor >= len(tokens) or tokens[cursor].text != "(":
        return None
    end = closing(tokens, cursor)
    as_type = index > 0 and tokens[index - 1].text == "]"
    body = None if as_type else find_body(tokens, end + 1)
    return Signature(name, tokens[index].line, parameter_types(tokens[cursor + 1 : end]), body)


def signatures(tokens: list[Token]) -> list[Signature]:
    found = (signature_at(tokens, index) for index, token in enumerate(tokens) if token.text == "func")
    return [signature for signature in found if signature is not None]


def context_positions(signature: Signature, alias: str) -> list[int]:
    return [index for index, kind in enumerate(signature.params) if is_context(kind, alias)]


def check_position(source: Source, signature: Signature, findings: list[Finding]) -> None:
    positions = context_positions(signature, source.alias)
    if not positions or positions[0] == 0:
        return
    before = signature.params[: positions[0]]
    if all(texts(kind) in TESTING_HANDLES for kind in before):
        return
    findings.append(
        Finding(
            f"{source.rel}:{signature.line}",
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


def check_fresh(source: Source, signature: Signature, reported: set[int], findings: list[Finding]) -> None:
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
                3,
                f"{signature.name} has a context.Context in scope and calls context.{call}; "
                "pass the context down, or detach with context.WithoutCancel",
            )
        )


def check_source(source: Source, findings: list[Finding]) -> None:
    check_fields(source, findings)
    reported: set[int] = set()
    for signature in signatures(source.tokens):
        check_position(source, signature, findings)
        if source.detach_available:
            check_fresh(source, signature, reported, findings)


def display(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def load(path: Path, base: Path) -> Source | None:
    """A Go file ready to check, or None when it is generated."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if GENERATED.search(text):
        return None
    tokens = lex(text)
    version = module_version(path)
    detach = version is None or version >= WITHOUT_CANCEL
    return Source(display(path, base), tokens, context_alias(tokens), detach)


def skipped(relative: Path) -> bool:
    """The go tool ignores dot and underscore directories, testdata and vendor."""
    return any(part.startswith((".", "_")) or part in SKIP_NAMES for part in relative.parts[:-1])


def sources(roots: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        if root.is_file():
            found.add(root)
            continue
        found.update(path for path in root.rglob("*.go") if not skipped(path.relative_to(root)))
    return sorted(found)


def report(findings: list[Finding], checked: int) -> int:
    if not findings:
        print(f"{checked} file(s), no failures.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s):\n")
    for finding in sorted(findings, key=lambda item: (item.where, item.condition)):
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    for path in sources(roots):
        source = load(path, base)
        if source is None:
            continue
        if source.alias:
            check_source(source, findings)
        checked += 1
    return report(findings, checked)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
