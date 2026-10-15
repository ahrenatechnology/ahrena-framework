#!/usr/bin/env python3
"""Ensure-or-report the agency entry directive, idempotently.

This writes the one entry directive that makes build work enter through the
`athena` agent into the platform's always-loaded instruction file — `CLAUDE.md`
for Claude Code, `AGENTS.md` for Codex — between clear markers, replacing only
what sits between them and never touching the surrounding content. A `--check`
mode reports whether the directive is present and current and writes nothing.

It mirrors the code-graph doctor's discipline: standard library only, so a
consumer runs it with nothing installed; ensure-or-report, never clobber; and a
report is a valid outcome. It is NOT run by the gate — it changes a consumer's
own instruction file, which no corpus check should do.

Usage:
    python3 install.py [--check] [--platform claude|codex] [root]

With no flags it writes or refreshes the directive. `--check` reports instead,
exiting 0 when the directive is present and current and 1 when it is absent or
stale, so a setup step can gate on it. `root` defaults to the current directory,
which is the consuming repository's root. `--platform` overrides the file
auto-detected from which instruction file is present.
"""

from __future__ import annotations

import sys
from pathlib import Path

START = "<!-- ahrena:agency:start -->"
END = "<!-- ahrena:agency:end -->"

# The platform's always-loaded instruction file. The directive is written into
# whichever one this repository uses.
TARGET = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}

# The directive itself: one line plus the route, the whole always-loaded cost of
# the binding. Kept between the markers so a re-write replaces only this.
DIRECTIVE = """## Build work enters through the agency

Build work enters through the `athena` agent. She plans the issue, routes the
concern, and delegates each layer to `iris` (frontend), `apollo` (backend) or
`clio` (data), running the develop→Argos loop (at most three rounds) before each
stacked pull request. Do not implement build work directly — delegate to the
agency. Athena orchestrates; she does not write production code, pass a review
verdict, or apply a fix."""

# Codex caps its subagents; the depth cap is the one to design around. Surfaced,
# not set — changing Codex's config is the owner's act, not this script's.
CODEX_NOTE = (
    "codex: the binding flattens to stay within agents.max_depth=1 — Athena spawns the\n"
    "       build agents directly and they do not sub-spawn. For a deeper tree, set\n"
    "       agents.max_depth = 2 in Codex's config (max_threads defaults to 6)."
)


def block() -> str:
    """The full marker-delimited block, as it is written and compared."""
    return f"{START}\n{DIRECTIVE}\n{END}"


def detect_platform(root: Path, given: str | None) -> tuple[str | None, str | None]:
    """The platform to target, as (platform, error). Exactly one is non-None."""
    if given is not None:
        if given not in TARGET:
            return None, f"--platform is 'claude' or 'codex', not '{given}'"
        return given, None
    present = [name for name, filename in TARGET.items() if (root / filename).is_file()]
    if len(present) == 1:
        return present[0], None
    if len(present) > 1:
        return None, "both CLAUDE.md and AGENTS.md are present; pass --platform to choose"
    # Neither present: default to Claude Code and create its file. Named in the
    # report so the choice is visible rather than silent.
    return "claude", None


def current_block(text: str) -> str | None:
    """The exact text between the markers, or None when they are not both present."""
    start = text.find(START)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start : end + len(END)]


def splice(text: str) -> str:
    """`text` with the marker region replaced by the current block, or appended.

    Everything outside the markers is preserved exactly; nothing else moves.
    """
    start = text.find(START)
    end = text.find(END)
    if start != -1 and end != -1 and end >= start:
        return text[:start] + block() + text[end + len(END) :]
    if not text.strip():
        return block() + "\n"
    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block() + "\n"


def cmd_check(path: Path, platform: str) -> int:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    found = current_block(text)
    if found is None:
        print(f"{platform}: directive ABSENT from {path.name}; run install.py to write it")
        status = 1
    elif found == block():
        print(f"{platform}: directive present and current in {path.name}")
        status = 0
    else:
        print(f"{platform}: directive STALE in {path.name}; run install.py to refresh it")
        status = 1
    if platform == "codex":
        print(CODEX_NOTE)
    return status


def cmd_write(path: Path, platform: str) -> int:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    updated = splice(text)
    if updated == text:
        print(f"{platform}: directive already current in {path.name}; nothing written")
    else:
        path.write_text(updated, encoding="utf-8")
        verb = "refreshed" if current_block(text) is not None else "wrote"
        print(f"{platform}: {verb} the directive in {path.name}")
    if platform == "codex":
        print(CODEX_NOTE)
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    check = "--check" in args
    args = [a for a in args if a != "--check"]

    given = None
    if "--platform" in args:
        i = args.index("--platform")
        if i + 1 >= len(args):
            print("usage: install.py [--check] [--platform claude|codex] [root]", file=sys.stderr)
            return 2
        given = args[i + 1]
        del args[i : i + 2]

    root = Path(args[0]).resolve() if args else Path.cwd()
    if not root.is_dir():
        print(f"{root}: not a directory", file=sys.stderr)
        return 2

    platform, error = detect_platform(root, given)
    if error is not None:
        print(error, file=sys.stderr)
        return 2

    path = root / TARGET[platform]
    return cmd_check(path, platform) if check else cmd_write(path, platform)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
