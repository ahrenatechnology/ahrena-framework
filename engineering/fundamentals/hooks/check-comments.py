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
it was handed is a gate that passes by seeing nothing. The diff machinery is the
one in check-structure.py, taken unchanged so that the two detectors scope the
same way and a local run agrees with CI: the diff is pinned against colour, a
replacement driver, a textconv filter and a dropped path prefix, each of which
empties or mis-points the scope while the run still exits 0; the spec is refused
when it is an option outside --cached and --staged; the output is decoded
leniently; and a `+++ ` row is read as a file header only where one can stand.
The no-dependency constraint forbids sharing this machinery in a module across
hooks, so it is duplicated here, the trade validate.yml documents for its own
harness.

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
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

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

CHANGED_FLAG = "--changed"
FIX_FLAG = "--fix"

SPEC_OPTIONS = ("--cached", "--staged")

DST_PREFIX = "b/"

PINNED = (
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--src-prefix=a/",
    f"--dst-prefix={DST_PREFIX}",
    "--unified=0",
)

HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

UNMERGED = ("diff --cc ", "diff --combined ", "* Unmerged path ")

ESCAPES = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
OCTAL = "01234567"


class Unavailable(Exception):
    """git could not answer, and the run must say so rather than see nothing."""


def git(args: list[str], cwd: Path) -> str:
    """git's standard output, decoded leniently.

    A diff carries whatever bytes the changed files carry, so a strict decode
    would raise inside subprocess and leave CI unable to tell a traceback from a
    finding. Every field this parser reads is ASCII, so a replaced byte in a
    content row costs nothing and the run completes.
    """
    try:
        done = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True)
    except OSError as exc:
        raise Unavailable(f"git could not be run: {exc}") from exc
    if done.returncode != 0:
        raise Unavailable(_decode(done.stderr).strip() or f"git exited {done.returncode}")
    return _decode(done.stdout)


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def unquote(field: str) -> str:
    """The path a diff header names, with git's C-style quoting undone."""
    if len(field) < 2 or not (field.startswith('"') and field.endswith('"')):
        return field
    body, out, at = field[1:-1], bytearray(), 0
    try:
        while at < len(body):
            if body[at] != "\\":
                out.extend(body[at].encode("utf-8"))
                at += 1
            elif body[at + 1] in OCTAL:
                out.append(int(body[at + 1 : at + 4], 8))
                at += 4
            else:
                out.extend(ESCAPES.get(body[at + 1], body[at + 1]).encode("utf-8"))
                at += 2
    except (IndexError, ValueError) as exc:
        raise Unavailable(f"git named a path this hook cannot read: {field} ({exc})") from exc
    return out.decode("utf-8", errors="replace")


def added_lines(diff: str, top: Path) -> dict[Path, set[int]]:
    """The lines each file gains, keyed by the path the walk will hand back.

    A `+++ ` row is a file header only where one can stand: straight after the
    matching `--- ` row, and never inside a hunk, whose body is consumed by the
    counts the header declares. Under --unified=0 an added source line renders
    with a single `+`, so a line whose own text begins `++ ` reaches this parser
    as `+++ `; read as a header it would re-point the scope at a path taken from
    somebody's source. Both locks guard that one input.
    """
    added: dict[Path, set[int]] = {}
    lines: set[int] | None = None
    source_header = False
    body = 0
    for row in diff.split("\n"):
        if body:
            body -= 0 if row.startswith("\\") else 1
            continue
        if row.startswith(UNMERGED):
            raise Unavailable(
                f"git gave no two-sided diff for an unresolved merge ({row.strip()!r}), and a "
                "file with no diff has no lines in scope. Finish the merge, or pass a revision"
            )
        if row.startswith("diff --git "):
            lines, source_header = None, False
            continue
        if row.startswith("+++ ") and source_header:
            target = unquote(row[4:])
            lines = None if target == "/dev/null" else added.setdefault(_target(top, target), set())
            source_header = False
            continue
        source_header = row.startswith("--- ")
        hunk = HUNK.match(row)
        if hunk is None:
            continue
        start, count = int(hunk.group(2)), int(hunk.group(3) or 1)
        body = int(hunk.group(1) or 1) + count
        if lines is not None:
            lines.update(range(start, start + count))
    return added


def _target(top: Path, target: str) -> Path:
    """The `+++ b/<path>` side of a file header, as an absolute path."""
    if not target.startswith(DST_PREFIX):
        raise Unavailable(
            f"git named the changed file {target!r}, which does not carry the "
            f"{DST_PREFIX!r} prefix this run pins, so the scope cannot be trusted"
        )
    return (top / target[len(DST_PREFIX) :]).resolve()


def scoped(spec: str, paths: list[Path]) -> dict[Path, frozenset[int]]:
    """The lines the change adds, for each walked path the diff reaches.

    No pathspec is passed: the walk has already chosen the files, and one
    argument per walked file is both redundant and, past a few thousand files, an
    argument list the kernel refuses. Intersecting the whole diff with the walk
    is a dict lookup per file and has no such limit.
    """
    top = Path(git(["rev-parse", "--show-toplevel"], Path.cwd()).strip()).resolve()
    outside = [path for path in paths if not path.is_relative_to(top)]
    if outside:
        raise Unavailable(
            f"{outside[0]} lies outside the repository at {top}, so no diff can say "
            f"which of its lines this change wrote ({len(outside)} path(s) in all)"
        )
    diff = git(["-c", "color.ui=false", "diff", spec, *PINNED], top)
    return {path: frozenset(lines) for path, lines in added_lines(diff, top).items()}


def split_argv(argv: list[str]) -> tuple[list[str], str | None]:
    """The paths, and the change the run is scoped to when one was named."""
    if CHANGED_FLAG not in argv:
        return argv, None
    at = argv.index(CHANGED_FLAG)
    if at + 1 == len(argv):
        raise Unavailable(f"{CHANGED_FLAG} needs a revision or range to pass to the diff")
    spec = argv[at + 1]
    if spec.startswith("-") and spec not in SPEC_OPTIONS:
        raise Unavailable(
            f"{spec!r} is not a revision or range, and the only options {CHANGED_FLAG} "
            f"takes are {' and '.join(SPEC_OPTIONS)}. An option that suppresses the "
            "patch would scope the condition to nothing and still exit 0"
        )
    return argv[:at] + argv[at + 2 :], spec


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


def report(findings: list[Finding], checked: int, unparsed: int) -> int:
    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if findings:
        print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
        for finding in sorted(findings, key=lambda f: (f.where, f.rule, f.condition)):
            print(finding)
        return 1
    print(f"{checked} file(s), no failures{suffix}.")
    return 0


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
