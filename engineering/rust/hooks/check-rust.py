#!/usr/bin/env python3
"""Detector for the Rust conditions that the source decides and Clippy does not.

Decides six conditions in five rules:

    engineering/rust/rules/error-types.md
      1. a public function or type alias of a library crate exposes an opaque
         error: anyhow's or eyre's, a boxed `dyn Error`, or a string

    engineering/rust/rules/async-blocking.md
      1. a call inside an async body that blocks the thread it runs on: a
         `std::thread::sleep`, a `std::fs` function, a synchronous connect, a
         `blocking_` method, or reqwest's blocking client

    engineering/rust/rules/dependency-direction.md
      1. two modules of one crate that reach each other, directly or round a
         longer cycle
      2. a workspace crate that depends on a crate of a higher layer, by the
         layers the workspace declares in its Cargo metadata

    engineering/rust/rules/unit-tests.md
      1. a source file that defines a function and has no test beside it

    engineering/rust/rules/redaction.md
      1. a type that derives `Debug` or `Serialize` over a field whose name
         says it holds a secret, in a type that does not redact it

Every other condition of those five rules, and every condition of the other
eight Rust rules, is decided by Clippy, by rustc, by a cargo tool the
consuming project runs, or by a reviewer, and each rule says which. This
script exists for the ones that none of those decides. Clippy has no lint for
an opaque error on a library's surface, and its `disallowed_methods` bans a
function everywhere, not only inside an async body, so a project that bans
`std::fs::read` that way bans it in the synchronous code where it is right.

Rust has no parser in the Python standard library and this hook takes no
dependency, so it reads a masked copy of the source: comments, strings and
character literals are blanked to spaces, keeping every offset and line, and
what remains is matched by brace and parenthesis. That is enough for the two
conditions here, which are about a signature and a call path, and it is not
enough for anything that needs a type. A path is resolved through the file's
own `use` declarations, so `fs::read` is std's only where `fs` was imported
from std.

Usage:
    python3 engineering/rust/hooks/check-rust.py [path ...]
"""

from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ERROR_RULE = "error-types"
ASYNC_RULE = "async-blocking"
DIRECTION_RULE = "dependency-direction"
TESTS_RULE = "unit-tests"
REDACTION_RULE = "redaction"

# #287: dot-prefixed directories are skipped by shape; tests and benches hold test code.
SKIP_NAMES = frozenset({"target", "vendor", "node_modules", "tests", "benches"})


RAW_STRING = re.compile(r'(?<![\w])(?:b|c)?r(#*)"')
STRING = re.compile(r'(?<![\w])(?:b|c)?"')
CHAR = re.compile(r"(?<![\w])b?'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.)|[^\\'\n])'")


CFG_TEST = re.compile(r"#\[\s*cfg\s*\(\s*test\s*\)\s*\]")
ITEM_HEAD = re.compile(
    r"\s*(?:#\[[^\]]*\]\s*)*(?:pub(?:\s*\([^)]*\))?\s+)?(?:(?:async|unsafe|const|extern)\s+)*"
    r"(?:mod|fn|impl|struct|enum|union|use|const|static|trait|type|macro_rules!)(?![\w])"
)


PUBLIC_FN = re.compile(
    r"(?<![\w(])pub\s+(?:(?:const|async|unsafe|safe)\s+|extern\s+)*fn\s+([A-Za-z_]\w*)"
)
PUBLIC_TYPE = re.compile(r"(?<![\w(])pub\s+type\s+([A-Za-z_]\w*)")
OPAQUE_PATH = re.compile(r"\b((?:anyhow|eyre|color_eyre)::(?:Result|Error|Report))\b")
BOXED_ERROR = re.compile(r"Box\s*<\s*dyn\s+(?:\w+::)*(?:Error|StdError)\b")
TYPE_ALIAS = re.compile(r"(?<![\w])type\s+([A-Za-z_]\w*)(?:\s*<[^=;]*>)?\s*=\s*([^;]+);")
DOC_HIDDEN = re.compile(r"#\[\s*doc\s*\(\s*hidden\s*\)\s*\]")
STRING_ERRORS = frozenset({"String", "&str", "&'static str", "std::string::String"})


