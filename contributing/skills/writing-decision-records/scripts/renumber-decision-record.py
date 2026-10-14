#!/usr/bin/env python3
"""Renumber one decision record to the next free number, mechanically.

A number collision between two concurrent branches is invisible to
`contributing/hooks/check-decision-records.py`, which reads one tree: each
branch sees only its own new record and passes, and the duplicate surfaces
only once both are in one tree, at rebase or at land. The forge-tier
`check-decision-records-numbers.py` catches it earlier, on the pull request,
and its finding names this script as the fix.

The fix is the same edit every time, which is why it is a script rather than a
procedure: the losing record moves to the next free number, its heading moves
with it, the index row moves with it, and every reference that resolves to its
file moves with it. That edit is mechanical, so Erodos can apply it — the
`applying-fixes` model, a finding whose correction is a concrete instruction.

What it does, given the path to the record that must move:

    1. reads the record's number and slug from its filename
    2. picks the next free number: one past the highest in the directory
    3. renames ADR-NNN-slug.md to ADR-MMM-slug.md
    4. rewrites the `# ADR-NNN:` heading inside the file to `# ADR-MMM:`
    5. rewrites the row in the directory's README.md that links the old file
    6. rewrites every reference across the tree that resolves to the old file

What it does not touch is a bare `ADR-NNN` with no slug. The number alone does
not say which record is meant: the record colliding here and the record it
collides with share it, and rewriting the wrong one is worse than leaving it.
Those mentions are listed at the end for a person to read, and there are none
when the record is new, which is the case this script exists for.

Standard library only, so it runs where the hook that names it runs: a
consumer's checkout, with nothing installed.

Usage:
    python3 renumber-decision-record.py <path-to-record> [--root <dir>]

`--root` is the tree whose references are rewritten; it defaults to the git
working tree the record sits in, and to the current directory when there is no
git tree. The record's own directory is where the next free number is read and
where the README.md index is.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# The same shape contributing/rules/decision-records.md condition 1 states and
# contributing/hooks/check-decision-records.py enforces: ADR-, three digits, a
# hyphen, a kebab-case slug.
FILENAME = re.compile(r"^ADR-(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")

# The record's own heading, `# ADR-nnn: title`, on its first line. Only the
# number is rewritten; the title is left exactly as it was.
HEADING = re.compile(r"^(#[ \t]+ADR-)\d+(:)", re.MULTILINE)

# Files that are not text are skipped rather than guessed at. The tree a
# decision log lives in is Markdown, Python, YAML and the like; a reference to
# a record does not live in a binary.
TEXT_SUFFIXES = frozenset(
    {".md", ".markdown", ".py", ".yml", ".yaml", ".txt", ".json", ".toml", ".cfg", ".ini", ".sh", ".rst"}
)

SKIP_DIRS = frozenset({".git", ".github/workflows/.cache"})


def numbers_in(directory: Path) -> list[int]:
    """Every decision-record number in the directory, one file at a time."""
    found: list[int] = []
    for path in directory.iterdir():
        match = FILENAME.match(path.name)
        if match is not None:
            found.append(int(match.group(1)))
    return found


def git_root(start: Path) -> Path | None:
    """The working tree `start` sits in, found by the `.git` that marks its top."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def text_files(root: Path):
    """Every text file under root, skipping .git and anything that is not text."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part == ".git" for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def rewrite_references(root: Path, old_stem: str, new_stem: str, old3: str, new3: str) -> tuple[int, list[str]]:
    """Move every reference that resolves to the old file, and list the bare ones.

    A reference that carries the slug — `ADR-015-the-slug` or that file's name —
    names this record and no other, so it is rewritten. A bare `ADR-015` names
    a number two records share right now, so it is left alone and reported.
    """
    stem = re.compile(re.escape(old_stem))
    # `[ADR-015](... the new file ...)`: the link's visible text is the bare
    # number and the stem rewrite above does not reach it, so the one place the
    # bare number is unambiguous — sitting on a link to this very file, under
    # any path — is fixed here and nowhere else.
    display = re.compile(r"\[ADR-" + old3 + r"\](\([^)]*" + re.escape(new_stem) + r")")
    bare = re.compile(r"ADR-" + old3 + r"(?![-\d])")
    changed = 0
    flagged: list[str] = []
    for path in text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        moved = display.sub(r"[ADR-" + new3 + r"]\1", stem.sub(new_stem, text))
        if moved != text:
            path.write_text(moved, encoding="utf-8")
            changed += 1
        for line_number, line in enumerate(moved.splitlines(), start=1):
            if bare.search(line):
                flagged.append(f"{path}:{line_number}: {line.strip()}")
    return changed, flagged


def renumber(record: Path, root: Path | None) -> int:
    match = FILENAME.match(record.name)
    if match is None:
        print(f"{record.name} is not a decision record: a record is ADR-nnn-slug.md")
        return 1
    old = int(match.group(1))
    slug = match.group(2)
    directory = record.parent

    highest = max(numbers_in(directory), default=0)
    new = highest + 1
    old3, new3 = f"{old:03d}", f"{new:03d}"
    old_stem, new_stem = f"ADR-{old3}-{slug}", f"ADR-{new3}-{slug}"
    moved = directory / f"{new_stem}.md"

    body = HEADING.sub(rf"\g<1>{new3}\g<2>", record.read_text(encoding="utf-8"), count=1)
    moved.write_text(body, encoding="utf-8")
    record.unlink()

    tree = root or git_root(directory) or Path.cwd()
    changed, flagged = rewrite_references(tree, old_stem, new_stem, old3, new3)

    print(f"renumbered {old_stem} to {new_stem}")
    print(f"  heading rewritten to ADR-{new3}")
    print(f"  references moved in {changed} file(s), including this directory's README.md where it has a row")
    if flagged:
        print(f"  {len(flagged)} bare ADR-{old3} mention(s) left for a person to read, as the number alone does not say which record:")
        for line in flagged:
            print(f"    {line}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Renumber one decision record to the next free number.")
    parser.add_argument("record", help="path to the ADR-nnn-slug.md record that must move")
    parser.add_argument("--root", default=None, help="tree whose references are rewritten; defaults to the git working tree")
    args = parser.parse_args(argv[1:])

    record = Path(args.record)
    if not record.is_file():
        print(f"{record}: not a file")
        return 1
    return renumber(record, Path(args.root) if args.root else None)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
