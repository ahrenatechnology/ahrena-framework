#!/usr/bin/env python3
"""Tests for check-decision-records.py.

A gate that has never rejected anything is a claim, not a guardrail.

The hook runs as a subprocess on purpose: that is what CI runs, exit code
included. It is always pointed at `docs/adr` under the fixture root, which is
the path it defaults to, so the case with no files at all exercises the
"nothing to decide" branch a consumer with no decision log gets.

Usage:
    python3 contributing/hooks/test-check-decision-records.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-decision-records.py"

FIRST = "docs/adr/ADR-001-records-live-at-the-repository-root.md"
SECOND = "docs/adr/ADR-002-the-log-keeps-its-index.md"

# The smallest record that satisfies every condition. Each failing case below
# is this with exactly one thing broken, so a case can only fail for its reason.
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


def case(name: str, files: dict, expect: list, ok: bool = False) -> tuple:
    return (name, files, expect, ok)


CASES = [
    case("a valid record passes", {FIRST: GOOD}, ["1 decision record(s), 0 failure(s)"], ok=True),
    case(
        "no decision log at all is nothing to decide",
        {},
        ["nothing to decide"],
        ok=True,
    ),
    case(
        "a resolved supersession pair passes",
        {FIRST: SUPERSEDED, SECOND: SUCCESSOR},
        ["2 decision record(s), 0 failure(s)"],
        ok=True,
    ),
    case(
        "condition 1 fails a filename that is not ADR-nnn-slug",
        {"docs/adr/adr-1-records.md": GOOD},
        ["condition 1", "kebab-case slug"],
    ),
    case(
        "condition 1 fails a two-digit number",
        {"docs/adr/ADR-01-records-live-at-the-repository-root.md": GOOD},
        ["condition 1"],
    ),
    case(
        "condition 2 fails a duplicate number",
        {FIRST: GOOD, "docs/adr/ADR-001-the-log-keeps-its-index.md": GOOD},
        ["condition 2", "already taken by"],
    ),
    case(
        "condition 2 fails a gap left by a deletion",
        {FIRST: GOOD, "docs/adr/ADR-003-a-third-record.md": GOOD.replace("# ADR-001:", "# ADR-003:")},
        ["condition 2", "ADR-002 is missing"],
    ),
    case(
        "condition 3 fails a heading that disagrees with the filename",
        {FIRST: GOOD.replace("# ADR-001:", "# ADR-007:")},
        ["condition 3", "the heading says ADR-007"],
    ),
    case(
        "condition 3 fails a record with no heading",
        {FIRST: GOOD.replace("# ADR-001: Records live at the repository root\n", "")},
        ["condition 3", "no heading"],
    ),
    case(
        "condition 4 fails a status outside the enum",
        {FIRST: GOOD.replace("- **Status:** accepted", "- **Status:** proposed")},
        ["condition 4", "accepted, superseded, withdrawn"],
    ),
    case(
        "condition 4 fails a missing status line",
        {FIRST: GOOD.replace("- **Status:** accepted\n", "")},
        ["condition 4", "no `- **Status:**` line"],
    ),
    case(
        "condition 5 fails a date that is not ISO-8601",
        {FIRST: GOOD.replace("- **Date:** 2026-09-19", "- **Date:** 19 September 2026")},
        ["condition 5", "not an ISO-8601 date"],
    ),
    case(
        "condition 5 fails a date that cannot exist",
        {FIRST: GOOD.replace("- **Date:** 2026-09-19", "- **Date:** 2026-13-01")},
        ["condition 5"],
    ),
    case(
        "condition 6 fails a superseded record that names no successor",
        {FIRST: GOOD.replace("- **Status:** accepted", "- **Status:** superseded")},
        ["condition 6", "no `- **Superseded by:**` line"],
    ),
    case(
        "condition 6 fails a pointer to a record that does not exist",
        {FIRST: SUPERSEDED},
        ["condition 6", "ADR-002 does not exist"],
    ),
    case(
        "condition 6 fails a supersession written in one direction only",
        {FIRST: SUPERSEDED, SECOND: GOOD.replace("# ADR-001:", "# ADR-002:")},
        ["condition 6", "does not name this record back"],
    ),
    case(
        "condition 6 fails a successor whose target still reads accepted",
        {FIRST: GOOD, SECOND: SUCCESSOR},
        ["condition 6"],
    ),
    case(
        "condition 6 fails a pointer that is not written as ADR-nnn",
        {FIRST: SUPERSEDED.replace("- **Superseded by:** ADR-002", "- **Superseded by:** the next one")},
        ["condition 6", "does not name a record"],
    ),
    case(
        "condition 7 fails a missing section",
        {FIRST: GOOD.replace("## Consequences", "## Outcome")},
        ["condition 7", "no `## Consequences` section"],
    ),
    case(
        "condition 7 fails an alternatives section with no list item",
        {FIRST: GOOD.replace("- **A wider table.** Rejected: a consequence cell of 111 words is not read.", "None came up.")},
        ["condition 7", "carries no list item"],
    ),
    # Pinned limits, not oversights.
    #
    # The alternatives clause is presence and not substance, which the rule and
    # its doc both say in as many words. A bullet that considers nothing
    # satisfies condition 7 and a reviewer is the only thing that catches it.
    case(
        "an alternative that says nothing still passes condition 7",
        {FIRST: GOOD.replace("- **A wider table.** Rejected: a consequence cell of 111 words is not read.", "- Do nothing.")},
        ["0 failure(s)"],
        ok=True,
    ),
    # A record quoting a heading or a header line inside a fence is not making
    # one. The fenced copy below would otherwise register a second status.
    case(
        "a heading quoted inside a fence is not a section",
        {FIRST: GOOD + "\n```markdown\n## Context\n- **Status:** proposed\n```\n"},
        ["0 failure(s)"],
        ok=True,
    ),
]


def run(files: dict) -> tuple:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(HOOK), str(root / "docs" / "adr")],
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr


def problems_with(code: int, output: str, expect: list, ok: bool) -> list:
    found = []
    if ok and code != 0:
        found.append("expected the hook to pass, it failed")
    if not ok and code == 0:
        found.append("expected the hook to fail, it passed")
    for fragment in expect:
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
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = problems_with(code, output, expect, ok)
        if problems:
            failed += 1
            report(name, problems, output)
        else:
            print(f"ok    {name}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
