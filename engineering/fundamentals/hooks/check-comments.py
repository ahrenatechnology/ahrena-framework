#!/usr/bin/env python3
"""Detector for rules/comment-pointers.md: a comment points, or it goes.

Decides one condition stated in one rule:

    engineering/fundamentals/rules/comment-pointers.md
      1. a comment a change adds or edits that carries no durable pointer and is
         no permitted exemption

The condition began as part 3 of Barte's check-comments.py and was generalised
into this framework for Python; this module generalises it again, across the
five languages that detector reads: Python, TypeScript, JavaScript, shell and
SQL. The readers are ported from the same downstream engine, so a consumer can
retire its own copy and consume this one, which is the whole point of a generic,
deterministic check living upstream.

A durable pointer is an ADR or an issue. ADR-N names a decision record that
lives in the repository and records what was refused; its number is zero-padded
here, so the pattern allows a leading zero. #N names a unit of work on the
forge; its number carries no leading zero, the spelling rules/debt-markers.md
and contributing/rules/branch-naming.md already require. A URL is not durable:
it points outside the repository at something nobody here controls, so it rots
as silently as the prose it would replace, and it is refused. The comment need
only contain a pointer, not be only a pointer, so a pointer followed by a brief
single-line description is clean. A pointer quoted in backticks is prose about
pointers and does not count, the backtick escape rules/debt-markers.md takes
from foundation/rules/completeness.md.

A comment is exempt when it is not explanatory prose at all: a shebang, a PEP
263 coding declaration, a license header, a directive to another tool matched
by prefix, the documentation block directly above a TypeScript or JavaScript
`export`, or a separator with no alphabetic word. Each is machinery, a legal
notice, an interface or visual structure wearing a comment's syntax, and each is
asserted rather than measured, the way rules/debt-markers.md asserts its marker
list.

Python is read through the standard library's tokenizer, so a `#` inside a
string is never a comment, and the Python path alone delegates: a comment whose
text parses as Python is commented-out code, owned by condition 3 of
rules/clean-code.md, and a comment carrying a bare TODO, TBD, FIXME or XXX is a
debt marker, owned by condition 1 of rules/debt-markers.md. Those two rules are
Python-only, so for the other four languages there is nothing to delegate to and
nothing is delegated: a non-Python comment is a durable pointer or a permitted
exemption, or it is this condition's finding. There is no second condition; a
bare marker in a non-Python comment is simply pointerless prose. TypeScript and
JavaScript go through a lexer that tracks strings, template literals, regular
expressions and both comment forms; shell and SQL are read for whole-line
comments only. Every reader is conservative in the same direction: where it
cannot tell a comment from data it returns None and the file is skipped by name,
because --fix deletes what is reported and a deleted piece of a string is a
defect this hook would have written itself.

Comments only, and this module and its test carry all of their own rationale in
docstrings, with no bare prose `#` or `//` comment, because the PR-scoped
self-check runs this detector over the framework's own hooks and a prose comment
here would redden its own pull request. The only inline comments it allows
itself are word-free separators. A docstring is a string literal rather than a
comment: it is the documented interface of the thing it opens, reached by
tooling, and it does not rot the way an inline aside does.

The condition's subject is a change rather than a file, so the change is a
second, explicit input. `--changed <spec>` passes the spec to a pinned git diff
and the condition is decided over the lines that diff adds and no others; with
no `--changed`, every line of every file the run was handed is in scope.
Defaulting to every line is deliberate: a gate that defaults to seeing less than
it was handed is a gate that passes by seeing nothing. The diff machinery is
check-structure.py's, and lives in changes.py beside both, so the change-scoped
detectors scope a change the same way and a local run agrees with CI.

`--fix` removes the offending comment. A full-line comment, one with only
whitespace before it, is deleted line and all; an inline comment is stripped
with the code kept; a block comment goes whole; the fix is idempotent, and it
invents no pointer, because it cannot know which ADR or issue the author meant.
The review route runs this detector report-only; `--fix` belongs to the fixer
agent Erodos (ADR-014) and to a pre-commit hook, so that a reviewer never reads
its own edit.

Usage:
    python3 engineering/fundamentals/hooks/check-comments.py [path ...]
    python3 engineering/fundamentals/hooks/check-comments.py --changed --cached [path ...]
    python3 engineering/fundamentals/hooks/check-comments.py --changed origin/main...HEAD [path ...]
    python3 engineering/fundamentals/hooks/check-comments.py --fix --changed --cached [path ...]
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changes import CHANGED_FLAG, Unavailable, report, scoped, split_argv  # noqa: E402

SKIP_DIRS = frozenset(
    ".git .hg .svn .tox .nox .venv venv .eggs .mypy_cache .pytest_cache"
    " .ruff_cache __pycache__ node_modules build dist".split()
)

PYTHON_SUFFIXES = (".py", ".pyi")
SCRIPT_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
SHELL_SUFFIXES = (".sh", ".bash")
SQL_SUFFIXES = (".sql",)
MARKUP_SUFFIXES = frozenset({".tsx", ".jsx", ".js", ".mjs", ".cjs"})


# ----------------------------------------------------------------------------


@dataclass
class Finding:
    where: str
    rule: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    """One file, as text, with the lines this run is scoped to and its syntax.

    The comment scan needs the text, the display path and the suffix that picks
    the reader; the scope is the lines `--changed` resolved, or None for every
    line. No tree: the Python path reads comments by tokenising and parses only
    each comment body in isolation, and the other readers lex for comments alone.
    """

    rel: str
    text: str
    scope: frozenset[int] | None = None
    suffix: str = ""

    def in_scope(self, line: int) -> bool:
        return self.scope is None or line in self.scope

    def touches(self, first: int, last: int) -> bool:
        """Whether any line a comment spans is one the run is scoped to."""
        return self.scope is None or any(line in self.scope for line in range(first, last + 1))


# ----------------------------------------------------------------------------

COMMENT_STATEMENTS: tuple[type, ...] = (
    ast.Assign,
    ast.AugAssign,
    ast.Return,
    ast.Raise,
    ast.Import,
    ast.ImportFrom,
    ast.Delete,
    ast.Assert,
    ast.Global,
    ast.Nonlocal,
)

TOOL_DIRECTIVES = ("type:", "noqa", "pragma", "pylint", "mypy", "ruff", "fmt:", "isort", "!")


def _is_code(comment: str) -> bool:
    """Whether a comment's text parses as a Python statement that carries an effect.

    The same predicate condition 3 of rules/clean-code.md uses, so a comment this
    one would flag is left to that condition and never double-flagged here.
    """
    body = comment.lstrip("#").strip()
    if not body or body.startswith(TOOL_DIRECTIVES):
        return False
    try:
        parsed = ast.parse(body)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    if not parsed.body:
        return False
    head = parsed.body[0]
    if isinstance(head, COMMENT_STATEMENTS):
        return True
    return isinstance(head, ast.Expr) and isinstance(head.value, ast.Call)


def _comments(text: str) -> list[tokenize.TokenInfo]:
    """Every `#` comment token in the file, or none when it will not tokenise."""
    try:
        stream = tokenize.generate_tokens(io.StringIO(text).readline)
        return [token for token in stream if token.type == tokenize.COMMENT]
    except (tokenize.TokenError, SyntaxError, IndentationError, ValueError):
        return []


# ----------------------------------------------------------------------------

MARKERS = ("TODO", "TBD", "FIXME", "XXX")

DEBT_MARKER = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(MARKERS) + r")(?![A-Za-z0-9_])")

POINTER = re.compile(r"(?<![0-9A-Za-z])(?:ADR-[0-9]+|#[1-9][0-9]*)")

QUOTED = re.compile(r"(`+)(?:(?!\1)[\s\S])*?\1")

CODING = re.compile(r"coding[:=]\s*[-\w.]+")

ALPHABETIC = re.compile(r"[A-Za-z]")

LICENSE_TOKENS = (
    "spdx-license-identifier",
    "copyright",
    "licensed under",
    "all rights reserved",
    "(c)",
)

EXEMPT_PREFIXES = (
    "type:",
    "noqa",
    "pragma",
    "pylint",
    "mypy",
    "ruff",
    "fmt:",
    "isort",
    "nosec",
    "pyright",
    "flake8",
    "yapf",
    "black",
    "coding",
)


def _exempt(comment: str) -> bool:
    """Whether a Python comment is machinery, a legal notice, a directive or a separator."""
    body = comment.lstrip("#").strip()
    if not body:
        return True
    if comment.startswith("#!"):
        return True
    if CODING.search(comment):
        return True
    if any(token in comment.lower() for token in LICENSE_TOKENS):
        return True
    if body.startswith(EXEMPT_PREFIXES):
        return True
    return ALPHABETIC.search(body) is None


def _delegated(comment: str) -> bool:
    """Whether another condition owns this Python comment: commented-out code or a marker."""
    if _is_code(comment):
        return True
    return DEBT_MARKER.search(QUOTED.sub("", comment)) is not None


def _offending(src: Source):
    """Each in-scope Python comment this condition flags: prose, no pointer, no exemption."""
    for token in _comments(src.text):
        line = token.start[0]
        if not src.in_scope(line):
            continue
        comment = token.string
        if _exempt(comment) or _delegated(comment):
            continue
        if POINTER.search(QUOTED.sub("", comment)):
            continue
        yield token


MESSAGE = (
    "this comment is prose with no durable pointer: {text!r}. Point it at an ADR or an issue — "
    "ADR-N or #N, a brief description after it is fine — or do what it says and delete it; a "
    "comment that explains code rots against every change that passes it"
)


def check_python(src: Source, findings: list[Finding]) -> None:
    for token in _offending(src):
        findings.append(
            Finding(
                f"{src.rel}:{token.start[0]}",
                "comment-pointers",
                1,
                MESSAGE.format(text=token.string.strip()),
            )
        )


def fix_python(src: Source, path: Path) -> list[str]:
    """Remove each offending Python comment and rewrite the file. Returns what was removed.

    A full-line comment is dropped line and all; an inline comment is stripped
    from the `#` to end-of-line with the code kept and trailing space removed.
    Idempotent, because the second run finds nothing left to remove.
    """
    offenders = {token.start[0]: token.start[1] for token in _offending(src)}
    if not offenders:
        return []
    removed: list[str] = []
    out: list[str] = []
    for number, raw in enumerate(src.text.splitlines(keepends=True), 1):
        col = offenders.get(number)
        if col is None:
            out.append(raw)
            continue
        removed.append(f"{src.rel}:{number} removed: {raw[col:].strip()!r}")
        code = raw[:col].rstrip()
        if code:
            out.append(code + "\n" if raw.endswith("\n") else code)
    path.write_text("".join(out), encoding="utf-8")
    return removed


# ----------------------------------------------------------------------------


@dataclass
class Comment:
    """One non-Python comment, by where it sits in the text the reader was handed."""

    start: int
    end: int
    line: int
    last: int
    text: str
    documents: bool = False

    @property
    def body(self) -> str:
        """The comment without the characters that open and close it."""
        if self.text.startswith("/*"):
            return self.text[2:-2].lstrip("*").strip()
        if self.text.startswith("//"):
            return self.text[2:].strip()
        if self.text.startswith("--"):
            return self.text.lstrip("-").strip()
        return self.text.lstrip("#").strip()

    @property
    def shown(self) -> str:
        first = self.text.splitlines()[0]
        return first if self.last == self.line else f"{first} ... ({self.last - self.line + 1} lines)"


def spot(text: str, start: int, end: int) -> Comment:
    line = text.count("\n", 0, start) + 1
    return Comment(start, end, line, line + text.count("\n", start, end), text[start:end])


def line_end(text: str, at: int) -> int:
    """Where the line holding `at` stops, before its terminator."""
    end = text.find("\n", at)
    end = len(text) if end < 0 else end
    return end - 1 if end > at and text[end - 1] == "\r" else end


SHEBANG = "#!"
WORD = re.compile(r"[A-Za-z0-9_$\u0080-￿]+")
REGEX_AFTER = frozenset(
    {
        "return",
        "typeof",
        "case",
        "do",
        "else",
        "in",
        "of",
        "void",
        "delete",
        "throw",
        "new",
        "yield",
        "await",
        "instanceof",
    }
)
CLOSING_TAG = re.compile(r"/[A-Za-z0-9_.:-]*\s*>")
EXPORTED = re.compile(r"[ \t]*(?:\r?\n)?[ \t]*export(?![A-Za-z0-9_$])")
VALUE = "0"
UNSURE = "\0"
OPERAND, OPERATOR, EITHER = "operand", "operator", "either"


class Script:
    """A lexer for TypeScript and JavaScript that finds comments and nothing else.

    It keeps the last significant token, because that is what tells a slash that
    divides from a slash that opens a regular expression. Where the token does
    not settle it, the rest of the line is passed over unread; where a misreading
    could carry past the line, through a template literal or a block comment, the
    lexer stops and what it found up to there is all it returns.

    Markup is the part it does not understand. In a file that may hold JSX, text
    between tags is not code, so a comment directly after a `>` and a `//`
    directly after a colon are passed over, not reported.
    """

    def __init__(self, text: str, suffix: str) -> None:
        self.text = text
        self.markup = suffix in MARKUP_SUFFIXES
        self.at = 0
        self.last = ""
        self.last_at = 0
        self.depths: list[int] = []
        self.found: list[Comment] = []
        self.trusted = True

    def comments(self) -> list[Comment] | None:
        if self.text.startswith(SHEBANG):
            self.at = line_end(self.text, 0)
        while self.trusted and self.at < len(self.text):
            self._step()
        return self.found

    def _step(self) -> None:
        char = self.text[self.at]
        two = self.text[self.at : self.at + 2]
        if char.isspace():
            self.at += 1
        elif two == "//":
            self._line_comment()
        elif two == "/*":
            self._block_comment()
        elif char == "/":
            self._slash()
        elif char in "'\"":
            self._string(char)
        elif char == "`":
            self._template()
        elif char in "{}":
            self._brace(char)
        else:
            self._token()

    def _note(self, token: str, at: int) -> None:
        self.last, self.last_at = token, at

    def _token(self) -> None:
        word = WORD.match(self.text, self.at)
        end = word.end() if word else self.at + 1
        self._note(self.text[self.at : end], self.at)
        self.at = end

    def _after_tag(self) -> bool:
        return self.markup and self.last == ">" and self.text[self.last_at - 1 : self.last_at] != "="

    def _skip_line(self) -> None:
        end = line_end(self.text, self.at)
        rest = self.text[self.at : end]
        if self.depths or "`" in rest or "/*" in rest:
            self.trusted = False
            return
        self.at = end
        self._note(UNSURE, end)

    def _line_comment(self) -> None:
        address = self.markup and self.text[self.at - 1 : self.at] == ":"
        if address or self._after_tag():
            self._skip_line()
            return
        end = line_end(self.text, self.at)
        self.found.append(spot(self.text, self.at, end))
        self.at = end

    def _block_comment(self) -> None:
        close = self.text.find("*/", self.at + 2)
        if close < 0:
            self.trusted = False
            return
        if not self._after_tag():
            comment = spot(self.text, self.at, close + 2)
            opens_doc = comment.text.startswith("/**") and len(comment.text) > 4
            comment.documents = opens_doc and EXPORTED.match(self.text, close + 2) is not None
            self.found.append(comment)
        self.at = close + 2

    def _slash(self) -> None:
        rest = self.text[self.at + 1 : line_end(self.text, self.at)]
        closes_tag = self.text.startswith("/>", self.at) or (
            self.last == "<" and CLOSING_TAG.match(self.text, self.at) is not None
        )
        before = OPERAND if closes_tag or "/" not in rest else self._before_slash()
        if before == OPERAND:
            self._note("/", self.at)
            self.at += 1
        elif before == OPERATOR:
            self._regex()
        else:
            self._skip_line()

    def _before_slash(self) -> str:
        last = self.last
        doubled = last in ("+", "-") and self.text[self.last_at - 1 : self.last_at] == last
        if last in (UNSURE, ")", "}") or doubled or (self.markup and last == ">"):
            return EITHER
        if last in REGEX_AFTER:
            return OPERATOR
        if last == "]" or WORD.fullmatch(last):
            return OPERAND
        return OPERATOR

    def _regex(self) -> None:
        at, end, in_class = self.at + 1, line_end(self.text, self.at), False
        while at < end:
            char = self.text[at]
            if char == "/" and not in_class:
                break
            in_class = char == "[" or (in_class and char != "]")
            at += 2 if char == "\\" else 1
        if at >= end:
            self._skip_line()
            return
        flags = WORD.match(self.text, at + 1)
        self._note(VALUE, at)
        self.at = flags.end() if flags else at + 1

    def _string(self, quote: str) -> None:
        at, end = self.at + 1, line_end(self.text, self.at)
        while at < end and self.text[at] != quote:
            at += 2 if self.text[at] == "\\" else 1
        if at < end:
            self._note(VALUE, at)
            self.at = at + 1
        elif self.text[end - 1 : end] == "\\":
            self.trusted = False
        else:
            self._skip_line()

    def _template(self) -> None:
        at = self.at + 1
        while at < len(self.text):
            if self.text[at] == "`":
                self._note(VALUE, at)
                self.at = at + 1
                return
            if self.text.startswith("${", at):
                self.depths.append(0)
                self._note("{", at)
                self.at = at + 2
                return
            at += 2 if self.text[at] == "\\" else 1
        self.trusted = False

    def _brace(self, char: str) -> None:
        if self.depths and char == "}" and self.depths[-1] == 0:
            self.depths.pop()
            self._template()
            return
        if self.depths:
            self.depths[-1] += 1 if char == "{" else -1
        self._note(char, self.at)
        self.at += 1


def script_reader(suffix: str) -> Callable[[str], list[Comment] | None]:
    return lambda text: Script(text, suffix).comments()


HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
COMMENT_AFTER = ";|&("
PLAIN, DOUBLE, ANSI = "'", '"', "$"


class Shell:
    """Whole-line comments of a shell script, outside quotes and here-documents.

    A line that opens with `#` inside a quoted string or a here-document is
    data. The quote state and the pending here-documents are carried from line
    to line. A command substitution opens a fresh context inside whatever quote
    holds it, so the state it interrupts is kept and restored at its closing
    parenthesis. A file that ends with any of the three still open was misread
    somewhere, so nothing from it is returned.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.quote = ""
        self.depth = 0
        self.outer: list[tuple[str, int]] = []
        self.pending: list[tuple[str, bool]] = []
        self.found: list[Comment] = []

    def comments(self) -> list[Comment] | None:
        offset = 0
        for line in self.text.split("\n"):
            self._line(line.rstrip("\r"), offset)
            offset += len(line) + 1
        return None if self.quote or self.pending or self.outer else self.found

    def _line(self, line: str, offset: int) -> None:
        if self.pending and not self.quote:
            word, tabbed = self.pending[0]
            if (line.lstrip("\t") if tabbed else line) == word:
                self.pending.pop(0)
            return
        indent = len(line) - len(line.lstrip())
        if not self.quote and line.startswith("#", indent):
            self.found.append(spot(self.text, offset + indent, offset + len(line)))
            return
        at = 0
        while at < len(line):
            at = self._advance(line, at)

    def _advance(self, line: str, at: int) -> int:
        char = line[at]
        if self.quote == PLAIN:
            self.quote = "" if char == PLAIN else PLAIN
            return at + 1
        if char == "\\":
            return at + 2
        if self.quote != ANSI and line.startswith("$(", at):
            self.outer.append((self.quote, self.depth))
            self.quote, self.depth = "", 0
            return at + 2
        if self.quote:
            closer = PLAIN if self.quote == ANSI else DOUBLE
            self.quote = "" if char == closer else self.quote
            return at + 1
        return self._code(line, at)

    def _code(self, line: str, at: int) -> int:
        char, before = line[at], line[at - 1 : at] if at else ""
        if char == PLAIN:
            self.quote = ANSI if before == "$" else PLAIN
        elif char == DOUBLE:
            self.quote = DOUBLE
        elif char == "#" and (not before or before.isspace() or before in COMMENT_AFTER):
            return len(line)
        elif line.startswith("<<<", at):
            return at + 3
        elif char in "()":
            self._parenthesis(char)
        heredoc = HEREDOC.match(line, at) if char == "<" else None
        if heredoc is None:
            return at + 1
        self.pending.append((heredoc.group(3), bool(heredoc.group(1))))
        return heredoc.end()

    def _parenthesis(self, char: str) -> None:
        if char == "(":
            self.depth += 1
        elif self.depth:
            self.depth -= 1
        elif self.outer:
            self.quote, self.depth = self.outer.pop()


