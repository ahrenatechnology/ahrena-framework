#!/usr/bin/env python3
"""Tests for the ahrena-engineering-llm-systems plugin's wiring.

Each property is one a script can decide:

    1. the artifact gate passes over the whole marketplace, including the
       acyclic plugin graph (#351/AC-5, #352/AC-4, #353/AC-3)
    2. the plugin is catalogued and its three manifests agree with the
       catalogue on name and version (#351/AC-1)
    3. the plugin declares references only to itself and to
       ahrena-engineering-fundamentals, so the edge Claudionor adds from
       ahrena-foundation cannot close a cycle (ADR-021)

Standard library only. Run from anywhere:

    python3 -B engineering/llm-systems/tests/test-plugin.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
ROOT = PLUGIN.parent.parent
NAME = "ahrena-engineering-llm-systems"
ALLOWED = {NAME, "ahrena-engineering-fundamentals"}
QUALIFIED = re.compile(r"^\s*-\s*(ahrena-[a-z0-9-]+):", re.MULTILINE)


def test_gate_passes() -> list[str]:
    """#351/AC-5, #352/AC-4, #353/AC-3"""
    run = subprocess.run(
        [sys.executable, "-B", str(ROOT / "foundation/hooks/validate-artifacts.py"), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0 or "no failures" not in run.stdout:
        return [f"the artifact gate failed:\n{run.stdout}{run.stderr}"]
    return []


def test_catalogued() -> list[str]:
    """#351/AC-1"""
    catalogue = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    entries = [p for p in catalogue["plugins"] if p["name"] == NAME]
    if len(entries) != 1:
        return [f"{NAME} is listed {len(entries)} times in the marketplace"]
    entry = entries[0]
    errors = []
    if entry["source"]["path"] != "engineering/llm-systems":
        errors.append(f"the marketplace points {NAME} at {entry['source']['path']}")
    for platform in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
        path = PLUGIN / platform / "plugin.json"
        if not path.is_file():
            errors.append(f"{platform}/plugin.json is missing")
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for key in ("name", "version"):
            if manifest.get(key) != entry[key]:
                errors.append(f"{platform}/plugin.json {key} is {manifest.get(key)!r}, the marketplace has {entry[key]!r}")
    return errors


def test_references_stay_downstream_of_nothing() -> list[str]:
    """ADR-021: only itself and fundamentals."""
    errors = []
    for path in sorted(PLUGIN.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        frontmatter = text.split("---", 2)[1]
        for owner in QUALIFIED.findall(frontmatter):
            if owner not in ALLOWED:
                errors.append(f"{path.relative_to(ROOT)} references {owner}, which ADR-021 does not allow")
    return errors


if __name__ == "__main__":
    failures = []
    for test in (test_gate_passes, test_catalogued, test_references_stay_downstream_of_nothing):
        errors = test()
        print(f"{'ok  ' if not errors else 'FAIL'}  {test.__name__}")
        failures += errors
    for error in failures:
        print(f"  {error}")
    sys.exit(1 if failures else 0)
