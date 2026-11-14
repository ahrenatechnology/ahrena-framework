"""The test harness shared by this plugin's hook tests.

Every hook here is tested the same way: a case is a throwaway tree of files,
the hook runs against it as a subprocess, and the case asserts on the exit
code and on fragments of the output. A detector that never accepts is as broken
as one that never rejects, so a case says which of the two it expects.

This module is imported by the `test-check-*.py` files beside it and runs
nothing on its own.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


def write(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def run(hook: Path, files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp), files)
        command = [sys.executable, "-B", str(hook), "."]
        result = subprocess.run(command, cwd=tmp, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    """What went wrong with this case, or nothing."""
    wanted = "pass" if ok else "fail"
    found = [] if ok == (code == 0) else [f"expected the hook to {wanted}, it did the other"]
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def report_failure(name: str, problems: list[str], output: str) -> None:
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")


def main(hook: Path, cases: list[Case]) -> int:
    failed = 0
    for name, files, expect, ok in cases:
        code, output = run(hook, files)
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            report_failure(name, problems, output)
        else:
            print(f"ok    {name}")
    print()
    if failed:
        print(f"{failed} of {len(cases)} cases failed.")
        return 1
    print(f"{len(cases)} cases passed.")
    return 0
