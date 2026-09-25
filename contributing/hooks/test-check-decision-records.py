#!/usr/bin/env python3
"""Tests for check-decision-records.py.

A gate that has never rejected anything is a claim, not a guardrail.

The hook runs as a subprocess on purpose: that is what CI runs, exit code
included. Every case names the directory it is pointed at, relative to the
fixture root, and `where=None` runs the hook from the fixture root with no
argument at all — which is how CI invokes it and the only invocation for which
a missing directory is allowed to pass.

Every case also states the number of failures the hook must report, and the
harness compares it against the count the hook prints. Asserting only that a
fragment appears lets a case pass on its own reason plus any number of others:
the case for a successor whose target still reads accepted produces two
findings and always did, and a duplicate number used to produce two false ones
beside the true one. Neither was visible until the count was checked.

Usage:
    python3 contributing/hooks/test-check-decision-records.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-decision-records.py"
TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "writing-decision-records"
    / "references"
    / "adr-template.md"
)

COUNTED = re.compile(r"(\d+) failure\(s\)")

FIRST = "docs/adr/ADR-001-records-live-at-the-repository-root.md"
SECOND = "docs/adr/ADR-002-the-log-keeps-its-index.md"
THIRD = "docs/adr/ADR-003-the-two-become-one.md"

# The smallest record that satisfies every condition. Each failing case below
# is this with exactly one thing broken, and the failure count is asserted, so
# a case can only fail for its reason.
GOOD = """# ADR-001: Records live at the repository root

- **Status:** accepted
- **Date:** 2026-09-19
- **Issue:** #65

## Context

The decision log had eleven rows and nowhere to put the reasoning behind any
of them.

## Decision

A decision that earns a record gets one under docs/adr, numbered and dated.

## Consequences

The log stays the index. The records carry what a row cannot, and the cost is
a second place to look.

## Alternatives considered