def shell_comments(text: str) -> list[Comment] | None:
    return Shell(text).comments()


class Sql:
    """Whole-line `--` comments of a SQL file, outside quoted text.

    A backslash before a quote inside a string closes it in standard SQL and
    escapes it in an escape string, and nothing in the file says which. The scan
    stops there and keeps what it had. A string or block comment still open at
    the end of the file means the pairing was wrong earlier, and nothing is
    returned.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0
        self.broken = False
        self.found: list[Comment] = []

    def comments(self) -> list[Comment] | None:
        while self.at < len(self.text):
            self._step()
        return None if self.broken else self.found

    def _step(self) -> None:
        two = self.text[self.at : self.at + 2]
        if two == "--":
            self._line_comment()
        elif two == "/*":
            close = self.text.find("*/", self.at + 2)
            self.broken = close < 0
            self.at = len(self.text) if close < 0 else close + 2
        elif self.text[self.at] in "'\"":
            self._quoted(self.text[self.at])
        else:
            self.at += 1

    def _line_comment(self) -> None:
        end = line_end(self.text, self.at)
        head = self.text.rfind("\n", 0, self.at) + 1
        if not self.text[head : self.at].strip():
            self.found.append(spot(self.text, self.at, end))
        self.at = end

    def _quoted(self, quote: str) -> None:
        at = self.at + 1
        while at < len(self.text):
            char, after = self.text[at], self.text[at + 1 : at + 2]
            if char == "\\" and after == quote:
                self.at = len(self.text)
                return
            if char == quote and after != quote:
                self.at = at + 1
                return
            at += 2 if char == quote else 1
        self.broken = True
        self.at = len(self.text)


def sql_comments(text: str) -> list[Comment] | None:
    return Sql(text).comments()


# ----------------------------------------------------------------------------


def opening(*tokens: str) -> re.Pattern:
    """A pattern for a comment body that opens with one of the tokens, as a whole word."""
    return re.compile(
        "|".join(re.escape(token) + ("(?![A-Za-z0-9_])" if token[-1].isalnum() else "") for token in tokens)
    )


SCRIPT_DIRECTIVES = (
    "eslint-",
    "@ts-",
    "prettier-ignore",
    "istanbul",
    "c8",
    "v8 ignore",
    "biome-",
    "/ <reference",
    "/ <amd-",
    "@vite-ignore",
    "webpackChunkName",
    "webpackMode",
    "webpackPrefetch",
    "webpackPreload",
    "webpackIgnore",
    "webpackInclude",
    "webpackExclude",
    "webpackExports",
    "@__PURE__",
    "#__PURE__",
    "@__NO_SIDE_EFFECTS__",
    "#__NO_SIDE_EFFECTS__",
    "@jsx",
    "@jsxImportSource",
    "@jsxRuntime",
    "@jsxFrag",
    "@type",
    "@license",
    "@preserve",
)
SHELL_DIRECTIVES = ("shellcheck",)
SQL_DIRECTIVES = ("+goose", "+migrate", "migrate:", "liquibase", "changeset", "sqlfluff:", "noqa")


@dataclass(frozen=True)
class Reader:
    """A non-Python syntax: how to find its comments, and which open a directive."""

    name: str
    read: Callable[[str], list[Comment] | None]
    directives: re.Pattern


READERS: dict[str, Reader] = {}
for _suffix in SCRIPT_SUFFIXES:
    READERS[_suffix] = Reader("script", script_reader(_suffix), opening(*SCRIPT_DIRECTIVES))
for _suffix in SHELL_SUFFIXES:
    READERS[_suffix] = Reader("shell", shell_comments, opening(*SHELL_DIRECTIVES))
READERS[".sql"] = Reader("sql", sql_comments, opening(*SQL_DIRECTIVES))

HANDLED = frozenset(PYTHON_SUFFIXES) | READERS.keys()


def _exempt_other(comment: Comment, directives: re.Pattern) -> bool:
    """Whether a non-Python comment is documentation, machinery, a notice or a separator."""
    body = comment.body
    if not body or comment.documents:
        return True
    if comment.line == 1 and comment.text.startswith(SHEBANG):
        return True
    if any(token in comment.text.lower() for token in LICENSE_TOKENS):
        return True
    if directives.match(body):
        return True
    return ALPHABETIC.search(body) is None


def _other_offending(src: Source, reader: Reader, comments: list[Comment]) -> list[Comment]:
    """Each in-scope non-Python comment this condition flags: prose, no pointer, no exemption."""
    out: list[Comment] = []
    for comment in comments:
        if not src.touches(comment.line, comment.last):
            continue
        if _exempt_other(comment, reader.directives):
            continue
        if POINTER.search(QUOTED.sub("", comment.text)):
            continue
        out.append(comment)
    return out


def cut(text: str, comment: Comment) -> tuple[int, int, str]:
    """The span to replace so the comment is gone, and what goes in its place."""
    head = text.rfind("\n", 0, comment.start) + 1
    tail = text.find("\n", comment.end)
    tail = len(text) if tail < 0 else tail
    before, after = text[head : comment.start], text[comment.end : tail]
    if not before.strip() and not after.strip():
        return head, min(tail + 1, len(text)), ""
    if not after.strip():
        return head + len(before.rstrip()), comment.end + len(after) - len(after.lstrip(" \t")), ""
    return inline(text, comment, before)


def inline(text: str, comment: Comment, before: str) -> tuple[int, int, str]:
    """A block comment with code after it on its last line.

    The two tokens around it must stay two tokens, and a line break inside it
    must stay a line break, because JavaScript reads one as the end of a
    statement.
    """
    gap = len(text) - comment.end - len(text[comment.end :].lstrip(" \t"))
    if before.strip() and comment.last > comment.line:
        return comment.start, comment.end, "\r\n" if "\r\n" in comment.text else "\n"
    if not before.strip() or before[-1] in " \t":
        return comment.start, comment.end + gap, ""
    return comment.start, comment.end, "" if gap else " "


def fix_other(src: Source, path: Path, offenders: list[Comment]) -> list[str]:
    """Remove each offending non-Python comment and rewrite the file. Returns what was removed."""
    if not offenders:
        return []
    text = src.text
    removed: list[str] = []
    for comment in sorted(offenders, key=lambda found: found.start, reverse=True):
        start, end, filler = cut(text, comment)
        removed.append(f"{src.rel}:{comment.line} removed: {comment.shown!r}")
        text = text[:start] + filler + text[end:]
    path.write_text(text, encoding="utf-8")
    return removed


# ----------------------------------------------------------------------------


def check_source(src: Source, findings: list[Finding]) -> bool:
    """Append this file's findings; False when a reader could not tell comments from data."""
    if src.suffix in PYTHON_SUFFIXES:
        check_python(src, findings)
        return True
    reader = READERS[src.suffix]
    comments = reader.read(src.text)
    if comments is None:
        return False
    for comment in _other_offending(src, reader, comments):
        findings.append(
            Finding(f"{src.rel}:{comment.line}", "comment-pointers", 1, MESSAGE.format(text=comment.shown))
        )
    return True


