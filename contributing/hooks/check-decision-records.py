#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/decision-records.md.

Decides all seven conditions the rule states:

    1. the filename is ADR- plus three digits, a hyphen and a kebab-case slug
    2. the numbers are unique and run from 001 with no gaps
    3. the heading is `# ADR-nnn:` plus a title, and nnn matches the filename
    4. the status is accepted, superseded or withdrawn
    5. the date parses as an ISO-8601 calendar date
    6. supersession resolves in both directions, and the graph is acyclic
    7. the four sections are present and alternatives carries a list item

Condition 6 is the one the hook exists for. Superseding a decision is two edits
in two files, made at one moment by somebody thinking about the new record; the
half that is forgotten is invisible from the file being written. Conditions 1
to 5 and 7 are shape, and the alternatives clause of 7 is presence rather than
substance: a bullet reading "do nothing" satisfies it, and whether the option
was real is a reviewer's question.

Condition 6 is decided over the whole graph and not one edge at a time. A
record superseding itself, two records superseding each other and a ring of
three all satisfy every single-edge check and leave a log in which no decision
is current — which is precisely the "reads as current and is not" state the
hook exists to prevent, so the walk is part of the condition rather than an
extra.

The hook judges a directory of records, including every directory under it: a
record moved into `archive/` is still a record, and letting one hide there
would make `git mv` a way to erase a gap or a half-written supersession from
the gate without deleting anything. It says nothing about whether a decision
should have had one, which is the judgment the rule's doc companion is written
to inform and which nothing can decide.

Standard library only. The hook ships inside the plugin, so a consumer runs the
same check CI runs without installing anything.

Usage:
    python3 contributing/hooks/check-decision-records.py [directory]

With no argument the default path is read, and a repository that has no
decision log passes. A path given on the command line and not found fails: a
missing `docs/adr/` is a project with no records, and a missing anything-else
is a typo or a CI step wired to the wrong directory.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RULE = "decision-records"

# Where the ADR ecosystem's tooling looks, and where the predecessor framework
# put them. The directory is an argument, so a project that keeps records
# elsewhere passes the path and loses nothing.
DEFAULT_DIR = "docs/adr"

# The two files that live in a decision directory without being records.
# `adr-tools` — the tooling the `ADR-` prefix is kept for — writes README.md
# there as the log's index, and .gitkeep is the only way to commit the
# directory before the first record exists. Failing either would make an empty
# log uncommittable and the ecosystem's own tool a gate failure.
NOT_RECORDS = frozenset({"README.md", ".gitkeep"})

