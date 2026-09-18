#!/usr/bin/env python3
"""Validate the artifact graph: every declared edge must resolve.

Checks two kinds of edge:
  - typed edges in frontmatter (invokes / orchestrates), written as repo-relative
    paths without the .md suffix. Per issue #3 these carry only the relations
    where direction is an authority claim; everything else is a prose link.
  - markdown links between artifacts, relative, including same-directory ones

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
# Any relative .md target, including a same-directory link like (yagni.md).
# Anchoring on ./ or ../ silently skipped every sibling reference.
MD_LINK = re.compile(r"\]\((?!https?:|/)([^)#]+\.md)(?:#[^)]*)?\)")


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parent.parent
    artifacts = {
        str(p.relative_to(repo).with_suffix(""))
        for root in ROOTS
        for p in (repo / root).rglob("*.md")
    }
    # A gate that passes because it scanned nothing is worse than no gate.
    # Assert the scan found the areas it is supposed to cover before trusting
    # a green result.
    required = ("rules/engineering/quality/solid", "docs/engineering/quality/solid")
    missing_areas = [area for area in required if area not in artifacts]
    if missing_areas or len(artifacts) < 4:
        print(
            f"artifact discovery returned {len(artifacts)} artifact(s) and is "
            f"missing {missing_areas or 'nothing'}; the scan is broken, not the graph",
            file=sys.stderr,
        )
        return 2

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