def fix_one(src: Source, path: Path) -> list[str] | None:
    """Remove this file's offending comments; None when a reader could not tell them from data."""
    if src.suffix in PYTHON_SUFFIXES:
        return fix_python(src, path)
    reader = READERS[src.suffix]
    comments = reader.read(src.text)
    if comments is None:
        return None
    return fix_other(src, path, _other_offending(src, reader, comments))


# ----------------------------------------------------------------------------

FIX_FLAG = "--fix"


# ----------------------------------------------------------------------------


def sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            if root.suffix in HANDLED:
                found.append(root)
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in HANDLED:
                continue
            if SKIP_DIRS.isdisjoint(path.relative_to(root).parts):
                found.append(path)
    return found


def display_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def load(path: Path, rel: str, scope: frozenset[int] | None) -> Source | None:
    """The file as text, or None once the reason it could not be read is reported."""
    try:
        return Source(rel, path.read_text(encoding="utf-8"), scope, path.suffix)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"{rel}\n    skipped, this file could not be read: {exc}", file=sys.stderr)
        return None


def skipped(rel: str) -> None:
    print(f"{rel}\n    skipped, its comments cannot be told from its strings", file=sys.stderr)




def read(argv: list[str]) -> tuple[list[Path], dict[Path, frozenset[int]], str | None]:
    """The walked paths, the scope the change resolves, and the spec or None."""
    base = Path.cwd()
    rest, spec = split_argv(argv)
    paths = sources([Path(a).resolve() for a in rest] or [base])
    scope = scoped(spec, paths) if spec is not None else {}
    return paths, scope, spec


