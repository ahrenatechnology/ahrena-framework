#!/usr/bin/env python3
"""Reference reader for the review marker.

The contract is in step 1 of ../SKILL.md. Reads a comment body on stdin and
prints the verdict, or `unknown` when the body has no valid marker.

Usage:
    python3 marker.py < comment-body.txt
"""

from __future__ import annotations

import re
import sys

MARKER = re.compile(
    r"<!-- ahrena-review:(?P<pr>[1-9][0-9]*):(?P<sha>[0-9a-f]{7,40})"
    r" verdict=(?P<verdict>approve|request-changes|comment) -->"
)


def parse(body: str) -> dict[str, str] | None:
    """The marker on the first line of the body, or None."""
    lines = body.splitlines()
    first = lines[0].strip() if lines else ""
    found = MARKER.fullmatch(first)
    return found.groupdict() if found else None


def approves(body: str, head: str) -> bool:
    """True when the body is an approval whose sha is a prefix of head."""
    marker = parse(body)
    return bool(marker) and marker["verdict"] == "approve" and head.startswith(marker["sha"])


def main() -> int:
    marker = parse(sys.stdin.read())
    print(marker["verdict"] if marker else "unknown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
