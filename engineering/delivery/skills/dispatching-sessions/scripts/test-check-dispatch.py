#!/usr/bin/env python3
"""Tests for check-dispatch.py.

Each case in fixtures/dispatches.json is one dispatch with the verdict it must
get and a line the report must carry. The script runs as a subprocess on each,
and once on the whole list. The behaviour is pinned against #225's criterion:

    #225/AC-6  one issue per child session, Sonnet unless the brief states why,
               title and brief in the person's language, the child runs Athena;
               a second, unrelated demand to a session holding one is refused,
               and a pull request another tool owns is skipped

Usage:
    python3 engineering/delivery/skills/dispatching-sessions/scripts/test-check-dispatch.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check-dispatch.py"
FIXTURES = json.loads((HERE / "fixtures" / "dispatches.json").read_text(encoding="utf-8"))
EXIT = {"dispatch": 0, "refuse": 1, "skip": 1}


def run(payload: object) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dispatch.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def check(case: dict) -> list[str]:
    code, output = run(case["dispatch"])
    found = []
    if code != EXIT[case["verdict"]]:
        found.append(f"exited {code}, not {EXIT[case['verdict']]}: {output.strip()}")
    if not output.startswith(f"{case['verdict']}:"):
        found.append(f"verdict was not {case['verdict']}: {output.strip()}")
    if case["says"] not in output:
        found.append(f"the report does not say '{case['says']}': {output.strip()}")
    return found


def case_whole_list() -> list[str]:
    """A list is judged item by item, and one refusal fails the whole."""
    code, output = run([case["dispatch"] for case in FIXTURES])
    lines = [line for line in output.splitlines() if not line.startswith("  ")]
    found = []
    if len(lines) != len(FIXTURES):
        found.append(f"{len(lines)} verdicts for {len(FIXTURES)} dispatches")
    if code != 1:
        found.append(f"a list holding refusals exited {code}")
    return found


CASES = [(f"{case['name']} (#225/AC-6)", lambda case=case: check(case)) for case in FIXTURES] + [
    ("a list of dispatches is judged item by item (#225/AC-6)", case_whole_list),
]


def main() -> int:
    failed = 0
    for name, case in CASES:
        problems = case()
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
