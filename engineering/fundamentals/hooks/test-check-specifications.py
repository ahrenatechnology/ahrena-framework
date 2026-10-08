#!/usr/bin/env python3
"""Tests for check-specifications.py.

A gate that has never rejected anything is a claim, not a guardrail, so every
condition is pinned by a tree that fails it and by the tree it must not flag.

The hook runs as a subprocess on purpose: that is what CI runs, exit code
included. `where=None` runs it from the fixture root with no argument, which
is how a consumer invokes it and the only invocation for which a missing
directory is allowed to pass.

Every case states the number of failures the hook must report, and the harness
compares it against the count the hook prints. A case that asserted only a
fragment would pass on its own reason plus any number of others.

The skeleton and the filled example are read from the template the skill
ships, not restated, so the suite fails when the shipped template stops being
something a reader can fill in and pass with.

Usage:
    python3 engineering/fundamentals/hooks/test-check-specifications.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-specifications.py"
TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "writing-entity-specifications"
    / "references"
    / "entity-specification.md"
)

COUNTED = re.compile(r"(\d+) failure\(s\)")

HOME = "docs/billing/entities/subscription.md"


def template_part(index: int) -> str:
    """One of the template's parts, which its `---` rules separate.

    Part 1 is the skeleton the skill's step 3 copies and part 3 is the filled
    example.
    """
    return TEMPLATE.read_text(encoding="utf-8").split("\n---\n")[index].strip() + "\n"


# The smallest specification the suite needs is the one the template ships.
# Each failing case below is this with exactly one thing broken, and the
# failure count is asserted, so a case can only fail for its reason.
GOOD = template_part(3)
SKELETON = template_part(1)


def without_section(text: str, name: str) -> str:
    """The same specification with one `##` heading gone and its body left behind."""
    assert f"\n## {name}\n" in text, name
    return text.replace(f"\n## {name}\n", "\n")


def with_header(text: str, name: str, value: str | None) -> str:
    """The same specification with one header line replaced, or removed for None."""
    line = re.compile(rf"^- \*\*{name}:\*\* .*\n", re.MULTILINE)
    assert line.search(text), name
    return line.sub("" if value is None else f"- **{name}:** {value}\n", text)


@dataclass
class Case:
    name: str
    files: dict
    expect: list = field(default_factory=list)
    # The count the hook must print. None where it prints none at all, and the
    # exit code is then stated separately.
    failures: int | None = 0
    code: int = 0
    where: str | None = None


CASES = [
    # --- the template the skill ships (#94/AC-2, #94/AC-3)
    Case(
        "the template's filled example passes at its home",
        {HOME: GOOD},
        ["1 entity specification(s) in 1 context(s), 0 failure(s)"],
    ),
    Case(
        "the skeleton copied unfilled fails only on what it asks the reader to fill in",
        {"docs/billing/entities/a-copied-skeleton.md": SKELETON},
        [
            "condition 4: the heading '{EntityName}' is not one PascalCase word",
            "condition 5: the classification '{aggregate root, entity or value object}'",
            "condition 6: the header names the context '{context}'",
            "line(s) still carry a template placeholder in braces",
        ],
        failures=4,
    ),
    # --- nothing to decide (#94/AC-9)
    Case("no docs directory at all is nothing to decide", {}, ["nothing to decide"], failures=None),
    Case(
        "a docs directory holding no context is nothing to decide",
        {"docs/adr/ADR-001-a-decision.md": "# ADR-001: A decision\n", "docs/guide.md": "# Guide\n"},
        ["no specifications here, nothing to decide"],
        failures=None,
    ),
    Case(
        "a path given and not found fails, where the default path would pass",
        {},
        ["not a directory"],
        failures=None,
        code=1,
        where="documentation",
    ),
    Case(
        "a docs directory given by path is read",
        {f"handbook/{HOME}": GOOD},
        ["1 entity specification(s) in 1 context(s), 0 failure(s)"],
        where="handbook/docs",
    ),
    # --- condition 1: the kind sits inside the context (#94/AC-4)
    Case(
        "a kind directory directly under docs fails as an inverted hierarchy",
        {"docs/entities/billing/subscription.md": GOOD},
        ["docs/entities", "[specification-homes] condition 1", "sits above the contexts"],
        failures=1,
    ),
    Case(
        "each of the four kinds is refused above the contexts",
        {
            "docs/entities/.gitkeep": "",
            "docs/contracts/.gitkeep": "",
            "docs/capabilities/.gitkeep": "",
            "docs/metrics/.gitkeep": "",
        },
        ["0 entity specification(s) in 0 context(s), 4 failure(s)"],
        failures=4,
    ),
    Case(
        "the three kinds with no shape are located and read no further",
        {
            HOME: GOOD,
            "docs/billing/contracts/openapi.yaml": "openapi: 3.1.0\n",
            "docs/billing/capabilities/anything.md": "{not judged}\n",
            "docs/billing/metrics/anything.md": "{not judged}\n",
        },
        ["1 entity specification(s) in 1 context(s), 0 failure(s)"],
    ),
    # --- condition 2: the context is kebab-case
    Case(
        "a context directory that is not kebab-case fails",
        {"docs/ScheduledPayments/entities/subscription.md": with_header(GOOD, "Context", "ScheduledPayments")},
        ["docs/ScheduledPayments", "condition 2", "is not kebab-case"],
        failures=1,
    ),
    Case(
        "a context holding only a contract is still a context",
        {"docs/Billing/contracts/openapi.yaml": "openapi: 3.1.0\n"},
        ["0 entity specification(s) in 1 context(s), 1 failure(s)", "condition 2"],
        failures=1,
    ),
    Case(
        "a directory holding no kind is not a context, whatever it is called",
        {HOME: GOOD, "docs/Old_Notes/entities.md": "{not judged}\n", "docs/adr/README.md": "# Log\n"},
        ["1 entity specification(s) in 1 context(s), 0 failure(s)"],
    ),
    # --- condition 3: one kebab-case markdown file per entity
    Case(
        "a subdirectory of entities fails",
        {HOME: GOOD, "docs/billing/entities/archive/plan.md": GOOD},
        ["docs/billing/entities/archive", "condition 3", "one .md file per entity"],
        failures=1,
    ),
    Case(
        "a file that is not markdown fails",
        {HOME: GOOD, "docs/billing/entities/subscription.txt": GOOD},
        ["docs/billing/entities/subscription.txt", "condition 3"],
        failures=1,
    ),
    Case(
        "a filename that is not kebab-case fails once, not also under condition 4",
        {"docs/billing/entities/Subscription.md": GOOD},
        ["condition 3: 'Subscription' is not kebab-case"],
        failures=1,
    ),
    Case(
        "an index and a placeholder file are not specifications",
        {HOME: GOOD, "docs/billing/entities/README.md": "# Entities\n", "docs/billing/entities/.gitkeep": ""},
        ["1 entity specification(s) in 1 context(s), 0 failure(s)"],
    ),
    Case(
        "a file that is not UTF-8 text fails without a traceback",
        {HOME: b"\xff\xfe\x00not text"},
        ["condition 3: the file is not UTF-8 text"],
        failures=1,
    ),
    # --- condition 4: the heading and the filename are one name (#94/AC-5)
    Case(
        "a filename that is another entity's fails",
        {"docs/billing/entities/invoice.md": GOOD},
        ["docs/billing/entities/invoice.md:1", "condition 4", "the heading names 'Subscription' and the file is 'invoice.md'"],
        failures=1,
    ),
    Case(
        "a two-word name agrees with its hyphenated filename",
        {"docs/billing/entities/scheduled-transfer.md": GOOD.replace("# Subscription", "# ScheduledTransfer")},
        ["0 failure(s)"],
    ),
    Case(
        "a heading that is not one PascalCase word fails",
        {HOME: GOOD.replace("# Subscription", "# Entity: Subscription")},
        ["condition 4: the heading 'Entity: Subscription' is not one PascalCase word"],
        failures=1,
    ),
    Case(
        "a file with no heading fails",
        {HOME: GOOD.replace("# Subscription\n", "")},
        ["condition 4: no `# ` heading"],
        failures=1,
    ),
    # --- condition 5: the classification (#94/AC-6)
    Case(
        "a classification outside the closed set fails",
        {HOME: with_header(GOOD, "Classification", "table")},
        [f"{HOME}:3", "condition 5: the classification 'table' is not one of: aggregate root, entity, value object"],
        failures=1,
    ),
    Case(
        "a header with no classification line fails",
        {HOME: with_header(GOOD, "Classification", None)},
        ["condition 5: no `- **Classification:**` line"],
        failures=1,
    ),
    Case(
        "each of the three classifications passes",
        {
            HOME: GOOD,
            "docs/billing/entities/invoice-line.md": with_header(
                GOOD.replace("# Subscription", "# InvoiceLine"), "Classification", "entity"
            ),
            "docs/billing/entities/period.md": with_header(
                GOOD.replace("# Subscription", "# Period"), "Classification", "value object"
            ),
        },
        ["3 entity specification(s) in 1 context(s), 0 failure(s)"],
    ),
    Case(
        "a classification written below the first section is not in the header",
        {HOME: with_header(GOOD, "Classification", None) + "\n- **Classification:** aggregate root\n"},
        ["condition 5: no `- **Classification:**` line"],
        failures=1,
    ),
    # --- condition 6: the context named is the directory (#94/AC-7)
    Case(
        "a header naming another context fails",
        {"docs/payments/entities/subscription.md": GOOD},
        ["docs/payments/entities/subscription.md:4", "condition 6", "names the context 'billing' and the file sits in 'payments'"],
        failures=1,
    ),
    Case(
        "a header with no context line fails",
        {HOME: with_header(GOOD, "Context", None)},
        ["condition 6: no `- **Context:**` line"],
        failures=1,
    ),
    # --- condition 7: the seven sections, filled (#94/AC-8)
    *[
        Case(
            f"a specification without its {name} section fails and names it",
            {HOME: without_section(GOOD, name)},
            [f"condition 7: no `## {name}` section"],
            failures=1,
        )
        for name in (
            "Why it exists",
            "Fields",
            "Invariants",
            "Business rules",
            "Relationships",
            "Events",
            "Errors",
        )
    ],
    Case(
        "a section that exists only inside a fenced block is an example, not a section",
        {HOME: without_section(GOOD, "Errors") + "\n```markdown\n## Errors\n```\n"},
        ["condition 7: no `## Errors` section"],
        failures=1,
    ),
    Case(
        "a section reading None is present",
        {HOME: GOOD.split("## Errors")[0] + "## Errors\n\nNone. Every refusal belongs to the root.\n"},
        ["0 failure(s)"],
    ),
    Case(
        "a placeholder left in one row fails once, at its line",
        {HOME: GOOD + "\n| {the attempt that is refused} | BR-2 | {the reason} |\n"},
        ["condition 7: 1 line(s) still carry a template placeholder"],
        failures=1,
    ),
    Case(
        "a brace inside a code span or a fenced block is a literal",
        {HOME: GOOD + "\nThe route is `/subscriptions/{id}`.\n\n```json\n{\"plan\": \"basic\"}\n```\n"},
        ["0 failure(s)"],
    ),
    Case(
        "a fenced block never closed is the finding, and hides nothing",
        {HOME: GOOD + "\n```json\n"},
        ["condition 7: a fenced block is opened here and never closed"],
        failures=1,
    ),
    # --- several contexts
    Case(
        "every context is read, and each failure is counted where it is",
        {
            HOME: GOOD,
            "docs/payments/entities/subscription.md": with_header(GOOD, "Context", "payments"),
            "docs/payments/entities/refund.md": GOOD,
        },
        ["3 entity specification(s) in 2 context(s), 2 failure(s)", "docs/payments/entities/refund.md"],
        failures=2,
    ),
]


def write(root: Path, files: dict) -> None:
    """The fixture on disk. A bytes value is written as given, for the case
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
