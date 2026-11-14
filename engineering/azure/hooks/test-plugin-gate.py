#!/usr/bin/env python3
"""The Azure plugin passes the foundation gate as a member of the marketplace.

#299/AC-6: `python3 foundation/hooks/validate-artifacts.py` passes and the
plugin graph stays acyclic. The gate's own suite tests the gate; this checks
that the gate reaches this plugin and that every artifact of it is read, so a
marketplace entry dropped in a rebase cannot leave the plugin unchecked.
Standard library only.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent
GATE = REPO / "foundation" / "hooks" / "validate-artifacts.py"
NAME = "ahrena-engineering-azure"


def load_gate():
    spec = importlib.util.spec_from_file_location("validate_artifacts", GATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    gate = load_gate()
    failures = 0

    listed = {name: path for name, path in gate.plugin_paths(REPO)}
    ok = NAME in listed and Path(listed[NAME]).resolve() == PLUGIN
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  #299/AC-6 the marketplace lists {NAME} at engineering/azure")

    on_disk = sorted(
        [p for d in ("rules", "docs", "agents") for p in (PLUGIN / d).glob("*.md")]
        + list((PLUGIN / "skills").glob("*/SKILL.md"))
    )
    findings: list = []
    read = gate.collect(PLUGIN, NAME, findings) if ok else []
    ok = len(read) == len(on_disk) and not findings
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  #299/AC-6 the gate reads all {len(on_disk)} artifacts of the plugin (read {len(read)})")

    ok = gate.main(["validate-artifacts.py", str(REPO)]) == 0
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  #299/AC-6 the gate passes over the marketplace, plugin graph included")

    print(f"\n{3 - failures} of 3 cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