ASYNC_BLOCK = re.compile(r"\basync\s+(?:move\s+)?\{")
ASYNC_FN = re.compile(r"\basync\s+(?:unsafe\s+)?(?:extern\s+)?fn\s+[A-Za-z_]\w*")
ASYNC_CLOSURE = re.compile(r"\basync\s+(?:move\s+)?\|")
OFFLOAD = re.compile(r"\b(?:spawn_blocking|block_in_place|thread\s*::\s*spawn|thread\s*::\s*scope)\s*\(")
USE = re.compile(r"\buse\s+([^;]+);")
CALL = re.compile(r"(?<![\w.:])((?:::)?(?:[A-Za-z_]\w*\s*::\s*)*[A-Za-z_]\w*)\s*\(")
BLOCKING_METHOD = re.compile(r"\.\s*(blocking_[a-z_]+)\s*\(")

# #287: the closed list of blocking calls; rules/async-blocking.md argues it.
STD_FS_FUNCTIONS = (
    "read read_to_string read_dir write copy rename remove_file remove_dir remove_dir_all "
    "create_dir create_dir_all metadata symlink_metadata canonicalize hard_link read_link "
    "set_permissions exists"
).split()
BLOCKING_PATHS = frozenset(
    {"std::thread::sleep", "std::net::TcpStream::connect", "std::net::TcpStream::connect_timeout"}
    | {f"std::fs::{name}" for name in STD_FS_FUNCTIONS}
    | {"std::fs::File::open", "std::fs::File::create", "std::fs::File::create_new"}
)
BLOCKING_PREFIXES = ("reqwest::blocking::",)

MODULE_PATH = re.compile(r"\b(?:crate|super|self)(?:\s*::\s*[A-Za-z_]\w*)+")
FUNCTION = re.compile(r"\bfn\s+([A-Za-z_]\w*)")
TEST_ATTRIBUTE = re.compile(r"#\[\s*(?:\w+\s*::\s*)*test\b")
EXTERNAL_TESTS = re.compile(r"#\[\s*cfg\s*\(\s*test\s*\)\s*\]\s*mod\s+tests\s*;")
DERIVE = re.compile(r"#\[\s*derive\s*\(([^)]*)\)\s*\]")
TYPE_ITEM = re.compile(r"\b(struct|enum)\s+([A-Za-z_]\w*)")
REVEALING_DERIVES = ("Debug", "Serialize")
RAW_TEXT = re.compile(
    r"(?:Option\s*<\s*)?(?:(?:std::string::)?String(?!\w)|Box\s*<\s*str\s*>|Vec\s*<\s*u8\s*>"
    r"|Cow\s*<[^>]*\bstr\s*>|&\s*(?:'\w+\s+)?(?:mut\s+)?(?:str(?!\w)|\[\s*u8\s*\]))"
)

# #287: field names that say a value is a secret, matched whole or as a suffix.
SECRET_NAMES = frozenset(
    "password passwd passphrase secret token api_key apikey private_key secret_key access_key credential credentials".split()
)




@dataclass(frozen=True)
class Finding:
    """One failure: the path with its line, the rule, and what was found."""

    where: str
    rule: str
    message: str
    condition: int = 1

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    """One file, read once.

    `rel` is the path to report, relative to the working directory. `code` is
    the text with comments, literals and test items blanked. `library` says
    whether the file is a library crate's own source. `imports` maps each name
    a `use` binds to the full path it binds, and `boxed_aliases` maps each type
    alias the file declares for a boxed error to what it names. `module` is
    the file's module path inside its crate, `crate` the crate's directory,
    and `tested` whether the file carries a test attribute.
    """

    rel: str
    code: str
    library: bool
    imports: dict[str, str] = field(default_factory=dict)
    boxed_aliases: dict[str, str] = field(default_factory=dict)
    module: tuple[str, ...] | None = None
    crate: Path | None = None
    tested: bool = False

    def where(self, offset: int) -> str:
        return f"{self.rel}:{self.code.count(chr(10), 0, offset) + 1}"




def blank(text: str, start: int, end: int) -> str:
    return "".join(char if char == "\n" else " " for char in text[start:end])


