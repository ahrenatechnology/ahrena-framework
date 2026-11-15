#!/usr/bin/env python3
"""Tests for validate-anthropic-skill.py.

Each case builds a throwaway skill folder, runs the checker against it and
asserts on the exit code and the output. The limits under test come from
foundation/docs/anthropic-skill-format.md, which cites Anthropic's own pages.

Each case in CASES is a tuple: case name, directory name, files, checker args,
fragments the output must hold, and whether the checker should pass.

Usage:
    python3 foundation/hooks/test-validate-anthropic-skill.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "validate-anthropic-skill.py"

DESCRIPTION = "Extracts text from PDF files. Use when the user mentions PDFs or document extraction."


def skill(name: str = "pdf-processing", description: str = DESCRIPTION, extra: str = "", body: str = "# PDF\n\nRun it.\n") -> str:
    return f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n{body}"


# #346/AC-3 each case below rejects an undeclared key, a malformed name or an over-long description, or passes a valid skill.
CASES = [
    ("minimal skill passes", "pdf-processing", {"SKILL.md": skill()}, [], [], True),
    (
        "optional portable fields pass",
        "pdf-processing",
        {
            "SKILL.md": skill(
                extra='license: Apache-2.0\ncompatibility: Requires Python 3\nmetadata:\n  author: example\n  version: "1.0"\nallowed-tools: Read Bash\n'
            )
        },
        [],
        [],
        True,
    ),
    (
        "layout with references, scripts and assets passes",
        "pdf-processing",
        {
            "SKILL.md": skill(body="# PDF\n\nSee [forms](references/FORMS.md). Run scripts/run.py.\n"),
            "references/FORMS.md": "# Forms\n",
            "scripts/run.py": "print('ok')\n",
            "assets/template.txt": "x\n",
        },
        [],
        [],
        True,
    ),
    (
        "undeclared key is rejected",
        "pdf-processing",
        {"SKILL.md": skill(extra="type: skill\n")},
        [],
        ["undeclared", "type"],
        False,
    ),
    (
        "framework field clade is rejected",
        "pdf-processing",
        {"SKILL.md": skill(extra="clade: foundation\n")},
        [],
        ["undeclared", "clade"],
        False,
    ),
    (
        "claude-code field is rejected under the portable profile",
        "pdf-processing",
        {"SKILL.md": skill(extra="disable-model-invocation: true\n")},
        [],
        ["undeclared", "disable-model-invocation"],
        False,
    ),
    (
        "claude-code field passes under the claude-code profile",
        "pdf-processing",
        {"SKILL.md": skill(extra="disable-model-invocation: true\nwhen_to_use: When asked.\n")},
        ["--profile", "claude-code"],
        [],
        True,
    ),
    (
        "undeclared key is rejected under the claude-code profile too",
        "pdf-processing",
        {"SKILL.md": skill(extra="clade: foundation\n")},
        ["--profile", "claude-code"],
        ["undeclared", "clade"],
        False,
    ),
    ("uppercase name is rejected", "PDF-Processing", {"SKILL.md": skill(name="PDF-Processing")}, [], ["name"], False),
    ("underscore name is rejected", "pdf_processing", {"SKILL.md": skill(name="pdf_processing")}, [], ["name"], False),
    ("leading hyphen name is rejected", "-pdf", {"SKILL.md": skill(name="-pdf")}, [], ["name"], False),
    ("trailing hyphen name is rejected", "pdf-", {"SKILL.md": skill(name="pdf-")}, [], ["name"], False),
    ("consecutive hyphens in name are rejected", "pdf--tools", {"SKILL.md": skill(name="pdf--tools")}, [], ["name"], False),
    (
        "name of 65 characters is rejected",
        "a" * 65,
        {"SKILL.md": skill(name="a" * 65)},
        [],
        ["64"],
        False,
    ),
    (
        "name of 64 characters passes",
        "a" * 64,
        {"SKILL.md": skill(name="a" * 64)},
        [],
        [],
        True,
    ),
    (
        "reserved word claude in name is rejected",
        "claude-tools",
        {"SKILL.md": skill(name="claude-tools")},
        [],
        ["reserved", "claude"],
        False,
    ),
    (
        "reserved word anthropic in name is rejected",
        "anthropic-helper",
        {"SKILL.md": skill(name="anthropic-helper")},
        [],
        ["reserved", "anthropic"],
        False,
    ),
    (
        "name that differs from the directory is rejected",
        "other-name",
        {"SKILL.md": skill(name="pdf-processing")},
        [],
        ["directory"],
        False,
    ),
    ("missing name is rejected", "pdf-processing", {"SKILL.md": f"---\ndescription: {DESCRIPTION}\n---\n\n# X\n"}, [], ["name"], False),
    (
        "description of 1025 characters is rejected",
        "pdf-processing",
        {"SKILL.md": skill(description="a" * 1025)},
        [],
        ["1024"],
        False,
    ),
    (
        "description of 1024 characters passes",
        "pdf-processing",
        {"SKILL.md": skill(description="a" * 1024)},
        [],
        [],
        True,
    ),
    ("missing description is rejected", "pdf-processing", {"SKILL.md": "---\nname: pdf-processing\n---\n\n# X\n"}, [], ["description"], False),
    (
        "empty description is rejected",
        "pdf-processing",
        {"SKILL.md": "---\nname: pdf-processing\ndescription:\n---\n\n# X\n"},
        [],
        ["description"],
        False,
    ),
    (
        "xml tag in description is rejected",
        "pdf-processing",
        {"SKILL.md": skill(description="Extracts <b>text</b> from PDFs. Use when asked.")},
        [],
        ["XML"],
        False,
    ),
    (
        "first-person description is rejected",
        "pdf-processing",
        {"SKILL.md": skill(description="I can extract text from PDFs. Use when asked.")},
        [],
        ["third person"],
        False,
    ),
    (
        "second-person description is rejected",
        "pdf-processing",
        {"SKILL.md": skill(description="You can use this to extract text from PDFs.")},
        [],
        ["third person"],
        False,
    ),
    (
        "compatibility of 501 characters is rejected",
        "pdf-processing",
        {"SKILL.md": skill(extra="compatibility: " + "a" * 501 + "\n")},
        [],
        ["500"],
        False,
    ),
    (
        "body over 500 lines is rejected",
        "pdf-processing",
        {"SKILL.md": skill(body="# X\n" + "line\n" * 500)},
        [],
        ["500 lines"],
        False,
    ),
    (
        "link to a missing file is rejected",
        "pdf-processing",
        {"SKILL.md": skill(body="# X\n\nSee [forms](references/FORMS.md).\n")},
        [],
        ["references/FORMS.md"],
        False,
    ),
    (
        "link that leaves the skill folder is rejected",
        "pdf-processing",
        {"SKILL.md": skill(body="# X\n\nSee [rules](../rules/x.md).\n")},
        [],
        ["outside"],
        False,
    ),
    (
        "backslash path in a link is rejected",
        "pdf-processing",
        {"SKILL.md": skill(body="# X\n\nSee [forms](references\\FORMS.md).\n"), "references/FORMS.md": "# F\n"},
        [],
        ["backslash"],
        False,
    ),
    (
        "folded first-person description is rejected",
        "pdf-processing",
        {"SKILL.md": "---\nname: pdf-processing\ndescription: >-\n  I extract text from PDFs.\n---\n\n# X\n"},
        [],
        ["third person"],
        False,
    ),
    ("missing SKILL.md is rejected", "pdf-processing", {"README.md": "x\n"}, [], ["SKILL.md"], False),
    ("no frontmatter is rejected", "pdf-processing", {"SKILL.md": "# X\n\nNo frontmatter.\n"}, [], ["frontmatter"], False),
]


def run(dirname: str, files: dict[str, str], args: list[str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / dirname
        for rel, text in files.items():
            path = folder / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        folder.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [sys.executable, str(CHECKER), *args, str(folder)],
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout + proc.stderr


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "foundation" / "docs" / "anthropic-skill-format.md"
TEMPLATE = ROOT / "foundation" / "skills" / "creating-artifacts" / "references" / "anthropic-skill.md"


def structure_failures() -> list[str]:
    """Checks on the files around the checker, one per criterion of #346."""
    failures = []
    # #346/AC-2 the page cites Anthropic's documentation for each limit it states.
    text = DOC.read_text(encoding="utf-8")
    for limit in ("64 characters", "1,024 characters", "500 characters", "500 lines"):
        if limit not in text:
            failures.append(f"the format doc does not state {limit}")
    for source in ("platform.claude.com/docs/en/agents-and-tools/agent-skills/overview", "code.claude.com/docs/en/skills"):
        if source not in text:
            failures.append(f"the format doc does not cite {source}")
    # #346/AC-1 #346/AC-5 the template, filled in, is a skill the checker accepts in the portable profile.
    body = TEMPLATE.read_text(encoding="utf-8").split("<!--", 1)[0]
    body = body.replace(body.split("\n")[1], "name: filled-skill").replace(body.split("\n")[2], f"description: {DESCRIPTION}")
    code, output = run("filled-skill", {"SKILL.md": body.replace("[the schema](references/schema.md)", "the schema")}, [])
    if code != 0:
        failures.append("the template, filled in, fails the checker: " + output.strip())
    # #346/AC-4 a framework skill still passes the foundation gate unchanged.
    gate = subprocess.run([sys.executable, str(ROOT / "foundation" / "hooks" / "validate-artifacts.py")], capture_output=True, text=True)
    if gate.returncode != 0:
        failures.append("validate-artifacts.py fails: " + gate.stdout.strip())
    return failures


def main() -> int:
    failed = 0
    for problem in structure_failures():
        failed += 1
        print(f"FAIL  structure: {problem}")
    for name, dirname, files, args, expect, ok in CASES:
        code, output = run(dirname, files, args)
        problems = []
        if ok and code != 0:
            problems.append("expected the checker to pass, it failed")
        if not ok and code == 0:
            problems.append("expected the checker to fail, it passed")
        for fragment in expect:
            if fragment not in output:
                problems.append(f"expected {fragment!r} in the output")
        if problems:
            failed += 1
            print(f"FAIL  {name}")
            for problem in problems:
                print(f"        {problem}")
            print("      --- checker output ---")
            for line in output.splitlines():
                print(f"      {line}")
        else:
            print(f"ok    {name}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
