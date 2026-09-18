#!/usr/bin/env python3
"""Every gate must reject a bad input.

A gate nobody proved can fail is decoration. Each case below builds a broken
repository in a temp directory and asserts the gate rejects it, then asserts the
gate accepts the real repository.

Run: python3 scripts/gates_test.py
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def run(script: str, cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(cwd / "scripts" / script)],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def scaffold(tmp: pathlib.Path) -> pathlib.Path:
    """A minimal repository the gates accept."""
    for name in ("validate_edges.py", "verify_budgets.py", "artifact-budgets.json"):
        (tmp / "scripts").mkdir(exist_ok=True)
        shutil.copy(SCRIPTS / name, tmp / "scripts" / name)
    for path in ("rules/engineering/quality", "docs/engineering/quality"):
        (tmp / path).mkdir(parents=True, exist_ok=True)
    (tmp / "rules/engineering/quality/solid.md").write_text(
        "---\ntype: rule\nconsults:\n  - docs/engineering/quality/solid\n---\n# Rule\n"
    )
    (tmp / "docs/engineering/quality/solid.md").write_text("---\ntype: doc\n---\n# Doc\n")
    (tmp / "rules/engineering/quality/kiss.md").write_text("# Rule\n")
    (tmp / "rules/engineering/quality/yagni.md").write_text("# Rule\n")
    return tmp


CASES: list[tuple[str, str, str]] = []


def case(gate: str, name: str):
    def wrap(fn):
        CASES.append((gate, name, fn))
        return fn
    return wrap


@case("verify-edges", "rejects a typed edge whose target does not exist")
def _(tmp: pathlib.Path) -> None:
    (tmp / "rules/engineering/quality/kiss.md").write_text(
        "---\ntype: rule\nconsults:\n  - docs/engineering/quality/nonexistent\n---\n# Rule\n"
    )


@case("verify-edges", "rejects a markdown link whose target does not exist")
def _(tmp: pathlib.Path) -> None:
    (tmp / "rules/engineering/quality/kiss.md").write_text(
        "# Rule\n\nSee [the doc](../../../docs/engineering/quality/missing.md).\n"
    )


@case("verify-edges", "rejects a broken same-directory link")
def _(tmp: pathlib.Path) -> None:
    # The original pattern anchored on ./ or ../ and skipped sibling links
    # entirely, so renaming a sibling artifact stayed green.
    (tmp / "rules/engineering/quality/kiss.md").write_text(
        "# Rule\n\nSee [yagni](gone.md).\n"
    )


@case("verify-edges", "rejects an empty scan instead of reporting success")
def _(tmp: pathlib.Path) -> None:
    shutil.rmtree(tmp / "rules")
    shutil.rmtree(tmp / "docs")


@case("verify-budgets", "rejects an artifact over its frozen ceiling")
def _(tmp: pathlib.Path) -> None:
    path = tmp / "rules/engineering/quality/solid.md"
    manifest = json.loads((tmp / "scripts/artifact-budgets.json").read_text())
    ceiling = manifest["frozen"]["rules/engineering/quality/solid.md"]
    path.write_text("x" * (ceiling + 1))


@case("verify-budgets", "rejects an artifact over target with no frozen entry")
def _(tmp: pathlib.Path) -> None:
    manifest = json.loads((tmp / "scripts/artifact-budgets.json").read_text())
    target = manifest["targets"]["docs"]
    (tmp / "docs/engineering/quality/solid.md").write_text("x" * (target + 1))


@case("verify-budgets", "rejects an empty scan instead of reporting success")
def _(tmp: pathlib.Path) -> None:
    shutil.rmtree(tmp / "rules")
    shutil.rmtree(tmp / "docs")


SCRIPT_OF = {"verify-edges": "validate_edges.py", "verify-budgets": "verify_budgets.py"}


def main() -> int:
    failures: list[str] = []

    for gate, script in SCRIPT_OF.items():
        result = run(script, REPO)
        if result.returncode != 0:
            failures.append(f"{gate}: rejects the real repository\n{result.stderr}")

    for gate, name, mutate in CASES:
        with tempfile.TemporaryDirectory() as raw:
            tmp = scaffold(pathlib.Path(raw))
            mutate(tmp)
            result = run(SCRIPT_OF[gate], tmp)
            if result.returncode == 0:
                failures.append(f"{gate}: {name} — gate passed a bad input")

    total = len(CASES) + len(SCRIPT_OF)
    if failures:
        print(f"{len(failures)} of {total} check(s) failed:", file=sys.stderr)
        for item in failures:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"gates_test: {total} check(s) passed across {len(SCRIPT_OF)} gate(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