def block_comment_end(text: str, start: int) -> int:
    """Rust block comments nest, so the end is found by depth."""
    depth = 0
    index = start
    while index < len(text):
        pair = text[index : index + 2]
        if pair in ("/*", "*/"):
            depth += 1 if pair == "/*" else -1
            index += 2
            if depth == 0:
                return index
            continue
        index += 1
    return len(text)


def string_end(text: str, start: int) -> int:
    index = start
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            return index + 1
        index += 1
    return len(text)


def literal_end(text: str, index: int) -> int | None:
    """Where the comment or literal starting at `index` ends, or None."""
    if text.startswith("//", index):
        newline = text.find("\n", index)
        return len(text) if newline < 0 else newline
    if text.startswith("/*", index):
        return block_comment_end(text, index)
    raw = RAW_STRING.match(text, index)
    if raw:
        closing = '"' + raw.group(1)
        found = text.find(closing, raw.end())
        return len(text) if found < 0 else found + len(closing)
    plain = STRING.match(text, index)
    if plain:
        return string_end(text, plain.end())
    char = CHAR.match(text, index)
    return char.end() if char else None


def mask(text: str) -> str:
    """The text with comments and literals blanked, offsets and lines kept.

    A lifetime (`'a`) is not a character literal and survives, because a
    signature that says `&'static str` has to be read as one.
    """
    out: list[str] = []
    index = 0
    while index < len(text):
        end = literal_end(text, index)
        if end is None:
            out.append(text[index])
            index += 1
        else:
            out.append(blank(text, index, end))
            index = end
    return "".join(out)


def closing(text: str, open_index: int) -> int:
    """The index just past the bracket that closes the one at `open_index`."""
    opener = text[open_index]
    closer = {"{": "}", "(": ")", "[": "]"}[opener]
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index + 1
    return len(text)


def item_end(code: str, index: int) -> int:
    """The end of the item that starts at `index`: its braces or its `;`."""
    body = body_after(code, index)
    if body:
        return body[1]
    semicolon = code.find(";", index)
    return len(code) if semicolon < 0 else semicolon + 1


def without_tests(code: str) -> str:
    """The code with every item under `#[cfg(test)]` blanked.

    The item is whatever the attribute decorates, up to its `;` or through its
    braces, so a test module, a test-only function and a test-only import all
    go the same way. An attribute on a field or a statement decorates no item
    and is left alone, and the search restarts on the blanked text so an
    attribute inside an item already blanked is never acted on.
    """
    index = 0
    while attribute := CFG_TEST.search(code, index):
        index = attribute.end()
        if ITEM_HEAD.match(code, attribute.end()):
            end = item_end(code, attribute.end())
            code = code[: attribute.start()] + blank(code, attribute.start(), end) + code[end:]
    return code


def split_top_level(text: str, separator: str = ",") -> list[str]:
    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        depth += char in "{<(["
        depth -= char in "}>)]"
        if char == separator and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def segments(path: str) -> list[str]:
    return [segment for segment in re.split(r"\s*::\s*", path.strip()) if segment]


def leaf(tree: str, prefix: list[str]) -> list[tuple[str, str]]:
    parts = re.split(r"\s+as\s+", tree)
    path = prefix + segments(parts[0])
    if path and path[-1] == "self":
        path = path[:-1]
    if not path or path[-1] == "*":
        return []
    alias = parts[1].strip() if len(parts) == 2 else path[-1]
    return [] if alias == "_" else [(alias, "::".join(path))]


def expand_use(tree: str, prefix: list[str]) -> list[tuple[str, str]]:
    """Every name a `use` tree binds, with the path it binds it to."""
    tree = tree.strip().removeprefix("::")
    brace = tree.find("{")
    if brace < 0:
        return leaf(tree, prefix)
    head = prefix + segments(tree[:brace])
    inner = tree[brace + 1 : closing(tree, brace) - 1]
    bound: list[tuple[str, str]] = []
    for item in split_top_level(inner):
        bound.extend(expand_use(item, head))
    return bound


