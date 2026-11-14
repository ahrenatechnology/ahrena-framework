"""Reading Go source without Go, shared by this plugin's detectors.

check-context.py, check-surface.py, check-packages.py and
check-test-placement.py each decide a rule's conditions from Go source, and
each needs the same reading of it: a lexer that knows Go's comments,
interpreted strings, raw strings and runes, so that a name inside any of them
is not code; the brackets that pair; the import declarations; the signatures;
the module a file belongs to and the version its go.mod declares. That reading
lives here once, beside them in the same plugin, the way the fundamentals
plugin's changes.py serves its change-scoped hooks.

It takes nothing but the Python standard library, because a consumer has to be
able to run exactly what CI runs, and it does not type-check: every detector
that uses it recognises a type by how the file spells it, and each rule's
boundary section says what that costs.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

SKIP_NAMES = frozenset({"vendor", "testdata", "node_modules"})

GENERATED = re.compile(r"^// Code generated .* DO NOT EDIT\.$", re.MULTILINE)

GO_DIRECTIVE = re.compile(r"^go\s+(\d+)\.(\d+)", re.MULTILINE)

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

VERSION_SUFFIX = re.compile(r"^v\d+$")

TYPE_KEYWORDS = frozenset({"func", "map", "chan", "struct", "interface"})

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
    rule: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass
class Signature:
    name: str
    line: int
    params: list[list[Token]]
    body: tuple[int, int] | None
    start: int
    header_end: int
    receiver: str | None


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


def default_name(import_path: str) -> str:
    """The package name an import path binds when no alias is written."""
    parts = import_path.split("/")
    if len(parts) > 1 and VERSION_SUFFIX.match(parts[-1]):
        return parts[-2]
    return parts[-1]


def import_specs(tokens: list[Token]) -> list[list[Token]]:
    """Each import spec, as its tokens, from every `import` declaration."""
    specs: list[list[Token]] = []
    for index, token in enumerate(tokens[:-1]):
        if token.text != "import":
            continue
        if tokens[index + 1].text == "(":
            specs.extend(split_top(tokens[index + 2 : closing(tokens, index + 1)], frozenset({"\n", ";"})))
        else:
            specs.append(tokens[index + 1 : index + 3])
    return specs


def imports(tokens: list[Token]) -> dict[str, str]:
    """Import path to the name this file uses for it; blank and dot imports left out."""
    bound: dict[str, str] = {}
    for spec in import_specs(tokens):
        spec = strip_newlines(spec)
        strings = [token for token in spec if token.kind in ("string", "raw")]
        if not strings:
            continue
        path = strings[0].text.strip('"`')
        named = spec[0] is not strings[0]
        name = spec[0].text if named else default_name(path)
        if name not in ("_", "."):
            bound[path] = name
    return bound


def is_internal(import_path: str) -> bool:
    return "internal" in import_path.split("/")


def module_root(path: Path) -> Path | None:
    for directory in path.parents:
        if (directory / "go.mod").is_file():
            return directory
    return None


def module_version(root: Path | None) -> tuple[int, int] | None:
    """The `go` directive of a module's go.mod."""
    if root is None:
        return None
    found = GO_DIRECTIVE.search((root / "go.mod").read_text(encoding="utf-8", errors="replace"))
    return (int(found.group(1)), int(found.group(2))) if found else None


def brace_depths(tokens: list[Token]) -> list[int]:
    """The `{}` nesting depth each token sits at."""
    depths: list[int] = []
    depth = 0
    for token in tokens:
        if token.text == "}":
            depth -= 1
        depths.append(depth)
        if token.text == "{":
            depth += 1
    return depths


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


def strip_newlines(tokens: list[Token]) -> list[Token]:
    return [token for token in tokens if token.kind != "newline"]


def struct_fields(tokens: list[Token], start: int) -> list[list[Token]]:
    """The field declarations of the struct whose `{` is at `start`."""
    end = closing(tokens, start)
    fields = split_top(tokens[start + 1 : end], frozenset({"\n", ";"}))
    return [field[:-1] if field[-1].kind in ("string", "raw") else field for field in fields]


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


def receiver_type(group: list[Token]) -> str:
    """The type name in a method receiver, past any pointer and type parameters."""
    names = [token.text for token in group[: next((i for i, t in enumerate(group) if t.text == "["), len(group))] if token.kind == "ident"]
    return names[-1] if names else ""


def signature_at(tokens: list[Token], index: int) -> Signature | None:
    """The signature that the `func` keyword at `index` opens."""
    name, cursor, receiver = "func literal", index + 1, None
    if cursor < len(tokens) and tokens[cursor].text == "(":
        after = closing(tokens, cursor) + 1
        if after + 1 < len(tokens) and tokens[after].kind == "ident" and tokens[after + 1].text in ("(", "["):
            receiver, cursor = receiver_type(tokens[cursor + 1 : after - 1]), after
    if cursor < len(tokens) and tokens[cursor].kind == "ident":
        name, cursor = tokens[cursor].text, after_type_parameters(tokens, cursor + 1)
    if cursor >= len(tokens) or tokens[cursor].text != "(":
        return None
    end = closing(tokens, cursor)
    as_type = index > 0 and tokens[index - 1].text == "]"
    body = None if as_type else find_body(tokens, end + 1)
    header_end = body[0] if body else min(end + 1, len(tokens))
    return Signature(name, tokens[index].line, parameter_types(tokens[cursor + 1 : end]), body, index, header_end, receiver)


def signatures(tokens: list[Token]) -> list[Signature]:
    found = (signature_at(tokens, index) for index, token in enumerate(tokens) if token.text == "func")
    return [signature for signature in found if signature is not None]


def is_exported(name: str) -> bool:
    return bool(name) and name[0].isupper()


def display(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


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


@dataclass
class GoFile:
    path: Path
    rel: str
    tokens: list[Token]
    root: Path | None
    package: str


def load(path: Path, base: Path) -> GoFile | None:
    """A Go file ready to check, or None when it is generated."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if GENERATED.search(text):
        return None
    tokens = lex(text)
    package = next((tokens[i + 1].text for i, t in enumerate(tokens[:-1]) if t.text == "package"), "")
    return GoFile(path, display(path, base), tokens, module_root(path), package)


def run(argv: list[str], check: Callable[[GoFile, list[Finding]], None]) -> int:
    """Walk the paths given, check every Go file that is not generated, and report."""
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    for path in sources(roots):
        source = load(path, base)
        if source is None:
            continue
        check(source, findings)
        checked += 1
    return report(findings, checked)
