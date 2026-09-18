#!/usr/bin/env python3
"""<One line: which rule this decides.>

Decides the conditions stated in <plugin>/rules/<rule>.md:

    1. <condition>
    2. <condition>

Standard library only. The hook ships inside the plugin, so a consumer runs
the same check CI runs without installing anything.

Usage:
    python3 <plugin>/hooks/<name>.py [root]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

RULE = "<rule-id>"


@dataclass
class Finding:
    where: str  # path, with :line where a line exists
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] {self.message}"


def subjects(root: Path) -> list[Path]:
    """Everything the rule applies to.

    Derive this from a manifest the repository already maintains where one
    exists, rather than from a glob. A glob drifts from the catalogue; a
    manifest is the catalogue.
    """
    raise NotImplementedError


def check(subject: Path, findings: list[Finding]) -> None:
    """One function per condition, each appending its own findings.

    Report every failure rather than stopping at the first. Somebody fixing
    six findings in one pass beats six red builds.
    """
    raise NotImplementedError


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    findings: list[Finding] = []
    checked = 0

    for subject in subjects(root):
        check(subject, findings)
        checked += 1

    if findings:
        print(f"{len(findings)} failure(s) across {checked} subject(s):\n")
        for finding in findings:
            print(finding)
        return 1

    print(f"{checked} subject(s), no failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