def imports_of(code: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for declaration in USE.finditer(code):
        found.update(expand_use(declaration.group(1), []))
    return found


def resolve(path: str, imports: dict[str, str]) -> str:
    parts = segments(path.removeprefix("::"))
    head = imports.get(parts[0])
    return "::".join([head, *parts[1:]]) if head else "::".join(parts)




def skip_generics(code: str, index: int) -> int:
    """Past a `<...>` list starting at `index`, which may hold `Fn() -> T`."""
    depth = 0
    while index < len(code):
        if code.startswith("->", index):
            index += 2
            continue
        depth += code[index] == "<"
        depth -= code[index] == ">"
        index += 1
        if depth == 0:
            return index
    return index


def return_type(code: str, after_name: int) -> str:
    """The text between `->` and the body, the `;` or the `where` clause."""
    index = after_name
    while code[index].isspace():
        index += 1
    if code[index] == "<":
        index = skip_generics(code, index)
    params = code.find("(", index)
    if params < 0:
        return ""
    rest = code[closing(code, params) :]
    arrow = re.match(r"\s*->", rest)
    if not arrow:
        return ""
    end = re.search(r"[{;]|\bwhere\b", rest[arrow.end() :])
    return rest[arrow.end() : arrow.end() + end.start()] if end else ""


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def outermost(spaced: str) -> tuple[str, list[str]]:
    """The outermost path of a type, and its generic arguments."""
    found = re.match(r"((?:[A-Za-z_]\w*\s*::\s*)*[A-Za-z_]\w*)\s*(<?)", spaced)
    if not found:
        return "", []
    path = re.sub(r"\s+", "", found.group(1))
    if not found.group(2):
        return path, []
    end = skip_generics(spaced, found.end() - 1)
    return path, split_top_level(spaced[found.end() : end - 1])


def opaque_error(error: str, source: Source) -> str | None:
    """What makes this error type opaque to a caller, or None."""
    if error in STRING_ERRORS:
        return f"{error} as its error"
    if BOXED_ERROR.match(error):
        return error
    path, _ = outermost(error)
    if path in source.boxed_aliases:
        return f"{path}, an alias of {source.boxed_aliases[path]}"
    full = resolve(path, source.imports) if path else ""
    return full if OPAQUE_PATH.fullmatch(full) else None


def error_channel(text: str, source: Source) -> str | None:
    """What makes the error channel of this type opaque, or None.

    Only the outermost type is read: a `Result` whose error is opaque, or
    anyhow's and eyre's own `Result`. A boxed error inside a callback type, or
    returned as the value, is not the error this function fails with.
    """
    path, arguments = outermost(collapse(text))
    if not path:
        return None
    full = resolve(path, source.imports)
    if OPAQUE_PATH.fullmatch(full) and full.endswith("Result"):
        return full
    if full.split("::")[-1] == "Result" and len(arguments) == 2:
        return opaque_error(arguments[1], source)
    return None


def hidden(code: str, start: int) -> bool:
    """Whether the item at `start` carries `#[doc(hidden)]`."""
    previous = max(code.rfind(mark, 0, start) for mark in ";{}")
    return bool(DOC_HIDDEN.search(code, previous + 1, start))


def boxed_aliases(code: str) -> dict[str, str]:
    """Every type alias in the file that names a boxed error, by its name."""
    return {
        alias.group(1): collapse(alias.group(2))
        for alias in TYPE_ALIAS.finditer(code)
        if BOXED_ERROR.match(collapse(alias.group(2)))
    }


def check_error_types(source: Source, findings: set[Finding]) -> None:
    if not source.library:
        return
    for match in PUBLIC_FN.finditer(source.code):
        what = error_channel(return_type(source.code, match.end()), source)
        if what and not hidden(source.code, match.start()):
            message = f"{match.group(1)} returns {what}; a library returns its own error type"
            findings.add(Finding(source.where(match.start()), ERROR_RULE, message))
    for match in PUBLIC_TYPE.finditer(source.code):
        value = re.match(r"[^=;]*=([^;]*);", source.code[match.end() :])
        what = error_channel(value.group(1), source) if value else None
        if what and not hidden(source.code, match.start()):
            message = f"type {match.group(1)} is {what}; a library returns its own error type"
            findings.add(Finding(source.where(match.start()), ERROR_RULE, message))


def body_after(code: str, index: int) -> tuple[int, int] | None:
    """The braces of the body that starts at or after `index`, if one does."""
    depth = 0
    while index < len(code):
        char = code[index]
        depth += char in "(["
        depth -= char in ")]"
        if char == "{" and depth == 0:
            return index, closing(code, index)
        if char == ";" and depth == 0:
            return None
        index += 1
    return None


def closure_body(code: str, bar: int) -> tuple[int, int] | None:
    params_end = code.find("|", bar + 1)
    if params_end < 0:
        return None
    rest = code[params_end + 1 :]
    head = re.match(r"\s*(?:->[^{]*)?\{", rest)
    if not head:
        return None
    open_index = params_end + 1 + head.end() - 1
    return open_index, closing(code, open_index)


def async_spans(code: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for block in ASYNC_BLOCK.finditer(code):
        spans.append((block.end() - 1, closing(code, block.end() - 1)))
    for function in ASYNC_FN.finditer(code):
        body = body_after(code, function.end())
        if body:
            spans.append(body)
    for closure in ASYNC_CLOSURE.finditer(code):
        body = closure_body(code, closure.end() - 1)
        if body:
            spans.append(body)
    return spans


def offloaded(code: str) -> list[tuple[int, int]]:
    """The argument lists of the calls that move work off the async worker."""
    return [(call.end() - 1, closing(code, call.end() - 1)) for call in OFFLOAD.finditer(code)]


def inside(offset: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= offset < end for start, end in spans)


def blocking(path: str) -> bool:
    return path in BLOCKING_PATHS or path.startswith(BLOCKING_PREFIXES)


def blocking_calls(source: Source, start: int, end: int) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for call in CALL.finditer(source.code, start, end):
        path = resolve(call.group(1), source.imports)
        if blocking(path):
            found.append((call.start(), path))
    for method in BLOCKING_METHOD.finditer(source.code, start, end):
        found.append((method.start(1), method.group(1)))
    return found


def check_async_blocking(source: Source, findings: set[Finding]) -> None:
    exempt = offloaded(source.code)
    for start, end in async_spans(source.code):
        for offset, path in blocking_calls(source, start, end):
            if inside(offset, exempt):
                continue
            message = f"{path} blocks the runtime's worker thread inside an async body; await an async API or move it into spawn_blocking"
            findings.add(Finding(source.where(offset), ASYNC_RULE, message))


def defined_functions(code: str) -> list[tuple[int, str]]:
    """Every function with a body, other than `main`, by offset and name."""
    found: list[tuple[int, str]] = []
    for function in FUNCTION.finditer(code):
        if function.group(1) != "main" and body_after(code, function.end()):
            found.append((function.start(), function.group(1)))
    return found


def check_unit_tests(source: Source, findings: set[Finding]) -> None:
    if source.module is None or source.tested:
        return
    functions = defined_functions(source.code)
    if functions:
        message = f"{source.rel} has functions and no #[test] beside them; add a #[cfg(test)] mod tests to the file"
        findings.add(Finding(source.where(functions[0][0]), TESTS_RULE, message))


def derives_before(code: str, start: int) -> list[str]:
    """The derive names in the attributes directly above the item at `start`."""
    previous = max(code.rfind(mark, 0, start) for mark in ";{}")
    names: list[str] = []
    for derive in DERIVE.finditer(code, previous + 1, start):
        names.extend(segments(name)[-1] for name in split_top_level(derive.group(1)) if segments(name))
    return names


def fields_of(text: str) -> list[tuple[str, str]]:
    """The named fields of a braced field list, as name and type."""
    fields: list[tuple[str, str]] = []
    for item in split_top_level(text):
        item = re.sub(r"#\[[^\]]*\]", "", item)
        item = re.sub(r"^\s*pub(?:\s*\([^)]*\))?\s+", "", item)
        named = re.match(r"\s*(?:r#)?([A-Za-z_]\w*)\s*:(.*)", item, re.S)
        if named:
            fields.append((named.group(1), collapse(named.group(2))))
    return fields


def item_fields(code: str, kind: str, after: int) -> list[tuple[str, str]]:
    body = body_after(code, after)
    if not body:
        return []
    inner = code[body[0] + 1 : body[1] - 1]
    if kind == "struct":
        return fields_of(inner)
    found: list[tuple[str, str]] = []
    for variant in re.finditer(r"\b[A-Za-z_]\w*\s*\{", inner):
        start = variant.end() - 1
        found.extend(fields_of(inner[start + 1 : closing(inner, start) - 1]))
    return found


def secret(name: str, type_text: str) -> bool:
    named = name.lower() in SECRET_NAMES or any(name.lower().endswith("_" + each) for each in SECRET_NAMES)
    return named and bool(RAW_TEXT.match(type_text))


def check_redaction(source: Source, findings: set[Finding]) -> None:
    for item in TYPE_ITEM.finditer(source.code):
        revealing = [name for name in derives_before(source.code, item.start()) if name in REVEALING_DERIVES]
        if not revealing:
            continue
        exposed = [name for name, kind in item_fields(source.code, item.group(1), item.end()) if secret(name, kind)]
        if exposed:
            previous = max(source.code.rfind(mark, 0, item.start()) for mark in ";{}")
            attribute = DERIVE.search(source.code, previous + 1, item.start())
            message = f"{item.group(2)} derives {revealing[0]} over {exposed[0]}; hold it in a redacting type or write the impl that redacts it"
            findings.add(Finding(source.where(attribute.start() if attribute else item.start()), REDACTION_RULE, message))


CHECKS = (check_error_types, check_async_blocking, check_unit_tests, check_redaction)


def resolve_module(path: list[str], module: tuple[str, ...]) -> tuple[str, ...]:
    """A `crate`, `self` or `super` path, as absolute segments under the crate."""
    current: list[str] = []
    for index, segment in enumerate(path):
        if index == 0 and segment == "crate":
            current = []
        elif index == 0 and segment in ("self", "super"):
            current = list(module) if segment == "self" else list(module[:-1])
        elif segment == "super":
            current = current[:-1]
        else:
            return tuple(current + path[index:])
    return tuple(current)


def target_module(resolved: tuple[str, ...], modules: set[tuple[str, ...]]) -> tuple[str, ...] | None:
    for length in range(len(resolved), -1, -1):
        if resolved[:length] in modules:
            return resolved[:length]
    return None


def lineage(first: tuple[str, ...], second: tuple[str, ...]) -> bool:
    """Whether one module is the other or an ancestor of it."""
    shorter = min(len(first), len(second))
    return first[:shorter] == second[:shorter]


def references(source: Source) -> list[tuple[int, list[str]]]:
    """Every module path the file names, in a `use` or inline, by offset."""
    found = [(match.start(), segments(match.group(0))) for match in MODULE_PATH.finditer(source.code)]
    for declaration in USE.finditer(source.code):
        found.extend((declaration.start(), segments(path)) for _, path in expand_use(declaration.group(1), []))
    return found


def module_edges(sources: list[Source]) -> dict[tuple[str, ...], dict[tuple[str, ...], str]]:
    """The edges between modules of one crate, each with where it is first made."""
    modules = {source.module for source in sources if source.module is not None}
    edges: dict[tuple[str, ...], dict[tuple[str, ...], str]] = {module: {} for module in modules}
    for source in sources:
        if source.module is None:
            continue
        for offset, path in sorted(references(source)):
            if path[0] not in ("crate", "self", "super"):
                continue
            target = target_module(resolve_module(path, source.module), modules)
            if target is not None and not lineage(source.module, target):
                edges[source.module].setdefault(target, source.where(offset))
    return edges


def unwind(parent: dict[tuple[str, ...], tuple[str, ...]], last: tuple[str, ...], start: tuple[str, ...]) -> list:
    path = [last]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return [*reversed(path), start]


def cycle_from(start: tuple[str, ...], edges: dict[tuple[str, ...], dict[tuple[str, ...], str]]) -> list:
    """The shortest cycle from `start` back to it, or nothing."""
    parent: dict[tuple[str, ...], tuple[str, ...]] = {start: start}
    queue = [start]
    while queue:
        node = queue.pop(0)
        if start in edges.get(node, {}):
            return unwind(parent, node, start)
        for following in sorted(edges.get(node, {})):
            parent.setdefault(following, node)
            if parent[following] == node and following != start:
                queue.append(following)
    return []


def reachable(start: tuple[str, ...], edges: dict[tuple[str, ...], dict[tuple[str, ...], str]]) -> set:
    """Every module `start` reaches, itself only when a cycle returns to it."""
    seen: set[tuple[str, ...]] = set()
    queue = list(edges.get(start, {}))
    while queue:
        node = queue.pop()
        if node not in seen:
            seen.add(node)
            queue.extend(edges.get(node, {}))
    return seen


def components(edges: dict[tuple[str, ...], dict[tuple[str, ...], str]]) -> list[set]:
    """The strongly connected components that hold a cycle, each once."""
    reach = {node: reachable(node, edges) for node in edges}
    found: list[set] = []
    covered: set[tuple[str, ...]] = set()
    for node in sorted(edges):
        if node in reach[node] and node not in covered:
            component = {other for other in reach[node] if node in reach[other]}
            covered |= component
            found.append(component)
    return found


def name_of(module: tuple[str, ...]) -> str:
    return "::".join(("crate", *module))


def cycle_message(cycle: list, component: set) -> str:
    message = " -> ".join(name_of(module) for module in cycle)
    others = sorted(component - set(cycle))
    if others:
        verb = "is" if len(others) == 1 else "are"
        message += f"; {', '.join(name_of(module) for module in others)} {verb} in the same cycle"
    return message + "; break it by moving what both need below both"


def check_module_cycles(sources: list[Source], findings: set[Finding]) -> None:
    by_crate: dict[Path, list[Source]] = {}
    for source in sources:
        if source.crate is not None and source.module is not None:
            by_crate.setdefault(source.crate, []).append(source)
    for members in by_crate.values():
        edges = module_edges(members)
        for component in components(edges):
            inside_edges = {node: {key: value for key, value in edges[node].items() if key in component} for node in component}
            cycle = cycle_from(min(component), inside_edges)
            findings.add(Finding(edges[cycle[0]][cycle[1]], DIRECTION_RULE, cycle_message(cycle, component)))


def manifests(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_dir():
            found.extend(path for path in sorted(root.rglob("Cargo.toml")) if not skipped(path, root))
    return found


def read_manifest(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except tomllib.TOMLDecodeError:
        return {}


def ahrena(table: dict) -> dict:
    metadata = table.get("metadata", {})
    return metadata.get("ahrena", {}) if isinstance(metadata, dict) else {}


def dependency_names(manifest: dict) -> list[tuple[str, str]]:
    """Each normal dependency, as the key written and the package it names."""
    found: list[tuple[str, str]] = []
    for key, spec in manifest.get("dependencies", {}).items():
        package = spec.get("package", key) if isinstance(spec, dict) else key
        found.append((key, package))
    return found


def line_of(path: Path, key: str, base: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    found = re.search(rf"^\s*{re.escape(key)}\s*=", text, re.M)
    line = text.count("\n", 0, found.start()) + 1 if found else 1
    return f"{display(path, base)}:{line}"


def check_layers(workspace: Path, layers: list[str], base: Path, findings: set[Finding]) -> None:
    rank = {layer: index for index, layer in enumerate(layers)}
    members: dict[str, tuple[Path, dict]] = {}
    for path in sorted(workspace.parent.rglob("Cargo.toml")):
        manifest = read_manifest(path)
        package = manifest.get("package", {})
        if path != workspace and "name" in package and not skipped(path, workspace.parent):
            members[package["name"]] = (path, manifest)
    for name, (path, manifest) in members.items():
        layer = ahrena(manifest["package"]).get("layer")
        if layer is not None and layer not in rank:
            message = f"{name} declares layer {layer}, which the workspace does not list"
            findings.add(Finding(line_of(path, "layer", base), DIRECTION_RULE, message, 2))
            continue
        for key, package in dependency_names(manifest):
            other = ahrena(members[package][1]["package"]).get("layer") if package in members else None
            if layer in rank and other in rank and rank[other] > rank[layer]:
                message = f"{name} ({layer}) depends on {package} ({other}); a layer depends only on the layers below it"
                findings.add(Finding(line_of(path, key, base), DIRECTION_RULE, message, 2))


def check_workspaces(roots: list[Path], base: Path, findings: set[Finding]) -> None:
    for path in manifests(roots):
        workspace = read_manifest(path).get("workspace", {})
        layers = ahrena(workspace).get("layers")
        if isinstance(layers, list):
            check_layers(path, [str(layer) for layer in layers], base, findings)




def display(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def skipped(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts[:-1] if path != root else ()
    return any(part.startswith(".") or part in SKIP_NAMES for part in parts)


def sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
            continue
        found.extend(
            path for path in sorted(root.rglob("*.rs")) if path.name != "tests.rs" and not skipped(path, root)
        )
    return found


def crate_root(path: Path) -> Path | None:
    for parent in path.parents:
        if (parent / "Cargo.toml").is_file():
            return parent
    return None


def in_library(path: Path) -> bool:
    """Whether the file is a library crate's own source, not a binary's."""
    root = crate_root(path)
    if root is None:
        return False
    manifest = (root / "Cargo.toml").read_text(encoding="utf-8", errors="replace")
    if not ((root / "src" / "lib.rs").is_file() or "[lib]" in manifest):
        return False
    parts = path.relative_to(root).parts
    return parts[:1] == ("src",) and parts[1:2] != ("bin",) and parts != ("src", "main.rs")


def module_path(path: Path) -> tuple[Path, tuple[str, ...]] | None:
    """The crate and module a file under `src/` is, or None for any other file.

    `lib.rs` is the crate root, and so is `main.rs` when there is no
    `lib.rs`. Each binary under `src/bin/` is a crate of its own, rooted at
    `src/bin/<name>.rs` or `src/bin/<name>/main.rs`.
    """
    root = crate_root(path)
    if root is None:
        return None
    parts = path.relative_to(root).parts
    if parts[:1] != ("src",):
        return None
    if parts[1:2] == ("bin",):
        return binary_module(root, parts[2:])
    if parts == ("src", "main.rs") and (root / "src" / "lib.rs").is_file():
        return None
    return root, module_of(parts[1:])


def module_of(parts: tuple[str, ...]) -> tuple[str, ...]:
    """The module a file is, from its path below the crate root's directory."""
    if parts in (("lib.rs",), ("main.rs",)):
        return ()
    module = list(parts)
    module[-1] = module[-1].removesuffix(".rs")
    return tuple(module[:-1] if module[-1] == "mod" else module)


def binary_module(root: Path, parts: tuple[str, ...]) -> tuple[Path, tuple[str, ...]] | None:
    if len(parts) == 1:
        return root / "src" / "bin" / parts[0].removesuffix(".rs"), ()
    return root / "src" / "bin" / parts[0], module_of(parts[1:])


def sibling_tested(path: Path, masked: str) -> bool:
    """Whether the file declares a `tests.rs` beside it that holds a test."""
    if not EXTERNAL_TESTS.search(masked):
        return False
    folder = path.parent if path.name in ("lib.rs", "main.rs", "mod.rs") else path.parent / path.stem
    sibling = folder / "tests.rs"
    return sibling.is_file() and bool(TEST_ATTRIBUTE.search(mask(sibling.read_text(encoding="utf-8", errors="replace"))))


def load(path: Path, base: Path) -> Source:
    masked = mask(path.read_text(encoding="utf-8", errors="replace"))
    code = without_tests(masked)
    located = module_path(path)
    return Source(
        display(path, base),
        code,
        in_library(path),
        imports_of(code),
        boxed_aliases(code),
        located[1] if located else None,
        located[0] if located else None,
        bool(TEST_ATTRIBUTE.search(masked)) or sibling_tested(path, masked),
    )


def report(findings: set[Finding], checked: int) -> int:
    if not findings:
        print(f"{checked} file(s), no failures.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s):\n")
    for finding in sorted(findings, key=lambda each: (each.where, each.rule)):
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd().resolve()
    findings: set[Finding] = set()
    loaded = [load(path, base) for path in sources(roots)]
    for source in loaded:
        for check in CHECKS:
            check(source, findings)
    check_module_cycles(loaded, findings)
    check_workspaces(roots, base, findings)
    return report(findings, len(loaded))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
