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

## Where this stops

It does not reach the fixture next door.
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

## Conditions

1. The thing is not done.

## Where this stops

It does not reach the other thing.
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

## 1. Do the thing

Do it.

## When this skill does not apply

When the thing is already done.
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

## What this agent is for

Specialist work.

## Skills it orchestrates

Only `doing-things`.

## What it does not do

Anything else.
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

## What runs

`doing-things`.
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
        "a code block over 10 lines in a skill body fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            )
            + "\n```python\n"
            + "x = 1\n" * 11
            + "```\n"
        },
        ["code block is 11 lines", "the limit in a skill body is 10"],
    ),
    case(
        "a code block of exactly 10 lines passes",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            )
            + "\n```python\n"
            + "x = 1\n" * 10
            + "```\n"
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a code block over 10 lines in an agent body fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ),
            "p/agents/specialist.md": GOOD_AGENT + "\n```sh\n" + "echo hi\n" * 12 + "```\n",
        },
        ["code block is 12 lines", "the limit in an agent body is 10"],
    ),
    case(
        "a long code block in a doc passes; the rule does not reach docs",
        {"p/docs/reference.md": GOOD_DOC + "\n```python\n" + "x = 1\n" * 40 + "```\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        "a long code block in a rule passes; the rule does not reach rules",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE + "\n```python\n" + "x = 1\n" * 40 + "```\n",
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a references file no step names fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ),
            "p/skills/doing-things/references/orphan.md": "nobody opens this\n",
        },
        ["'references/orphan.md' is never named in SKILL.md"],
    ),
    case(
        "a scripts file no step names fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ),
            "p/skills/doing-things/scripts/orphan.py": "# nobody runs this\n",
        },
        ["'scripts/orphan.py' is never named in SKILL.md"],
    ),
    case(
        "a references file the body names passes",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            )
            + "\nStep 1 reads `references/material.md`.\n",
            "p/skills/doing-things/references/material.md": "read me\n",
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a leftover marker in a body fails",
        {"p/docs/reference.md": GOOD_DOC + "\nTODO: finish this section.\n"},
        ["body still carries the marker 'TODO'"],
    ),
    case(
        "a leftover marker in a frontmatter field fails",
        {"p/docs/reference.md": GOOD_DOC.replace("summary: A doc that passes.", "summary: TBD")},
        ["field 'summary' still carries the marker 'TBD'"],
    ),
    case(
        "an unfilled template placeholder in a body fails",
        {"p/docs/reference.md": GOOD_DOC + "\nThis explains <the concept>.\n"},
        ["body still carries the template placeholder '<the concept>'"],
    ),
    case(
        "an unfilled template placeholder in a frontmatter field fails",
        {
            "p/docs/reference.md": GOOD_DOC.replace(
                "title: Reference", "title: <noun phrase, title case>"
            )
        },
        ["field 'title' still carries the template placeholder"],
    ),
    case(
        # <plugin> and <name> in a command line are what the reader substitutes,
        # not what the author forgot. All 18 angle brackets in the real corpus
        # are this, so the scan skips code.
        "a placeholder inside a code fence passes",
        {"p/docs/reference.md": GOOD_DOC + "\n```sh\npython3 <plugin>/hooks/x.py\n```\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        "a marker inside inline code passes",
        {"p/docs/reference.md": GOOD_DOC + "\nA leftover `TODO` passes the field check.\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        "a rule with no Conditions section fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "## Conditions\n\n1. The thing is not done.\n\n", ""
            ),
        },
        ["'## Conditions' is missing"],
    ),
    case(
        "a rule with no Where this stops section fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "## Where this stops\n\nIt does not reach the other thing.\n", ""
            ),
        },
        ["'## Where this stops' is missing"],
    ),
    case(
        "a doc with no Where this stops section fails",
        {
            "p/docs/reference.md": GOOD_DOC.replace(
                "## Where this stops\n\nIt does not reach the fixture next door.\n", ""
            )
        },
        ["'## Where this stops' is missing"],
    ),
    case(
        "a skill with no When this skill does not apply section fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ).replace("## When this skill does not apply\n\nWhen the thing is already done.\n", "")
        },
        ["'## When this skill does not apply' is missing"],
    ),
    case(
        "a skill with no numbered step fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ).replace("## 1. Do the thing", "## Doing it")
        },
        ["no numbered step"],
    ),
    case(
        "an agent missing a required section fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ),
            "p/agents/specialist.md": GOOD_AGENT.replace(
                "## What it does not do\n\nAnything else.\n", ""
            ),
        },
        ["'## What it does not do' is missing"],
    ),
    case(
        "a command with no What runs section fails",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ),
            "p/commands/start.md": GOOD_COMMAND.replace("## What runs\n\n`doing-things`.\n", ""),
        },
        ["'## What runs' is missing"],
    ),
    case(
        "a heading inside a code fence does not satisfy a required section",
        {
            "p/docs/reference.md": GOOD_DOC.replace(
                "## Where this stops\n\nIt does not reach the fixture next door.\n",
                "```markdown\n## Where this stops\n```\n",
            )
        },
        ["'## Where this stops' is missing"],
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
    case(
        "a line that is not a 'key: value' pair fails, on its own line number",
        {"p/docs/reference.md": GOOD_DOC.replace("title: Reference", "title: Reference\njust a line")},
        ["line 6: not a 'key: value' pair"],
    ),
    case(
        # A blank line closes the list above it, so what follows has no key.
        "a list item after a blank line fails, on its own line number",
        {
            "p/docs/reference.md": GOOD_DOC.replace(
                "summary: A doc that passes.",
                "references:\n  - docs/reference.md\n\n  - docs/other.md\nsummary: A doc that passes.",
            )
        },
        ["line 9: list item with no key above it"],
    ),
    case(
        "a leftover marker in a list field fails",
        {
            "p/docs/reference.md": GOOD_DOC.replace(
                "summary: A doc that passes.",
                "summary: A doc that passes.\nreferences:\n  - docs/TODO-later.md",
            )
        },
        ["field 'references' still carries the marker 'TODO'"],
    ),
    case(
        # Markers win the tie, so the field is reported once rather than twice.
        "a field carrying both a marker and a placeholder is reported once",
        {"p/docs/reference.md": GOOD_DOC.replace("summary: A doc that passes.", "summary: TODO <fill this in>")},
        ["1 failure(s)", "field 'summary' still carries the marker 'TODO'"],
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