- **A wider table.** Rejected: a consequence cell of 111 words is not read.
"""

ALTERNATIVE = "- **A wider table.** Rejected: a consequence cell of 111 words is not read."

# The successor in a supersession pair. Numbered 002, and the pair is only
# valid when each half names the other.
SUCCESSOR = (
    GOOD.replace("# ADR-001:", "# ADR-002:")
    .replace("- **Issue:** #65", "- **Issue:** #65\n- **Supersedes:** ADR-001")
)

SUPERSEDED = (
    GOOD.replace("- **Status:** accepted", "- **Status:** superseded")
    .replace("- **Issue:** #65", "- **Issue:** #65\n- **Superseded by:** ADR-002")
)


def renumbered(text: str, number: int) -> str:
    """The same record carrying a different number in its heading."""
    return text.replace("# ADR-001:", f"# ADR-{number:03d}:")


def retired(text: str, number: int) -> str:
    """The same record, superseded by the record with that number."""
    return text.replace("- **Status:** accepted", "- **Status:** superseded").replace(
        "- **Issue:** #65", f"- **Issue:** #65\n- **Superseded by:** ADR-{number:03d}"
    )


def replacing(text: str, line: str) -> str:
    """The same record, carrying the given `Supersedes` line or lines."""
    return text.replace("- **Issue:** #65", f"- **Issue:** #65\n{line}")


def skeleton() -> str:
    """The record the skill's step 3 copies: the template between its first two rules.

    Extracted rather than restated, so that the case fails when the shipped
    skeleton stops being something a reader can fill in and pass with.
    """
    return TEMPLATE.read_text(encoding="utf-8").split("\n---\n")[1].strip() + "\n"


@dataclass
class Case:
    name: str
    files: dict
    expect: list = field(default_factory=list)
    # The count the hook must print. None where it prints none at all, and the
    # exit code is then stated separately because a directory that is absent
    # passes at the default path and fails at any other.
    failures: int | None = 0
    code: int = 0
    where: str | None = "docs/adr"


CASES = [
    Case("a valid record passes", {FIRST: GOOD}, ["1 decision record(s), 0 failure(s)"]),
    Case(
        "no decision log at all is nothing to decide",
        {},
        ["nothing to decide"],
        failures=None,
        where=None,
    ),
    Case(
        "the default path is what CI runs, and it judges what is there",
        {FIRST: GOOD},
        ["1 decision record(s), 0 failure(s)"],
        where=None,
    ),
    Case(
        "a resolved supersession pair passes",
        {FIRST: SUPERSEDED, SECOND: SUCCESSOR},
        ["2 decision record(s), 0 failure(s)"],
    ),
    Case(
        "condition 1 fails a filename that is not ADR-nnn-slug",
        {"docs/adr/adr-1-records.md": GOOD},
        ["condition 1", "kebab-case slug"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 1 fails a two-digit number",
        {"docs/adr/ADR-01-records-live-at-the-repository-root.md": GOOD},
        ["condition 1"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 1 fails a file that does not read as UTF-8, and nothing else does",
        {FIRST: GOOD.replace("111 words", "111 wörds").encode("latin-1")},
        ["condition 1", "does not read as UTF-8 text"],
        failures=1,
        code=1,
    ),
    Case(
        "README.md and .gitkeep are not records and do not fail condition 1",
        {"docs/adr/README.md": "# Decision log\n", "docs/adr/.gitkeep": ""},
        ["0 decision record(s), 0 failure(s)"],
    ),
    Case(
        "condition 2 fails a duplicate number",
        {FIRST: GOOD, "docs/adr/ADR-001-the-log-keeps-its-index.md": GOOD},
        ["condition 2", "already taken by"],
        failures=1,
        code=1,
    ),
    Case(
        # The numbering check kept the first file and the pointer lookup kept
        # the last, so condition 6 resolved against the stray copy and filed
        # two findings against the record that was correct.
        "a duplicate number does not misdirect condition 6 at the innocent file",
        {
            "docs/adr/ADR-001-a-record.md": SUPERSEDED,
            "docs/adr/ADR-001-b-record.md": GOOD,
            SECOND: SUCCESSOR,
        },
        ["condition 2", "already taken by"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 2 fails a gap left by a deletion",
        {FIRST: GOOD, "docs/adr/ADR-003-a-third-record.md": renumbered(GOOD, 3)},
        ["condition 2", "ADR-002 is missing"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 2 fails ADR-000, because numbering runs from 001",
        {"docs/adr/ADR-000-the-zeroth-record.md": renumbered(GOOD, 0)},
        ["condition 2", "ADR-000 is not a number in this log"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 2 states a log that starts at 999 once, not 998 times",
        {"docs/adr/ADR-999-the-first-record.md": renumbered(GOOD, 999)},
        ["condition 2", "ADR-001 to ADR-998 are missing (998 numbers)"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 2 names the directory it was given, not the default one",
        {"records/ADR-002-the-log-keeps-its-index.md": renumbered(GOOD, 2)},
        ["records\n    [decision-records] condition 2", "ADR-001 is missing"],
        failures=1,
        code=1,
        where="records",
    ),
    Case(
        "a directory other than the default is the one that is judged",
        {"records/ADR-001-records-live-at-the-repository-root.md": GOOD},
        ["1 decision record(s), 0 failure(s)"],
        where="records",
    ),
    Case(
        "a directory argument that is not there fails rather than passing empty",
        {FIRST: GOOD},
        ["not a directory"],
        failures=None,
        code=1,
        where="docs/adrs",
    ),
    Case(
        "a file given where a directory belongs fails",
        {FIRST: GOOD},
        ["not a directory"],
        failures=None,
        code=1,
        where=FIRST,
    ),
    Case(
        # Moving a record into archive/ used to take its number, its
        # supersession and its gap out of the gate's sight.
        "a record in a subdirectory is still a record",
        {FIRST: SUPERSEDED, "docs/adr/archive/ADR-002-the-log-keeps-its-index.md": renumbered(GOOD, 2)},
        ["2 decision record(s)", "condition 6", "does not name this record back"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 3 fails a heading that disagrees with the filename",
        {FIRST: renumbered(GOOD, 7)},
        ["condition 3", "the heading says ADR-007"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 3 fails a record with no heading",
        {FIRST: GOOD.replace("# ADR-001: Records live at the repository root\n", "")},
        ["condition 3", "no heading"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 3 fails a one-digit heading number on its width",
        {FIRST: GOOD.replace("# ADR-001:", "# ADR-7:")},
        ["condition 3", "the heading says ADR-7 and a record's number is three digits"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 3 fails a four-digit heading number on its width",
        {FIRST: GOOD.replace("# ADR-001:", "# ADR-0007:")},
        ["condition 3", "the heading says ADR-0007 and a record's number is three digits"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 3 fails a heading that is not the first line",
        {FIRST: "Draft, do not read.\n\n" + GOOD},
        ["condition 3", "the heading is the first line of a record"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 3 fails a heading with no title after the colon",
        {FIRST: GOOD.replace("# ADR-001: Records live at the repository root", "# ADR-001:")},
        ["condition 3", "no title after the colon"],
        failures=1,
        code=1,
    ),
    Case(
        "a byte-order mark is not a missing heading",
        {FIRST: "﻿" + GOOD},
        ["1 decision record(s), 0 failure(s)"],
    ),
    Case(
        "condition 4 fails a status outside the enum",
        {FIRST: GOOD.replace("- **Status:** accepted", "- **Status:** proposed")},
        ["condition 4", "accepted, superseded, withdrawn"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 4 fails a missing status line",
        {FIRST: GOOD.replace("- **Status:** accepted\n", "")},
        ["condition 4", "no `- **Status:**` line"],
        failures=1,
        code=1,
    ),
    Case(
        # Last-wins would have let the second line hide the first.
        "condition 4 fails a status given twice, rather than reading the last",
        {FIRST: GOOD.replace("- **Status:** accepted", "- **Status:** banana\n- **Status:** accepted")},
        ["condition 4", "`Status` is given 2 times"],
        failures=1,
        code=1,
    ),
    Case(
        "a header field may use any of Markdown's three bullet markers",
        {FIRST: GOOD.replace("- **Status:** accepted", "* **Status:** accepted")},
        ["1 decision record(s), 0 failure(s)"],
    ),
    Case(
        "condition 5 fails a date that is not ISO-8601",
        {FIRST: GOOD.replace("- **Date:** 2026-09-19", "- **Date:** 19 September 2026")},
        ["condition 5", "not an ISO-8601 date"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 5 fails a date that cannot exist",
        {FIRST: GOOD.replace("- **Date:** 2026-09-19", "- **Date:** 2026-13-01")},
        ["condition 5"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 6 fails a superseded record that names no successor",
        {FIRST: GOOD.replace("- **Status:** accepted", "- **Status:** superseded")},
        ["condition 6", "no `- **Superseded by:**` line"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 6 fails a pointer to a record that does not exist",
        {FIRST: SUPERSEDED},
        ["condition 6", "ADR-002 does not exist"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 6 fails a supersession written in one direction only",
        {FIRST: SUPERSEDED, SECOND: renumbered(GOOD, 2)},
        ["condition 6", "does not name this record back"],
        failures=1,
        code=1,
    ),
    Case(
        # Two findings, and always has been: the older record's status is
        # wrong and its pointer is missing. The count is the assertion that
        # says so out loud.
        "condition 6 fails a successor whose target still reads accepted",
        {FIRST: GOOD, SECOND: SUCCESSOR},
        ["condition 6", "is named as superseded and its own status is not"],
        failures=2,
        code=1,
    ),
    Case(
        "condition 6 fails a pointer that is not written as ADR-nnn",
        {FIRST: SUPERSEDED.replace("- **Superseded by:** ADR-002", "- **Superseded by:** the next one")},
        ["condition 6", "does not name a record"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 6 fails a record that supersedes itself",
        {
            FIRST: replacing(retired(GOOD, 1), "- **Supersedes:** ADR-001"),
        },
        ["condition 6", "names itself"],
        failures=2,
        code=1,
    ),
    Case(
        "condition 6 fails two records that supersede each other",
        {
            FIRST: replacing(retired(GOOD, 2), "- **Supersedes:** ADR-002"),
            SECOND: replacing(retired(renumbered(GOOD, 2), 1), "- **Supersedes:** ADR-001"),
        },
        ["condition 6", "supersession runs in a circle: ADR-001 -> ADR-002 -> ADR-001"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 6 fails a ring of three",
        {
            FIRST: replacing(retired(GOOD, 2), "- **Supersedes:** ADR-003"),
            SECOND: replacing(retired(renumbered(GOOD, 2), 3), "- **Supersedes:** ADR-001"),
            THIRD: replacing(retired(renumbered(GOOD, 3), 1), "- **Supersedes:** ADR-002"),
        },
        ["condition 6", "ADR-001 -> ADR-002 -> ADR-003 -> ADR-001"],
        failures=1,
        code=1,
    ),
    Case(
        # Condition 2 forbids deleting a record, so merging two decisions into
        # one is a supersession with two edges on the new record.
        "condition 6 resolves one record superseding two, written on two lines",
        {
            FIRST: retired(GOOD, 3),
            SECOND: retired(renumbered(GOOD, 2), 3),
            THIRD: replacing(
                renumbered(GOOD, 3), "- **Supersedes:** ADR-001\n- **Supersedes:** ADR-002"
            ),
        },
        ["3 decision record(s), 0 failure(s)"],
    ),
    Case(
        "condition 6 resolves one record superseding two, written on one line",
        {
            FIRST: retired(GOOD, 3),
            SECOND: retired(renumbered(GOOD, 2), 3),
            THIRD: replacing(renumbered(GOOD, 3), "- **Supersedes:** ADR-001, ADR-002"),
        },
        ["3 decision record(s), 0 failure(s)"],
    ),
    Case(
        "condition 6 fails `Superseded by` given twice",
        {FIRST: SUPERSEDED.replace("- **Superseded by:** ADR-002", "- **Superseded by:** ADR-002\n- **Superseded by:** ADR-003")},
        ["condition 6", "`Superseded by` is given 2 times"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 7 fails a missing section",
        {FIRST: GOOD.replace("## Consequences", "## Outcome")},
        ["condition 7", "no `## Consequences` section"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 7 fails an alternatives section with no list item",
        {FIRST: GOOD.replace(ALTERNATIVE, "None came up.")},
        ["condition 7", "carries no list item"],
        failures=1,
        code=1,
    ),
    Case(
        "condition 7 accepts an ordered list under alternatives",
        {FIRST: GOOD.replace(ALTERNATIVE, "1. **A wider table.** Rejected: too wide.")},
        ["1 decision record(s), 0 failure(s)"],
    ),
    Case(
        "a `#` heading closes the alternatives section",
        {
            FIRST: GOOD.replace(ALTERNATIVE + "\n", "")
            + "\n# Appendix\n\n- A bullet that is not an alternative.\n"
        },
        ["condition 7", "carries no list item"],
        failures=1,
        code=1,
    ),
    Case(
        # Hiding the rest of the file behind the open fence reported three
        # sections missing that are plainly there.
        "an unterminated fence is the finding, not the sections it would hide",
        {FIRST: GOOD + "\n```text\n7   8   11   13   15\n"},
        ["condition 7", "never closed"],
        failures=1,
        code=1,
    ),
    # Pinned limits, not oversights.
    #
    # The alternatives clause is presence and not substance, which the rule and
    # its doc both say in as many words. A bullet that considers nothing
    # satisfies condition 7 and a reviewer is the only thing that catches it.
    Case(
        "an alternative that says nothing still passes condition 7",
        {FIRST: GOOD.replace(ALTERNATIVE, "- Do nothing.")},
        ["0 failure(s)"],
    ),
    # A record quoting a heading or a header line inside a fence is not making
    # one. The fenced copy below would otherwise register a second status.
    Case(
        "a heading quoted inside a fence is not a section",
        {FIRST: GOOD + "\n```markdown\n## Context\n- **Status:** proposed\n```\n"},
        ["0 failure(s)"],
    ),
    # The first thing anybody does with this hook is copy the template and run
    # it. Everything it reports must be a placeholder the reader was asked to
    # fill in, and nothing else — least of all a `Supersedes` line the skeleton
    # put there, whose message told the reader to write what they had written.
    Case(
        "the shipped skeleton fails only on what it asks the reader to fill in",
        {"docs/adr/ADR-001-a-copied-skeleton.md": skeleton()},
        [
            "the heading says ADR-nnn and a record's number is three digits",
            "'YYYY-MM-DD' is not an ISO-8601 date",
            "carries no list item",
        ],
        failures=3,
        code=1,
    ),
]


def write(root: Path, files: dict) -> None:
    """The fixture on disk. A bytes value is written as given, for the cases
    about a file that is not UTF-8 text."""
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")


def run(files: dict, where: str | None) -> tuple:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root, files)
        command = [sys.executable, str(HOOK)]
        if where is not None:
            command.append(str(root / where))
        result = subprocess.run(command, capture_output=True, text=True, cwd=str(root))
        return result.returncode, result.stdout + result.stderr


def counted(output: str) -> int | None:
    """The failure count the hook printed, or None where it printed none."""
    match = COUNTED.search(output)
    return int(match.group(1)) if match is not None else None


def wanted_code(case: Case) -> int:
    """The exit the hook owes: a failure for any finding, and for a bad path."""
    if case.failures is None:
        return case.code
    return 1 if case.failures else 0


def problems_with(case: Case, code: int, output: str) -> list:
    found = []
    expected = wanted_code(case)
    if code != expected:
        found.append(f"expected exit {expected}, the hook exited {code}")
    reported = counted(output)
    if case.failures != reported:
        found.append(f"expected exactly {case.failures} failure(s), the hook reported {reported}")
    for fragment in case.expect:
        if fragment not in output:
            found.append(f"expected {fragment!r} in the output")
    return found


def report(name: str, problems: list, output: str) -> None:
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")


def main() -> int:
    failed = 0
    for case in CASES:
        code, output = run(case.files, case.where)
        problems = problems_with(case, code, output)
        if problems:
            failed += 1
            report(case.name, problems, output)
        else:
            print(f"ok    {case.name}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
