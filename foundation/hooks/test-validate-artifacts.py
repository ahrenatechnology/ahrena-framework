#!/usr/bin/env python3
"""Tests for validate-artifacts.py.

A gate that has never rejected anything is a claim, not a guardrail. Each case
below builds a throwaway plugin tree, runs the gate against it, and asserts on
what comes back.

Usage:
    python3 foundation/hooks/test-validate-artifacts.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parent / "validate-artifacts.py"

MARKETPLACE = json.dumps(
    {"name": "fixture", "plugins": [{"name": "fixture-plugin", "source": {"path": "p"}}]}
)

GOOD_DOC = """---
id: reference
type: doc
clade: fixture
title: Reference
summary: A doc that passes.
---

# Reference
"""

GOOD_RULE = """---
id: bounded
type: rule
clade: fixture
title: Bounded
statement: Something is never done.
enforcement: judgment
references:
  - docs/reference.md
---

# Bounded
"""

GOOD_SKILL = """---
name: doing-things
description: Does things. Use when things need doing.
type: skill
clade: fixture
references:
  - rules/bounded.md
---

# Doing things
"""

GOOD_AGENT = """---
name: specialist
description: A specialist. Hand it specialist work.
type: agent
clade: fixture
role: thing-doer
references:
  - skills/doing-things/SKILL.md
---

# Specialist
"""

GOOD_COMMAND = """---
name: start
description: Starts the thing.
type: command
clade: fixture
references:
  - skills/doing-things/SKILL.md
---

