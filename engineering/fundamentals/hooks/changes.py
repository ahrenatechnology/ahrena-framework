"""The change a run is scoped to, shared by this plugin's change-scoped hooks.

Three detectors decide a condition whose subject is a change rather than a file:
check-structure.py for rules/debt-markers.md, check-comments.py for
rules/comment-pointers.md, and check-backstage-language.py for
rules/backstage-language.md. A path names a file and nothing in it says which
lines this change wrote, so the change is a second, explicit input:
`--changed <spec>` hands the spec to a pinned git diff and each detector decides
its condition over the lines that diff adds. Each of the three carried its own
copy of this machinery until the third made it one decision written three times
(rules/duplication.md condition 1), so it lives here, beside them in the same
plugin, the way contributing/hooks/forge.py serves the forge-tier hooks.

Every guard below exists because its absence is a silent pass, the failure
rules/debt-markers.md names as worse than a noisy one:

    - The spec is refused when it is an option other than --cached or --staged.
      It lands on the same command line as the diff's own options and git lets
      the last flag win, so `--name-only`, `--quiet` and `--output=` would empty
      the scope while the run still exited 0, and `-U5` would widen it past the
      lines the change wrote.
    - The diff is pinned: no colour (color.diff), no replacement driver
      (diff.external, GIT_EXTERNAL_DIFF), no content filter (diff.*.textconv),
      and an explicit `b/` prefix, because diff.noprefix drops it and
      diff.mnemonicPrefix rewrites it, and a hook that chopped two characters
      unconditionally would read `abc.py` as `c.py`. The pinned options follow
      the caller's spec so that a spec cannot override them.
    - Under --unified=0 the `+` side of a hunk header is exactly the lines the
      change adds or rewrites, and the two counts are exactly how many body rows
      follow, so the parser consumes a hunk rather than scanning for the next.
    - An unresolved merge renders as a combined diff or a bare `* Unmerged path`
      line, with no two-sided change to scope, and is reported as such.
    - A path git C-quotes, as it does for a double quote, a backslash, a control
      character or a byte above ASCII, is unquoted, or the hook would be blind to
      those names.
    - No pathspec is passed: the walk has already chosen the files, and past a
      few thousand of them one argument per file is a list the kernel refuses.

Standard library only. This is a module the detectors beside it import, not a
detector, and it decides no condition of its own.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

CHANGED_FLAG = "--changed"

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


def added_paths(spec: str) -> frozenset[Path]:
    """The files the change adds or renames into place, as absolute paths.

    A file the change only edits keeps the path it already had, so a condition
    about a name the change writes reaches the added and renamed sides alone.
    The listing is NUL-separated, so no path needs unquoting.
    """
    top = Path(git(["rev-parse", "--show-toplevel"], Path.cwd()).strip()).resolve()
    listing = git(
        ["-c", "color.ui=false", "diff", spec, "--no-ext-diff", "--name-only", "-z", "-M", "--diff-filter=AR"],
        top,
    )
    return frozenset((top / rel).resolve() for rel in listing.split("\0") if rel)


def report(findings: list, checked: int, unparsed: int) -> int:
    """Print the findings sorted by place, rule and condition; the exit code."""
    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if findings:
        print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
        for finding in sorted(findings, key=lambda f: (f.where, f.rule, f.condition)):
            print(finding)
        return 1
    print(f"{checked} file(s), no failures{suffix}.")
    return 0
