#!/usr/bin/env python3
"""Detector for the conditions in contributing/rules/decision-records.md.

Decides all seven conditions the rule states:

    1. the filename is ADR- plus three digits, a hyphen and a kebab-case slug
    2. the numbers are unique and run from 001 with no gaps
    3. the heading is `# ADR-nnn:` plus a title, and nnn matches the filename
    4. the status is accepted, superseded or withdrawn
    5. the date parses as an ISO-8601 calendar date
    6. supersession resolves in both directions
    7. the four sections are present and alternatives carries a list item

Condition 6 is the one the hook exists for. Superseding a decision is two edits
in two files, made at one moment by somebody thinking about the new record; the
half that is forgotten is invisible from the file being written. Conditions 1
to 5 and 7 are shape, and the alternatives clause of 7 is presence rather than
substance: a bullet reading "do nothing" satisfies it, and whether the option
was real is a reviewer's question.

The hook judges a directory of records. It says nothing about whether a
decision should have had one, which is the judgment the rule's doc companion is
written to inform and which nothing can decide.

Standard library only. The hook ships inside the plugin, so a consumer runs the
same check CI runs without installing anything.

Usage:
    python3 contributing/hooks/check-decision-records.py [directory]
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

# Three digits rather than a variable width, so the directory sorts in numeric
# order in every tool that lists it. The slug is the same character class the
# framework uses for artifact names, minus the rule against a type prefix,
# which does not apply outside a plugin.
FILENAME = re.compile(r"^ADR-(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# The record's own copy of its number, which is what a copied record forgets.
HEADING = re.compile(r"^#[ \t]+ADR-(\d{3}):[ \t]*(\S.*)$")

# A header line, as `- **Name:** value`. Matched loosely on the name so that an
# unknown field is ignored rather than mistaken for a missing known one.
HEADER_FIELD = re.compile(r"^-[ \t]+\*\*(?P<name>[A-Za-z][A-Za-z ]*):\*\*[ \t]*(?P<value>.*?)[ \t]*$")

SECTION = re.compile(r"^##[ \t]+(.*?)[ \t]*$")
FENCE = re.compile(r"^\s*(```|~~~)")
BULLET = re.compile(r"^[ \t]*[-*+][ \t]+\S")
NUMBER_REF = re.compile(r"^ADR-(\d{3})$")
ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STATUSES = ("accepted", "superseded", "withdrawn")
REQUIRED_SECTIONS = ("context", "decision", "consequences", "alternatives considered")
ALTERNATIVES = "alternatives considered"


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
    heading: str | None = None
    heading_line: int = 0
    fields: dict = field(default_factory=dict)
    sections: list = field(default_factory=list)
    alternatives: int = 0


def visible_lines(text: str) -> list[tuple[int, str]]:
    """Every line outside a fenced block, numbered from 1.

    A record quoting a heading or a header line in an example is not making
    one, so the fences are skipped before anything is matched.
    """
    out: list[tuple[int, str]] = []
    inside = False
    for offset, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            out.append((offset, line))
    return out


def read_header(record: Record, lines: list[tuple[int, str]]) -> None:
    """The heading and the `- **Name:** value` lines above the first section."""
    for number, line in lines:
        if SECTION.match(line):
            return
        match = HEADING.match(line)
        if match is not None:
            record.heading, record.heading_line = match.group(1), number
        header = HEADER_FIELD.match(line)
        if header is not None:
            record.fields[header.group("name").strip().lower()] = (number, header.group("value"))


def read_sections(record: Record, lines: list[tuple[int, str]]) -> None:
    """The section titles, and how many bullets sit under the alternatives one."""
    current = ""
    for _, line in lines:
        match = SECTION.match(line)
        if match is not None:
            current = match.group(1).strip().lower()
            record.sections.append(current)
        elif current == ALTERNATIVES and BULLET.match(line):
            record.alternatives += 1


def parse(path: Path, number: int) -> Record:
    record = Record(rel=path.name, number=number)
    lines = visible_lines(path.read_text(encoding="utf-8"))
    read_header(record, lines)
    read_sections(record, lines)
    return record


def collect(directory: Path, findings: list[Finding]) -> list[Record]:
    """Condition 1, and the parse everything else reads."""
    records: list[Record] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        match = FILENAME.match(path.name)
        if match is None:
            findings.append(
                Finding(
                    path.name,
                    1,
                    "a record is named ADR- plus three digits, a hyphen and a "
                    "kebab-case slug, as in ADR-007-plans-live-in-the-issue.md",
                )
            )
            continue
        records.append(parse(path, int(match.group(1))))
    return records


def check_numbering(records: list[Record], findings: list[Finding]) -> None:
    """Condition 2. A duplicate is concurrent authorship; a gap is a deletion."""
    seen: dict[int, str] = {}
    for record in records:
        first = seen.get(record.number)
        if first is not None:
            findings.append(
                Finding(record.rel, 2, f"number {record.number:03d} is already taken by {first}")
            )
            continue
        seen[record.number] = record.rel
    for expected in range(1, max(seen, default=0) + 1):
        if expected not in seen:
            findings.append(
                Finding(
                    f"{DEFAULT_DIR}",
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
    if int(record.heading) != record.number:
        findings.append(
            Finding(
                f"{record.rel}:{record.heading_line}",
                3,
                f"the heading says ADR-{record.heading} and the filename says "
                f"ADR-{record.number:03d}; a copied record is where this comes from",
            )
        )


def check_status(record: Record, findings: list[Finding]) -> None:
    """Condition 4."""
    held = record.fields.get("status")
    if held is None:
        findings.append(Finding(record.rel, 4, "no `- **Status:**` line"))
        return
    number, value = held
    if value.strip().lower() not in STATUSES:
        findings.append(
            Finding(
                f"{record.rel}:{number}",
                4,
                f"'{value}' is not a status; the enum is {', '.join(STATUSES)}",
            )
        )


def check_date(record: Record, findings: list[Finding]) -> None:
    """Condition 5. A format check: a record dated 1970 passes."""
    held = record.fields.get("date")
    if held is None:
        findings.append(Finding(record.rel, 5, "no `- **Date:**` line"))
        return
    number, value = held
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
    for wanted in REQUIRED_SECTIONS:
        if wanted not in record.sections:
            findings.append(
                Finding(record.rel, 7, f"no `## {wanted.capitalize()}` section")
            )
    if ALTERNATIVES in record.sections and record.alternatives == 0:
        findings.append(
            Finding(
                record.rel,
                7,
                "the alternatives section carries no list item. The gate checks that "
                "a bullet is there, not that the option was real",
            )
        )


def _named(record: Record, name: str) -> str | None:
    """The raw value of a pointer line, or None when the line is absent."""
    held = record.fields.get(name)
    return held[1].strip() if held is not None else None


def _number_of(text: str) -> int | None:
    """The number a pointer names, or None when it does not name one."""
    match = NUMBER_REF.match(text)
    return int(match.group(1)) if match is not None else None


def _status_of(record: Record) -> str:
    held = record.fields.get("status")
    return held[1].strip().lower() if held is not None else ""


def _resolve(record: Record, named: str, by_number: dict, findings: list[Finding]) -> Record | None:
    """The record a pointer names, or None with the reason already reported."""
    target = _number_of(named)
    if target is None:
        findings.append(Finding(record.rel, 6, f"'{named}' does not name a record; write it as ADR-nnn"))
        return None
    other = by_number.get(target)
    if other is None:
        findings.append(Finding(record.rel, 6, f"{named} does not exist in this directory"))
    return other


def check_forward(record: Record, by_number: dict, findings: list[Finding]) -> None:
    """Condition 6, from the superseded record towards its successor."""
    named = _named(record, "superseded by")
    superseded = _status_of(record) == "superseded"
    if named is None:
        if superseded:
            findings.append(Finding(record.rel, 6, "the status is superseded and there is no `- **Superseded by:**` line"))
        return
    if not superseded:
        findings.append(Finding(record.rel, 6, f"`Superseded by` names {named} and the status is not superseded"))
    successor = _resolve(record, named, by_number, findings)
    if successor is None:
        return
    back = _named(successor, "supersedes")
    if back is None or _number_of(back) != record.number:
        findings.append(
            Finding(
                record.rel,
                6,
                f"{successor.rel} does not name this record back. A supersession is "
                "two edits in two files and this is the one that gets forgotten",
            )
        )


def check_backward(record: Record, by_number: dict, findings: list[Finding]) -> None:
    """Condition 6, from the successor towards the record it replaces."""
    named = _named(record, "supersedes")
    if named is None:
        return
    older = _resolve(record, named, by_number, findings)
    if older is None:
        return
    if _status_of(older) != "superseded":
        findings.append(Finding(record.rel, 6, f"{older.rel} is named as superseded and its own status is not"))
    back = _named(older, "superseded by")
    if back is None or _number_of(back) != record.number:
        findings.append(
            Finding(record.rel, 6, f"{older.rel} does not carry `Superseded by: ADR-{record.number:03d}`")
        )


def judge(record: Record, findings: list[Finding]) -> None:
    """Conditions 3, 4, 5 and 7, all of which one record decides alone."""
    check_heading(record, findings)
    check_status(record, findings)
    check_date(record, findings)
    check_sections(record, findings)


def main(argv: list[str]) -> int:
    directory = Path(argv[1] if len(argv) > 1 else DEFAULT_DIR)
    if not directory.is_dir():
        print(f"{directory}: no decision log here, nothing to decide.")
        return 0

    findings: list[Finding] = []
    records = collect(directory, findings)
    check_numbering(records, findings)
    by_number = {record.number: record for record in records}
    for record in records:
        judge(record, findings)
        check_forward(record, by_number, findings)
        check_backward(record, by_number, findings)

    for finding in findings:
        print(finding)
    print(f"{len(records)} decision record(s), {len(findings)} failure(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
