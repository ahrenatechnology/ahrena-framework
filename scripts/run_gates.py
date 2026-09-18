#!/usr/bin/env python3
"""Run the named gates.

One narrow gate per invariant, composed here. Each gate is its own script, owns
one invariant, prints one success line with a count, and on failure prints the
offending artifact and exits non-zero.

  run_gates.py            every gate
  run_gates.py --quick    the build-free subset, for a local edit loop
  run_gates.py --list     the registry

Adding a gate means adding a row here and a case to gates_test.py proving the
gate rejects a bad input. A gate with no failing case is not a gate.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent

# name -> (script, quick)
GATES: dict[str, tuple[str, bool]] = {
    "verify-edges": ("validate_edges.py", True),
    "verify-budgets": ("verify_budgets.py", True),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="the build-free subset")
    parser.add_argument("--list", action="store_true", help="print the registry")
    args = parser.parse_args()

    if args.list:
        for name, (script, quick) in GATES.items():
            print(f"{name:20} {script:24} {'quick' if quick else 'full'}")
        return 0

    selected = {n: g for n, g in GATES.items() if g[1] or not args.quick}
    failed: list[str] = []

    for name, (script, _) in selected.items():
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / script)], capture_output=True, text=True
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            failed.append(f"{name} (exit {result.returncode})")

    mode = "quick" if args.quick else "all"
    if failed:
        print(f"\n{mode}: {len(failed)} of {len(selected)} gate(s) failed:", file=sys.stderr)
        for item in failed:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"\n{mode}: {len(selected)} gate(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
