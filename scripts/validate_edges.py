#!/usr/bin/env python3
"""Validate the artifact graph: every declared edge must resolve.

Checks two kinds of edge:
  - typed edges in frontmatter (consults / relates / consulted_by), written as
    repo-relative paths without the .md suffix
  - markdown links between artifacts

Exits non-zero on the first dangling edge. This is the seed of issue #3; the
hierarchy-direction check is not implemented yet.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOTS = ("rules", "docs", "skills", "agents", "commands")
FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.S)
TYPED_EDGE = re.compile(r"^\s+- ((?:%s)/[\w/-]+)$" % "|".join(ROOTS), re.M)
MD_LINK = re.compile(r"\]\((\.\.?/[^)]+\.md)\)")


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parent.parent
    artifacts = {
        str(p.relative_to(repo).with_suffix(""))
        for root in ROOTS
        for p in (repo / root).rglob("*.md")
    }
    dangling: list[str] = []

    for root in ROOTS:
        for path in (repo / root).rglob("*.md"):
            rel = path.relative_to(repo)
            text = path.read_text(encoding="utf-8")

            block = FRONTMATTER.match(text)
            if block:
                for target in TYPED_EDGE.findall(block.group(1)):
                    if target not in artifacts:
                        dangling.append(f"{rel}: typed edge -> {target}")

            for link in MD_LINK.findall(text):
                if not (path.parent / link).resolve().exists():
                    dangling.append(f"{rel}: link -> {link}")

    if dangling:
        print(f"{len(dangling)} dangling edge(s):", file=sys.stderr)
        for item in dangling:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"{len(artifacts)} artifacts, every declared edge resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