def run_fix(paths: list[Path], scope: dict[Path, frozenset[int]], spec: str | None, base: Path) -> int:
    removed: list[str] = []
    for path in paths:
        lines = None if spec is None else scope.get(path, frozenset())
        source = load(path, display_path(path, base), lines)
        if source is None:
            continue
        taken = fix_one(source, path)
        if taken is None:
            skipped(source.rel)
            continue
        removed.extend(taken)
    for line in removed:
        print(line)
    print(f"removed {len(removed)} comment(s).")
    return 0


def run_report(paths: list[Path], scope: dict[Path, frozenset[int]], spec: str | None, base: Path) -> int:
    findings: list[Finding] = []
    checked = 0
    unparsed = 0
    for path in paths:
        lines = None if spec is None else scope.get(path, frozenset())
        source = load(path, display_path(path, base), lines)
        if source is None:
            unparsed += 1
            continue
        if not check_source(source, findings):
            skipped(source.rel)
            unparsed += 1
            continue
        checked += 1
    return report(findings, checked, unparsed)


def main(argv: list[str]) -> int:
    base = Path.cwd()
    fix = FIX_FLAG in argv
    try:
        paths, scope, spec = read([a for a in argv[1:] if a != FIX_FLAG])
    except Unavailable as exc:
        print(f"{CHANGED_FLAG}: {exc}", file=sys.stderr)
        return 2
    if fix:
        return run_fix(paths, scope, spec, base)
    return run_report(paths, scope, spec, base)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
