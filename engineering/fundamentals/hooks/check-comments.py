#!/usr/bin/env python3
"""Detector for rules/comment-pointers.md: a comment points, or it goes.

Decides one condition stated in one rule:

    engineering/fundamentals/rules/comment-pointers.md
      1. a comment a change adds or edits that carries no durable pointer and is
         no permitted exemption

This is part 3 of Barte's check-comments.py, generalised into this framework.
Parts 1 and 2 already live here and this detector does not repeat them: a
comment whose text parses as Python is commented-out code, owned by condition 3
of rules/clean-code.md; a comment carrying a TODO, TBD, FIXME or XXX that names
no issue is a debt marker, owned by condition 1 of rules/debt-markers.md. What
is left after those two is this condition's subject: a comment that carries
alphabetic prose and points at nothing durable.

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
by prefix, or a separator with no alphabetic word. Each is machinery, a legal
notice or visual structure wearing a comment's syntax, and each is asserted
rather than measured, the way rules/debt-markers.md asserts its marker list.

Python only, and comments only. The standard library ships one parser, this
plugin takes no dependency, and a docstring is a string literal rather than a
comment: it is the documented interface of the thing it opens, reached by
tooling, and it does not rot the way an inline aside does. So this module, and
its test, carry all of their own rationale in docstrings, with no bare prose
`#` comment, because the PR-scoped self-check runs this detector over the
framework's own hooks and a prose comment here would redden its own pull
request. The only inline comments it allows itself are word-free separators.

The condition's subject is a change rather than a file, so the change is a
second, explicit input. `--changed <spec>` passes the spec to a pinned git diff
and the condition is decided over the lines that diff adds and no others; with
no `--changed`, every line of every file the run was handed is in scope.
Defaulting to every line is deliberate: a gate that defaults to seeing less than
it was handed is a gate that passes by seeing nothing. The diff machinery is
check-structure.py's, and lives in changes.py beside both, so the change-scoped
detectors scope a change the same way and a local run agrees with CI.

`--fix` removes the offending comment. A full-line comment, one with only
whitespace before the `#`, is deleted line and all; an inline comment is
stripped from the `#` to the end of the line with the code kept; the fix is
idempotent, and it invents no pointer, because it cannot know which ADR or issue
the author meant. The review route runs this detector report-only; `--fix`
belongs to the fixer agent Erodos (ADR-014) and to a pre-commit hook, so that a
reviewer never reads its own edit.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changes import CHANGED_FLAG, Unavailable, report, scoped, split_argv  # noqa: E402

SKIP_DIRS = frozenset(
    ".git .hg .svn .tox .nox .venv venv .eggs .mypy_cache .pytest_cache"
    " .ruff_cache __pycache__ node_modules build dist".split()
)


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
    """One file, as text, with the lines this run is scoped to.

    The comment scan needs the text and the display path; the scope is the lines
    `--changed` resolved, or None for every line. No tree: this detector reads
    comments by tokenising, and parses only each comment body in isolation.
    """

    rel: str
    text: str
    scope: frozenset[int] | None = None

    def in_scope(self, line: int) -> bool:
        return self.scope is None or line in self.scope


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
    """Whether a comment is machinery, a legal notice, a directive or a separator."""
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
    """Whether another condition owns this comment: commented-out code or a marker."""
    if _is_code(comment):
        return True
    return DEBT_MARKER.search(QUOTED.sub("", comment)) is not None


def _offending(src: Source):
    """Each in-scope comment this condition flags: prose, no pointer, no exemption."""
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


def check_comment_pointers(src: Source, findings: list[Finding]) -> None:
    for token in _offending(src):
        findings.append(
            Finding(
                f"{src.rel}:{token.start[0]}",
                "comment-pointers",
                1,
                f"this comment is prose with no durable pointer: {token.string.strip()!r}. "
                "Point it at an ADR or an issue — ADR-N or #N, a brief description after it is "
                "fine — or do what it says and delete it; a comment that explains code rots "
                "against every change that passes it",
            )
        )


def fix_source(src: Source, path: Path) -> list[str]:
    """Remove each offending comment and rewrite the file. Returns what was removed.

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

FIX_FLAG = "--fix"


# ----------------------------------------------------------------------------


def sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
            continue
        for path in sorted(root.rglob("*.py")):
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
        return Source(rel, path.read_text(encoding="utf-8"), scope)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"{rel}\n    skipped, this file could not be read: {exc}", file=sys.stderr)
        return None



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
        if source is not None:
            removed.extend(fix_source(source, path))
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
        check_comment_pointers(source, findings)
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