# Three digits rather than a variable width, so the directory sorts in numeric
# order in every tool that lists it. The slug is the same character class the
# framework uses for artifact names, minus the rule against a type prefix,
# which does not apply outside a plugin.
FILENAME = re.compile(r"^ADR-(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# The record's own copy of its number, which is what a copied record forgets.
# Whatever stands where the number belongs is taken as written, so that ADR-7
# and ADR-0007 reach a message about their width instead of reading as a record
# with no heading at all.
HEADING = re.compile(r"^#[ \t]+ADR-(?P<number>[^:]*):[ \t]*(?P<title>.*?)[ \t]*$")
THREE_DIGITS = re.compile(r"^\d{3}$")

# A header line, as `- **Name:** value`. Matched loosely on the name so that an
# unknown field is ignored rather than mistaken for a missing known one, and on
# any of Markdown's three bullet markers, as the alternatives clause is.
HEADER_FIELD = re.compile(
    r"^[-*+][ \t]+\*\*(?P<name>[A-Za-z][A-Za-z ]*):\*\*[ \t]*(?P<value>.*?)[ \t]*$"
)

SECTION = re.compile(r"^##[ \t]+(.*?)[ \t]*$")
# A `#` heading closes the section above it; a `###` one does not, because a
# subsection is part of the section it sits in.
TOP_HEADING = re.compile(r"^#[ \t]+")
FENCE = re.compile(r"^\s*(```|~~~)")
# Markdown has two kinds of list item and the rule asks for a list item, so an
# ordered one satisfies the alternatives clause exactly as a bullet does.
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+\S")
NUMBER_REF = re.compile(r"^ADR-(\d{3})$")
ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STATUSES = ("accepted", "superseded", "withdrawn")
REQUIRED_SECTIONS = ("context", "decision", "consequences", "alternatives considered")
ALTERNATIVES = "alternatives considered"

# A log whose first record is numbered 999 has one mistake, not 998 deletions.
# Past this many missing numbers the gap finding is stated once.
GAPS_LISTED_MAX = 10


@dataclass
class Finding:
    where: str  # path, with :line where a line exists
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


@dataclass
class Record:
    rel: str
    number: int
    readable: bool = True
    heading: str | None = None
    heading_line: int = 0
    title: str = ""
    first_line: int = 0
    fields: dict = field(default_factory=dict)
    sections: list = field(default_factory=list)
    alternatives: int = 0
    open_fence: int = 0


def visible_lines(text: str) -> tuple[list[tuple[int, str]], int]:
    """Every line outside a fenced block, numbered from 1, and an unclosed fence.

    A record quoting a heading or a header line in an example is not making
    one, so the fences are skipped before anything is matched. A fence that is
    never closed is a different thing: hiding the rest of the file behind it
    reports three sections missing that are plainly present, so when one is
    left open nothing is hidden and the fence itself is the finding.
    """
    shown: list[tuple[int, str]] = []
    hidden: list[tuple[int, str]] = []
    opened = 0
    for offset, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            opened = 0 if opened else offset
            continue
        (hidden if opened else shown).append((offset, line))
    if opened:
        return sorted(shown + hidden), opened
    return shown, 0


def read_header(record: Record, lines: list[tuple[int, str]]) -> None:
    """The heading and the `- **Name:** value` lines above the first section."""
    for number, line in lines:
        if SECTION.match(line):
            return
        if line.strip() and not record.first_line:
            record.first_line = number
        _read_heading(record, number, line)
        header = HEADER_FIELD.match(line)
        if header is not None:
            name = header.group("name").strip().lower()
            record.fields.setdefault(name, []).append((number, header.group("value")))


def _read_heading(record: Record, number: int, line: str) -> None:
    """The first `# ADR-...:` line. The first, so a second cannot overwrite it."""
    match = HEADING.match(line)
    if match is None or record.heading is not None:
        return
    record.heading = match.group("number").strip()
    record.title = match.group("title").strip()
    record.heading_line = number


def read_sections(record: Record, lines: list[tuple[int, str]]) -> None:
    """The section titles, and how many list items sit under the alternatives one."""
    current = ""
    for _, line in lines:
        match = SECTION.match(line)
        if match is not None:
            current = match.group(1).strip().lower()
            record.sections.append(current)
        elif TOP_HEADING.match(line):
            current = ""
        elif current == ALTERNATIVES and LIST_ITEM.match(line):
            record.alternatives += 1


def parse(path: Path, rel: str, number: int) -> Record:
    record = Record(rel=rel, number=number)
    lines, record.open_fence = visible_lines(path.read_text(encoding="utf-8-sig"))
    read_header(record, lines)
    read_sections(record, lines)
    return record


def _parsed(path: Path, rel: str, number: int, findings: list[Finding]) -> Record:
    """The parsed record, or a stand-in that holds the number and nothing else.

    A file that cannot be read is one finding about that file. Letting the
    decoding error out of here would replace every other record's findings with
    a stack trace.
    """
    try:
        return parse(path, rel, number)
    except (UnicodeDecodeError, OSError):
        findings.append(
            Finding(rel, 1, "the file does not read as UTF-8 text; a record is UTF-8 Markdown")
        )
        return Record(rel=rel, number=number, readable=False)


def collect(directory: Path, findings: list[Finding]) -> list[Record]:
    """Condition 1, and the parse everything else reads.

    Every file under the directory, at any depth. A record in a subdirectory is
    still a record, so moving one out of sight does not take its number, its
    supersession or its gap with it.
    """
    records: list[Record] = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        if path.name in NOT_RECORDS:
            continue
        rel = path.relative_to(directory).as_posix()
        match = FILENAME.match(path.name)
        if match is None:
            findings.append(
                Finding(
                    rel,
                    1,
                    "a record is named ADR- plus three digits, a hyphen and a "
                    "kebab-case slug, as in ADR-007-plans-live-in-the-issue.md",
                )
            )
            continue
        records.append(_parsed(path, rel, int(match.group(1)), findings))
    return records


def check_numbering(records: list[Record], directory: Path, findings: list[Finding]) -> None:
    """Condition 2. A duplicate is concurrent authorship; a gap is a deletion."""
    seen: dict[int, str] = {}
    for record in records:
        if record.number == 0:
            findings.append(
                Finding(record.rel, 2, "ADR-000 is not a number in this log; numbering runs from 001")
            )
            continue
        first = seen.get(record.number)
        if first is not None:
            findings.append(
                Finding(record.rel, 2, f"number {record.number:03d} is already taken by {first}")
            )
            continue
        seen[record.number] = record.rel
    _check_gaps(seen, directory, findings)


def _check_gaps(seen: dict, directory: Path, findings: list[Finding]) -> None:
    """Every number below the highest that no file carries, in the directory read."""
    missing = [n for n in range(1, max(seen, default=0) + 1) if n not in seen]
    if not missing:
        return
    where = str(directory)
    if len(missing) > GAPS_LISTED_MAX:
        findings.append(
            Finding(
                where,
                2,
                f"ADR-{missing[0]:03d} to ADR-{missing[-1]:03d} are missing ({len(missing)} "
                "numbers); numbering runs from 001 with no gaps, and a log this far from 001 "
                "is one record numbered wrong rather than a log that lost the rest",
            )
        )
        return
    for expected in missing:
        findings.append(
            Finding(
                where,
                2,
                f"ADR-{expected:03d} is missing; numbering runs from 001 with no "
                "gaps, and a deleted record is superseded or withdrawn instead",
            )
        )


def check_heading(record: Record, findings: list[Finding]) -> None:
    """Condition 3."""
    if record.heading is None:
        findings.append(
            Finding(record.rel, 3, "no heading of the form `# ADR-nnn: title` before the first section")
        )
        return
    where = f"{record.rel}:{record.heading_line}"
    if record.heading_line != record.first_line:
        findings.append(
            Finding(where, 3, "the heading is the first line of a record and something precedes it")
        )
    if not record.title:
        findings.append(Finding(where, 3, "the heading carries no title after the colon"))
    _check_heading_number(record, where, findings)


def _check_heading_number(record: Record, where: str, findings: list[Finding]) -> None:
    """The number inside the record against the number on disk."""
    if THREE_DIGITS.match(record.heading or "") is None:
        findings.append(
            Finding(
                where,
                3,
                f"the heading says ADR-{record.heading} and a record's number is three "
                "digits, as in ADR-007",
            )
        )
        return
    if int(record.heading) != record.number:
        findings.append(
            Finding(
                where,
                3,
                f"the heading says ADR-{record.heading} and the filename says "
                f"ADR-{record.number:03d}; a copied record is where this comes from",
            )
        )


def _held(record: Record, name: str) -> list:
    """Every occurrence of a header field, in the order they were written."""
    return record.fields.get(name, [])


def _repeated(record: Record, name: str, condition: int, findings: list[Finding]) -> bool:
    """True, with the reason reported, when a single-valued field is written twice.

    Keeping the last quietly is the one wrong answer: `Status: banana` followed
    by `Status: accepted` would pass, and the reader would never learn which
    line the gate read.
    """
    held = _held(record, name)
    if len(held) < 2:
        return False
    findings.append(
        Finding(
            f"{record.rel}:{held[1][0]}",
            condition,
            f"`{name[:1].upper()}{name[1:]}` is given {len(held)} times and a record carries "
            "one. Which line counts cannot be guessed, so neither is read",
        )
    )
    return True


def check_status(record: Record, findings: list[Finding]) -> None:
    """Condition 4. The field name and the value are read without regard to case."""
    held = _held(record, "status")
    if not held:
        findings.append(Finding(record.rel, 4, "no `- **Status:**` line"))
        return
    if _repeated(record, "status", 4, findings):
        return
    number, value = held[0]
    if value.strip().lower() in STATUSES:
        return
    findings.append(
        Finding(
            f"{record.rel}:{number}",
            4,
            f"'{value}' is not a status; the enum is {', '.join(STATUSES)}",
        )
    )


def check_date(record: Record, findings: list[Finding]) -> None:
    """Condition 5. A format check: a record dated 1970 passes."""
    held = _held(record, "date")
    if not held:
        findings.append(Finding(record.rel, 5, "no `- **Date:**` line"))
        return
    if _repeated(record, "date", 5, findings):
        return
    number, value = held[0]
    if ISO_DAY.match(value) is not None and _is_a_day(value):
        return
    findings.append(
        Finding(f"{record.rel}:{number}", 5, f"'{value}' is not an ISO-8601 date, as in 2026-09-19")
    )


def _is_a_day(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def check_sections(record: Record, findings: list[Finding]) -> None:
    """Condition 7."""
    if record.open_fence:
        findings.append(
            Finding(
                f"{record.rel}:{record.open_fence}",
                7,
                "a fenced block is opened here and never closed. Nothing below it has been "
                "hidden from the gate, but every tool that renders the record will hide it",
            )
        )
    for wanted in REQUIRED_SECTIONS:
        if wanted not in record.sections:
            findings.append(Finding(record.rel, 7, f"no `## {wanted.capitalize()}` section"))
    if ALTERNATIVES in record.sections and record.alternatives == 0:
        findings.append(
            Finding(
                record.rel,
                7,
                "the alternatives section carries no list item. The gate checks that "
                "a bullet is there, not that the option was real",
            )
        )


def _targets(record: Record, name: str) -> list:
    """Each record a pointer field names, as (line, text).

    A pointer field may be written more than once, and one line may carry
    several names separated by commas. Both spellings mean the same thing and
    both are needed: condition 2 forbids deleting a record, so merging two
    decisions into one goes through supersession, and the merged record names
    both of the records it replaces.
    """
    out: list[tuple[int, str]] = []
    for number, value in _held(record, name):
        out.extend((number, piece.strip()) for piece in value.split(",") if piece.strip())
    return out


def _numbers_named(record: Record, name: str) -> set:
    """Every record number a pointer field resolves to, ignoring what does not parse."""
    found = {_number_of(text) for _, text in _targets(record, name)}
    found.discard(None)
    return found


def _number_of(text: str) -> int | None:
    """The number a pointer names, or None when it does not name one."""
    match = NUMBER_REF.match(text)
    return int(match.group(1)) if match is not None else None


def _status_of(record: Record) -> str:
    held = _held(record, "status")
    return held[0][1].strip().lower() if held else ""


def _resolve(record: Record, pointer: tuple, by_number: dict, findings: list[Finding]) -> Record | None:
    """The record a pointer names, or None with the reason already reported."""
    line, named = pointer
    where = f"{record.rel}:{line}"
    target = _number_of(named)
    if target is None:
        findings.append(Finding(where, 6, f"'{named}' does not name a record; write it as ADR-nnn"))
        return None
    if target == record.number:
        findings.append(
            Finding(
                where,
                6,
                "a record supersedes the record it replaces, and this one names itself. "
                "A record that replaces itself is never the current decision",
            )
        )
        return None
    other = by_number.get(target)
    if other is None:
        findings.append(Finding(where, 6, f"{named} does not exist in this directory"))
    return other


def check_forward(record: Record, by_number: dict, findings: list[Finding]) -> None:
    """Condition 6, from the superseded record towards its successor."""
    superseded = _status_of(record) == "superseded"
    if _repeated(record, "superseded by", 6, findings):
        return
    pointers = _targets(record, "superseded by")
    if not pointers:
        if superseded:
            findings.append(
                Finding(record.rel, 6, "the status is superseded and there is no `- **Superseded by:**` line")
            )
        return
    if not superseded:
        findings.append(
            Finding(record.rel, 6, f"`Superseded by` names {pointers[0][1]} and the status is not superseded")
        )
    if len(pointers) > 1:
        findings.append(
            Finding(
                record.rel,
                6,
                "`Superseded by` names more than one record. A record is replaced by one "
                "successor; two records merging into one is written on the successor instead",
            )
        )
        return
    successor = _resolve(record, pointers[0], by_number, findings)
    if successor is not None and record.number not in _numbers_named(successor, "supersedes"):
        findings.append(
            Finding(
                record.rel,
                6,
                f"{successor.rel} does not name this record back. A supersession is "
                "two edits in two files and this is the one that gets forgotten",
            )
        )


def check_backward(record: Record, by_number: dict, findings: list[Finding]) -> None:
    """Condition 6, from the successor towards each record it replaces."""
    for pointer in _targets(record, "supersedes"):
        _check_older(record, pointer, by_number, findings)


def _check_older(record: Record, pointer: tuple, by_number: dict, findings: list[Finding]) -> None:
    """One `Supersedes` edge: the older record exists, is retired and points back."""
    older = _resolve(record, pointer, by_number, findings)
    if older is None:
        return
    if _status_of(older) != "superseded":
        findings.append(Finding(record.rel, 6, f"{older.rel} is named as superseded and its own status is not"))
    if record.number not in _numbers_named(older, "superseded by"):
        findings.append(
            Finding(record.rel, 6, f"{older.rel} does not carry `Superseded by: ADR-{record.number:03d}`")
        )


def _supersession_edges(records: list[Record], by_number: dict) -> dict:
    """Number to number, for every `Superseded by` line that resolves elsewhere.

    A self-reference is left out because `_resolve` has already reported it,
    and reporting it twice would spend two findings on one wrong line.
    """
    edges: dict[int, int] = {}
    for record in records:
        pointers = _targets(record, "superseded by")
        target = _number_of(pointers[0][1]) if len(pointers) == 1 else None
        if target is not None and target != record.number and target in by_number:
            edges.setdefault(record.number, target)
    return edges


def _ring_from(start: int, edges: dict) -> list:
    """The cycle the chain out of `start` falls into, or an empty list."""
    walked: list[int] = []
    node = start
    while node in edges and node not in walked:
        walked.append(node)
        node = edges[node]
    if node not in walked:
        return []
    return walked[walked.index(node) :]


def check_cycles(records: list[Record], by_number: dict, findings: list[Finding]) -> None:
    """Condition 6 over the graph, which no single edge can see.

    Two records superseding each other, or a ring of three, satisfy every
    per-edge check and report nothing. What they produce is a log in which
    every record reads as replaced and none is current, which is the failure
    the rule closes with "every other arrangement fails".
    """
    edges = _supersession_edges(records, by_number)
    reported: set = set()
    for start in sorted(edges):
        ring = _ring_from(start, edges)
        if not ring or reported.intersection(ring):
            continue
        reported.update(ring)
        findings.append(Finding(by_number[ring[0]].rel, 6, _ring_message(ring)))


def _ring_message(ring: list) -> str:
    chain = " -> ".join(f"ADR-{number:03d}" for number in ring + [ring[0]])
    return (
        f"supersession runs in a circle: {chain}. Every record in it reads as replaced, so "
        "the log holds no current decision at all"
    )


def judge(record: Record, findings: list[Finding]) -> None:
    """Conditions 3, 4, 5 and 7, all of which one record decides alone."""
    check_heading(record, findings)
    check_status(record, findings)
    check_date(record, findings)
    check_sections(record, findings)


def _absent(directory: Path, given: str | None) -> int:
    """A directory that is not there. Silence for the default path, a failure for one given."""
    if given is None:
        print(f"{directory}: no decision log here, nothing to decide.")
        return 0
    print(
        f"{directory}: not a directory. A missing decision log is nothing to decide only at "
        f"the default path, {DEFAULT_DIR}; a path given on the command line and not found is a "
        "typo or a step wired to the wrong directory, and passing would hide it forever."
    )
    return 1


def main(argv: list[str]) -> int:
    given = argv[1] if len(argv) > 1 else None
    directory = Path(given if given is not None else DEFAULT_DIR)
    if not directory.is_dir():
        return _absent(directory, given)

    findings: list[Finding] = []
    records = collect(directory, findings)
    check_numbering(records, directory, findings)
    readable = [record for record in records if record.readable]
    # The first file to carry a number is the one every pointer resolves to,
    # which is the same one condition 2 names as the holder. Keeping the last
    # here and the first there made a duplicate number produce two false
    # findings against whichever file was innocent.
    by_number: dict[int, Record] = {}
    for record in readable:
        by_number.setdefault(record.number, record)
    for record in readable:
        judge(record, findings)
        check_forward(record, by_number, findings)
        check_backward(record, by_number, findings)
    check_cycles(readable, by_number, findings)

    for finding in findings:
        print(finding)
    print(f"{len(records)} decision record(s), {len(findings)} failure(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