# /start
"""

VALID_CORPUS = {
    "p/docs/reference.md": GOOD_DOC,
    "p/rules/bounded.md": GOOD_RULE,
    "p/skills/doing-things/SKILL.md": GOOD_SKILL,
    "p/agents/specialist.md": GOOD_AGENT,
    "p/commands/start.md": GOOD_COMMAND,
}


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> tuple:
    return (name, files, expect, ok)


CASES = [
    case("a valid corpus passes", VALID_CORPUS, ["5 artifact(s), no failures"], ok=True),
    case(
        "a missing required field fails",
        {"p/docs/reference.md": GOOD_DOC.replace("summary: A doc that passes.\n", "")},
        ["required field 'summary' is missing"],
    ),
    case(
        "an empty required field fails",
        {"p/docs/reference.md": GOOD_DOC.replace("title: Reference", "title:   ")},
        ["required field 'title'"],
    ),
    case(
        "an undeclared field on a rule fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace("title: Bounded", "title: Bounded\nowner: someone"),
        },
        ["'owner' is not a declared field"],
    ),
    case(
        "an undeclared field on a skill passes",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE,
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "type: skill", "allowed-tools: Read\ntype: skill"
            ),
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a type that disagrees with its directory fails",
        {"p/docs/reference.md": GOOD_DOC.replace("type: doc", "type: rule")},
        ["declares type 'rule' but sits in a doc directory"],
    ),
    case(
        "a type outside the five fails",
        {"p/docs/reference.md": GOOD_DOC.replace("type: doc", "type: playbook")},
        ["'playbook' is not one of the five types"],
    ),
    case(
        "a command referencing a doc fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/commands/start.md": GOOD_COMMAND.replace(
                "skills/doing-things/SKILL.md", "docs/reference.md"
            ),
        },
        ["a command may not reference a doc"],
    ),
    case(
        "a rule referencing a skill fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", ""),
            "p/rules/bounded.md": GOOD_RULE.replace(
                "docs/reference.md", "skills/doing-things/SKILL.md"
            ),
        },
        ["a rule may not reference a skill"],
    ),
    case(
        "a dangling reference fails",
        {"p/rules/bounded.md": GOOD_RULE.replace("docs/reference.md", "docs/missing.md")},
        ["reference 'docs/missing.md' does not exist"],
    ),
    case(
        "a reference that escapes the plugin fails",
        {"p/rules/bounded.md": GOOD_RULE.replace("docs/reference.md", "../other/docs/x.md")},
        ["escapes the plugin"],
    ),
    case(
        "a reference to a non-artifact fails",
        {
            "p/hooks/thing.py": "# not an artifact\n",
            "p/rules/bounded.md": GOOD_RULE.replace("docs/reference.md", "hooks/thing.py"),
        },
        ["is not an artifact"],
    ),
    case(
        "a nested skill fails",
        {"p/skills/python/doing-things/SKILL.md": GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", "")},
        ["exactly one level deep"],
    ),
    case(
        "a flat skill file fails",
        {"p/skills/doing-things.md": GOOD_SKILL},
        ["never a flat file"],
    ),
    case(
        "a skill named as a noun phrase fails",
        {
            "p/skills/artifact-creation/SKILL.md": GOOD_SKILL.replace(
                "name: doing-things", "name: artifact-creation"
            ).replace("references:\n  - rules/bounded.md\n", "")
        },
        ["is not in the gerund"],
    ),
    case(
        # A documented limit, not an oversight. The check is a suffix test, so a
        # noun that happens to end in 'ing' slips through. Stated in naming.md.
        "a noun ending in 'ing' slips past the gerund check",
        {
            "p/skills/thing-doer/SKILL.md": GOOD_SKILL.replace(
                "name: doing-things", "name: thing-doer"
            ).replace("references:\n  - rules/bounded.md\n", "")
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "an agent with no role fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", ""),
            "p/agents/specialist.md": GOOD_AGENT.replace("role: thing-doer\n", ""),
        },
        ["required field 'role' is missing"],
    ),
    case(
        "an agent role that is not kebab-case fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", ""),
            "p/agents/specialist.md": GOOD_AGENT.replace("role: thing-doer", "role: Thing Doer"),
        },
        ["role 'Thing Doer' is not kebab-case"],
    ),
    case(
        "an agent role that repeats its type fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", ""),
            "p/agents/specialist.md": GOOD_AGENT.replace("role: thing-doer", "role: agent-thing-doer"),
        },
        ["role 'agent-thing-doer' repeats its type"],
    ),
    case(
        # The point of the two-name rule: a persona handle is allowed on an
        # agent, and only on an agent.
        "an agent with a persona name and a noun-phrase role passes",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", ""),
            "p/agents/claudionor.md": GOOD_AGENT.replace("name: specialist", "name: claudionor"),
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a name that is not kebab-case fails",
        {"p/docs/Reference_Manual.md": GOOD_DOC.replace("id: reference", "id: Reference_Manual")},
        ["is not kebab-case"],
    ),
    case(
        "a name that repeats its type fails",
        {"p/docs/doc-reference.md": GOOD_DOC.replace("id: reference", "id: doc-reference")},
        ["repeats its type"],
    ),
    case(
        "a name that repeats its clade fails",
        {"p/docs/fixture-reference.md": GOOD_DOC.replace("id: reference", "id: fixture-reference")},
        ["repeats its clade"],
    ),
    case(
        "an id that disagrees with the filename fails",
        {"p/docs/reference.md": GOOD_DOC.replace("id: reference", "id: something-else")},
        ["but the filename says 'reference'"],
    ),
    case(
        "a nested file in a flat directory fails",
        {"p/docs/group/reference.md": GOOD_DOC},
        ["docs/ is flat"],
    ),
    case(
        "an overlong statement fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "statement: Something is never done.", "statement: " + "word " * 40
            ),
        },
        ["the limit is 160"],
    ),
    case(
        "enforcement: hook with no enforced-by fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace("enforcement: judgment", "enforcement: hook"),
        },
        ["enforced-by names no file"],
    ),
    case(
        "enforcement: hook pointing at nothing fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "enforcement: judgment", "enforcement: hook\nenforced-by: hooks/absent.py"
            ),
        },
        ["which does not exist"],
    ),
    case(
        "enforcement: judgment with an enforced-by fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "enforcement: judgment", "enforcement: judgment\nenforced-by: hooks/thing.py"
            ),
            "p/hooks/thing.py": "",
        },
        ["so enforced-by is not allowed"],
    ),
    case(
        "an unknown enforcement value fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace("enforcement: judgment", "enforcement: review"),
        },
        ["it is 'hook' or 'judgment'"],
    ),
    case(
        "a broken body link fails",
        {"p/docs/reference.md": GOOD_DOC + "\nSee [the thing](./absent.md).\n"},
        ["link target './absent.md' does not exist"],
    ),
    case(
        "a link inside a fence is not checked",
        {"p/docs/reference.md": GOOD_DOC + "\n```\n[the thing](./absent.md)\n```\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        "an external link is not checked",
        {"p/docs/reference.md": GOOD_DOC + "\n[the thing](https://example.com/x.md)\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        "a nested map in frontmatter fails",
        {"p/docs/reference.md": GOOD_DOC.replace("title: Reference", "title:\n  nested: value")},
        ["nested maps are not allowed"],
    ),
    case(
        "an inline collection in frontmatter fails",
        {"p/docs/reference.md": GOOD_DOC.replace("title: Reference", "title: [a, b]")},
        ["inline collections"],
    ),
    case(
        "a duplicated field fails",
        {"p/docs/reference.md": GOOD_DOC.replace("title: Reference", "title: Reference\ntitle: Again")},
        ["is declared twice"],
    ),
    case(
        "a missing frontmatter block fails",
        {"p/docs/reference.md": "# Reference\n"},
        ["does not open with a frontmatter block"],
    ),
    case(
        "an unclosed frontmatter block fails",
        {"p/docs/reference.md": "---\nid: reference\n\n# Reference\n"},
        ["never closed"],
    ),
    case(
        "a field name that is not kebab-case fails",
        {"p/docs/reference.md": GOOD_DOC.replace("title: Reference", "Title_Case: Reference")},
        ["is not a valid field name"],
    ),
]


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".claude-plugin").mkdir()
        (root / ".claude-plugin" / "marketplace.json").write_text(MARKETPLACE, encoding="utf-8")
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(GATE), str(root)], capture_output=True, text=True
        )
        return result.returncode, result.stdout + result.stderr


def main() -> int:
    failed = 0
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = []
        if ok and code != 0:
            problems.append("expected the gate to pass, it failed")
        if not ok and code == 0:
            problems.append("expected the gate to fail, it passed")
        for fragment in expect:
            if fragment not in output:
                problems.append(f"expected {fragment!r} in the output")
        if problems:
            failed += 1
            print(f"FAIL  {name}")
            for problem in problems:
                print(f"        {problem}")
            print("      --- gate output ---")
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
