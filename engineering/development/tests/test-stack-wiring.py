#!/usr/bin/env python3
"""The agency reaches the stack plugins: names resolve, the graph stays acyclic, CI runs every suite.

1. Every `ahrena-engineering-<stack>:<skill>` named by an artifact outside the
   stack plugins is a skill that exists (#290/AC-2).
2. `foundation/hooks/validate-artifacts.py` passes, and with it the acyclic
   plugin graph (#290/AC-2, #290/AC-4).
3. Each layer builder invokes the writing skill of every language it names in
   its review step, and reads the exposure rule, at a step numbered before the
   one that writes the red tests.
4. Every test suite in the tree has a step in `.github/workflows/validate.yml`.

Standard library only. Run from anywhere: paths resolve from this file.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STACKS = ("python", "go", "rust", "typescript", "terraform", "aws", "gcp", "azure")
NAMED = re.compile(r"ahrena-engineering-(" + "|".join(STACKS) + r"):(?:skills/)?([a-z0-9-]+)")
BUILDERS = {
    "engineering/backend/agents/hephaestus.md": ("python", "typescript", "go", "rust"),
    "engineering/data/agents/mnemosyne.md": ("python", "typescript", "go", "rust"),
    "engineering/frontend/agents/aglaia.md": ("typescript",),
}
# #290: fixtures and a template, not suites of their own.
NOT_SUITES = {
    "costs/runtime/test-support.py",
    "foundation/skills/writing-hooks/references/test-template.py",
}

results: list[tuple[str, bool]] = []


def check(ok: bool, label: str) -> None:
    results.append((label, ok))


def tracked(*patterns: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def test_named_stack_skills_exist() -> None:
    outside = [
        p for p in tracked("*.md", "*.json", "*.py")
        if not any(p.startswith(f"engineering/{s}/") for s in STACKS) and not p.startswith("artifacts/")
    ]
    missing = []
    for rel in outside:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for stack, name in NAMED.findall(text):
            if name in ("rules", "docs", "agents", "hooks"):
                continue
            if not (ROOT / "engineering" / stack / "skills" / name / "SKILL.md").is_file() and not (
                ROOT / "engineering" / stack / "agents" / f"{name}.md"
            ).is_file():
                missing.append(f"{rel}: ahrena-engineering-{stack}:{name}")
    check(not missing, "#290/AC-2 every stack skill or agent named outside its plugin exists" + (f": {missing}" if missing else ""))


def test_gate_passes() -> None:
    r = subprocess.run([sys.executable, "foundation/hooks/validate-artifacts.py"], cwd=ROOT, capture_output=True, text=True)
    check(r.returncode == 0, "#290/AC-2 validate-artifacts.py passes" + ("" if r.returncode == 0 else f": {r.stdout[-400:]}"))
    check("cycle" not in r.stdout, "#290/AC-4 the plugin graph has no cycle")


def _step_of(body: str, needle: str) -> int | None:
    for line in body.splitlines():
        found = re.match(r"^(\d+)\. ", line)
        if found and needle in line:
            return int(found.group(1))
    return None


def test_builders_load_the_discipline_first() -> None:
    for rel, languages in BUILDERS.items():
        body = (ROOT / rel).read_text(encoding="utf-8")
        red = _step_of(body, "tests red")
        check(red is not None, f"{rel}: has a step that writes the tests red")
        for lang in languages:
            step = _step_of(body, f"`ahrena-engineering-{lang}:writing-{lang}`")
            check(step is not None and red is not None and step < red, f"{rel}: writing-{lang} is invoked before the red tests")
            review = _step_of(body, f"`ahrena-engineering-{lang}:reviewing-{lang}`")
            check(review is not None and red is not None and review > red, f"{rel}: reviewing-{lang} still runs after the code")
        rule = _step_of(body, "`ahrena-engineering-security:rules/layer-exposure.md`")
        check(rule is not None and red is not None and rule < red, f"{rel}: the exposure rule is read before the red tests")


def test_ci_runs_every_suite() -> None:
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    suites = [p for p in tracked("*/test-*.py", "*_test.py") if p not in NOT_SUITES]
    absent = [p for p in suites if p not in workflow]
    check(not absent, "every test suite in the tree has a CI step" + (f": {absent}" if absent else ""))


if __name__ == "__main__":
    test_named_stack_skills_exist()
    test_gate_passes()
    test_builders_load_the_discipline_first()
    test_ci_runs_every_suite()
    failures = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
    print(f"\n{'all passed' if not failures else f'{len(failures)} failed'}")
    sys.exit(1 if failures else 0)
