#!/usr/bin/env python3
"""Detector for the Rust conditions that the source decides and Clippy does not.

Decides one condition in each of two rules:

    engineering/rust/rules/error-types.md
      1. a public function or type alias of a library crate exposes an opaque
         error: anyhow's or eyre's, a boxed `dyn Error`, or a string

    engineering/rust/rules/async-blocking.md
      1. a call inside an async body that blocks the thread it runs on: a
         `std::thread::sleep`, a `std::fs` function, a synchronous connect, a
         `blocking_` method, or reqwest's blocking client

Every other condition of those two rules, and every condition of the other
eight Rust rules, is decided by Clippy, by rustc, by a cargo tool the
consuming project runs, or by a reviewer, and each rule says which. This
script exists for the two that none of those decides. Clippy has no lint for
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
from dataclasses import dataclass, field
from pathlib import Path

ERROR_RULE = "error-types"
ASYNC_RULE = "async-blocking"

# #287: dot-prefixed directories are skipped by shape; tests and benches hold test code.
SKIP_NAMES = frozenset({"target", "vendor", "node_modules", "tests", "benches"})


RAW_STRING = re.compile(r'(?<![\w])(?:b|c)?r(#*)"')
STRING = re.compile(r'(?<![\w])(?:b|c)?"')
CHAR = re.compile(r"(?<![\w])b?'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.)|[^\\'\n])'")


CFG_TEST = re.compile(r"#\[\s*cfg\s*\(\s*test\s*\)\s*\]")


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




@dataclass(frozen=True)
class Finding:
    """One failure: the path with its line, the rule, and what was found."""

    where: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition 1: {self.message}"


@dataclass
class Source:
    """One file, read once.

    `rel` is the path to report, relative to the working directory. `code` is
    the text with comments, literals and test items blanked. `library` says
    whether the file is a library crate's own source. `imports` maps each name
    a `use` binds to the full path it binds, and `boxed_aliases` maps each type
    alias the file declares for a boxed error to what it names.
    """

    rel: str
    code: str
    library: bool
    imports: dict[str, str] = field(default_factory=dict)
    boxed_aliases: dict[str, str] = field(default_factory=dict)

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


def without_tests(code: str) -> str:
    """The code with every item under `#[cfg(test)]` blanked.

    The item is whatever the attribute decorates, up to its `;` or through its
    braces, so a test module, a test-only function and a test-only import all
    go the same way.
    """
    for attribute in list(CFG_TEST.finditer(code)):
        brace = code.find("{", attribute.end())
        semicolon = code.find(";", attribute.end())
        if brace < 0 or (0 <= semicolon < brace):
            continue
        end = closing(code, brace)
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


CHECKS = (check_error_types, check_async_blocking)




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


def load(path: Path, base: Path) -> Source:
    code = without_tests(mask(path.read_text(encoding="utf-8", errors="replace")))
    return Source(display(path, base), code, in_library(path), imports_of(code), boxed_aliases(code))


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
    paths = sources(roots)
    for path in paths:
        source = load(path, base)
        for check in CHECKS:
            check(source, findings)
    return report(findings, len(paths))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
