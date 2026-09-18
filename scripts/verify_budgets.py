#!/usr/bin/env python3
"""Enforce per-artifact size budgets.

Every artifact has a ceiling: an explicit entry under `frozen`, or its type
target. Exceeding the ceiling fails. Exceeding the type target without a frozen
entry also fails, which forces over-budget artifacts to be visible in the
manifest rather than silently large.

See the `_policy` block in artifact-budgets.json for the ladder.
"""
from __future__ import annotations

import json
import pathlib
import sys

TYPES = ("rules", "docs", "skills", "agents", "commands")
HEADROOM = 0.95


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parent.parent
    manifest = json.loads((repo / "scripts" / "artifact-budgets.json").read_text())
    targets: dict[str, int] = manifest["targets"]
    frozen = {k: v for k, v in manifest["frozen"].items() if not k.startswith("_")}

    artifacts = sorted(
        p for artifact_type in TYPES for p in (repo / artifact_type).rglob("*.md")
    )
    if len(artifacts) < 4:
        print(
            f"artifact discovery returned {len(artifacts)} file(s); "
            "the scan is broken, not the budgets",
            file=sys.stderr,
        )
        return 2

    over: list[str] = []
    undeclared: list[str] = []
    tight: list[str] = []
    debt = 0

    for path in artifacts:
        rel = str(path.relative_to(repo))
        size = path.stat().st_size
        target = targets[rel.split("/")[0]]
        ceiling = frozen.get(rel, target)

        if size > ceiling:
            over.append(f"{rel}: {size} B exceeds its ceiling of {ceiling} B")
        elif rel in frozen:
            debt += size - target
        elif size > target:
            undeclared.append(
                f"{rel}: {size} B is over the {target} B target for its type "
                "and carries no frozen entry"
            )
        elif size > target * HEADROOM:
            tight.append(f"{rel}: {size} B leaves under 5% headroom of {target} B")

    for line in tight:
        print(f"  headroom: {line}")

    if over or undeclared:
        print(f"{len(over) + len(undeclared)} budget violation(s):", file=sys.stderr)
        for line in over + undeclared:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(
        f"verify-budgets: {len(artifacts)} artifact(s) within budget; "
        f"{len(frozen)} frozen, {debt} B of recorded debt."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
