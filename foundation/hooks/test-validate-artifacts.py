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
skills:
  - fixture-plugin:doing-things
---

# Specialist

## What this agent is for

Specialist work.

## Before you start

Before doing anything else, invoke `fixture-plugin:doing-things` with the Skill tool, so its procedure is in your context.

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


# A case that needs a second plugin supplies its own marketplace under the same
# path, which the runner writes after the default one.
TWO_PLUGINS = json.dumps(
    {
        "name": "fixture",
        "plugins": [
            {"name": "fixture-plugin", "source": {"path": "p"}},
            {"name": "other-plugin", "source": {"path": "q"}},
        ],
    }
)
MARKETPLACE_PATH = ".claude-plugin/marketplace.json"

# A fork carries its parent's plugins without cataloguing them, so a plugin can
# be named by its own manifest alone.
ONE_PLUGIN = json.dumps({"name": "fixture", "plugins": [{"name": "fixture-plugin", "source": {"path": "p"}}]})

# The engineering plugins sit one level down, as engineering/fundamentals and
# engineering/python, so a source.path is a path and not a directory name.
NESTED_PLUGINS = json.dumps(
    {
        "name": "fixture",
        "plugins": [
            {"name": "fixture-plugin", "source": {"path": "group/p"}},
            {"name": "other-plugin", "source": {"path": "group/q"}},
        ],
    }
)

NEIGHBOUR_DOC = GOOD_DOC.replace("id: reference", "id: neighbour").replace(
    "title: Reference", "title: Neighbour"
)
NEIGHBOUR_DOC_TO_RULE = NEIGHBOUR_DOC.replace(
    "summary: A doc that passes.",
    "summary: A doc that passes.\nreferences:\n  - fixture-plugin:rules/bounded.md",
)


# #252: each fixture below varies one of the two load paths, `skills` or `## Before you start`.
UNWIRED_AGENT = GOOD_AGENT.replace("skills:\n  - fixture-plugin:doing-things\n", "")
NO_LOAD_SECTION = (
    "## Before you start\n\n"
    "Before doing anything else, invoke `fixture-plugin:doing-things` with the Skill tool, so its procedure is in your context.\n\n"
)
SECOND_SKILL = GOOD_SKILL.replace("name: doing-things", "name: checking-things").replace(
    "references:\n  - rules/bounded.md\n", ""
)
TWO_SKILL_AGENT = GOOD_AGENT.replace(
    "  - skills/doing-things/SKILL.md\n",
    "  - skills/doing-things/SKILL.md\n  - skills/checking-things/SKILL.md\n",
)


# #252/AC-3 #252/AC-7 — An agent that has `## Procedure` is held to the body
# skeleton instead of the pre-#252 agent row, so the fixtures below drop or
# break one part of a skeleton agent that otherwise passes.
SKELETON_OUTPUT = (
    "## Output\n\n"
    "```text\nDONE\nexists: the thing, done\nleft: none\n```\n\n"
    "```text\nBLOCKED\nblocker: the missing input\nneeds: what to relaunch with\n```\n\n"
    "```text\nNEEDS_APPROVAL\napprove: the plan\nrecommendation: approve it\n"
    "resume: relaunch with approval; the run resumes at step 2\n```\n\n"
)
SKELETON_EXAMPLE = (
    "## Example\n\n"
    "<example>\nInput: a thing to do.\n\n```text\nDONE\nexists: the thing, done\nleft: none\n```\n"
    "</example>\n"
)
SKELETON_AGENT = GOOD_AGENT.replace(
    NO_LOAD_SECTION,
    "## Before you start\n\nBefore doing anything else, invoke each of these with the Skill tool, so its "
    "procedure is in your context: `fixture-plugin:doing-things`.\n\nLoading a skill is not running it: "
    "run each one only at the step of `## Procedure` that names it.\n\n",
).replace(
    "## Skills it orchestrates\n\nOnly `doing-things`.\n\n",
    "## Inputs\n\n- `thing`: the thing to do. Missing, return BLOCKED naming it.\n"
    "- `approval`: the person's answer to a NEEDS_APPROVAL. Present, resume at step 2.\n\n"
    "## Procedure\n\n1. Plan the thing. Return NEEDS_APPROVAL with the plan.\n"
    "2. Do the thing with `doing-things`. Output: the thing, done.\n\n"
    "## Delegation\n\nNone.\n\n"
    "## Done when\n\nDo not return before the thing is done.\n\n"
    "## When blocked\n\nThe thing is missing. Return BLOCKED naming it.\n\n"
    + SKELETON_OUTPUT,
) + "\n" + SKELETON_EXAMPLE


def wired_agent(preload: list[str], section: str) -> str:
    """The fixture agent with its `skills` list and its load section replaced."""
    lines = "".join(f"  - {name}\n" for name in preload)
    return (
        GOOD_AGENT.replace("skills:\n  - fixture-plugin:doing-things\n", f"skills:\n{lines}")
        .replace(NO_LOAD_SECTION, section)
    )


ATHENA_BEFORE_252 = (Path(__file__).resolve().parent / "fixtures" / "athena-before-252.md").read_text(
    encoding="utf-8"
)

# #252/AC-11: stubs of every artifact athena.md (e9f4342) points at, so only its wiring fails.
ATHENA_PLUGINS = {
    "ahrena-engineering-delivery": "d",
    "ahrena-engineering-fundamentals": "f",
    "ahrena-contributing": "c",
    "ahrena-engineering-frontend": "fe",
    "ahrena-engineering-backend": "be",
    "ahrena-engineering-data": "da",
    "ahrena-engineering-quality": "qa",
}
STUB_SKILL = GOOD_SKILL.replace("references:\n  - rules/bounded.md\n", "")
STUB_AGENT = UNWIRED_AGENT.replace("references:\n  - skills/doing-things/SKILL.md\n", "").replace(
    NO_LOAD_SECTION, ""
)


def athena_tree() -> dict[str, str]:
    """A marketplace in which every reference of the pre-#252 athena.md resolves."""
    tree = {
        MARKETPLACE_PATH: json.dumps(
            {
                "name": "fixture",
                "plugins": [{"name": n, "source": {"path": d}} for n, d in ATHENA_PLUGINS.items()],
            }
        ),
        "d/agents/athena.md": ATHENA_BEFORE_252,
        "d/docs/clef-decision-gate.md": GOOD_DOC.replace("id: reference", "id: clef-decision-gate"),
    }
    skills = {
        "d": ("orchestrating-delivery", "routing-concern"),
        "f": ("reading-the-component-map",),
        "c": ("opening-issues", "planning-changes", "stacking-pull-requests"),
    }
    for directory, names in skills.items():
        for name in names:
            tree[f"{directory}/skills/{name}/SKILL.md"] = STUB_SKILL.replace("name: doing-things", f"name: {name}")
    agents = {"fe": ("iris",), "be": ("apollo",), "da": ("clio",), "qa": ("argos", "erodos")}
    for directory, names in agents.items():
        for name in names:
            tree[f"{directory}/agents/{name}.md"] = STUB_AGENT.replace("name: specialist", f"name: {name}")
    return tree


def qualified(ref: str) -> str:
    """The fixture rule, with its one reference replaced by `ref`."""
    return GOOD_RULE.replace("  - docs/reference.md", f"  - {ref}")


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
    # Red on a case-insensitive filesystem before the glob in `collect` was
    # fixed, and green on a case-sensitive one either way: there, the literal
    # `rglob("SKILL.md")` never returned `skill.md` in the first place. So this
    # case has teeth only on the macOS leg of the matrix in validate.yml, which
    # is why that leg exists. No arrangement of files can reproduce the defect
    # on Linux, because the defect is the filesystem's answer and not the
    # tree's shape.
    case(
        "a lowercase skill.md under references is a template, not a nested skill",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE,
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "Do it.", "Do it, the way references/skill.md lays out."
            ),
            "p/skills/doing-things/references/skill.md": "# The template a step hands out\n",
        },
        ["no failures"],
        ok=True,
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
        "enforcement: hook with enforced-in: forge passes",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "enforcement: judgment",
                "enforcement: hook\nenforced-by: hooks/thing.py\nenforced-in: forge",
            ),
            "p/hooks/thing.py": "",
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "enforcement: hook with enforced-in: tree passes",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "enforcement: judgment",
                "enforcement: hook\nenforced-by: hooks/thing.py\nenforced-in: tree",
            ),
            "p/hooks/thing.py": "",
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "an unknown enforced-in value fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "enforcement: judgment",
                "enforcement: hook\nenforced-by: hooks/thing.py\nenforced-in: cloud",
            ),
            "p/hooks/thing.py": "",
        },
        ["it is 'tree' or 'forge'"],
    ),
    case(
        "enforcement: judgment with an enforced-in fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": GOOD_RULE.replace(
                "enforcement: judgment", "enforcement: judgment\nenforced-in: forge"
            ),
        },
        ["so enforced-in is not allowed"],
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
    # --- brace placeholders ------------------------------------------------
    # #200/#202 made `{ ... }` the placeholder for `description:`, because
    # claude.ai strips `<`/`>` from the field it stores. A copied template that
    # was never filled now leaves a brace placeholder, so the scan reads for one.
    case(
        # #205/AC-1 — A brace placeholder in a frontmatter value opens with `{`,
        # which frontmatter.md already rejects as an inline collection, before
        # the completeness scan runs. So the field side needs no brace scan: the
        # copied `description: { what it does… }` from the template is blocked.
        "a brace placeholder in a frontmatter value is rejected as an inline collection",
        {
            "p/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "description: Does things. Use when things need doing.",
                "description: { what it does, then when to use it }",
            ).replace("references:\n  - rules/bounded.md\n", "")
        },
        ["inline collections and block scalars are not allowed"],
    ),
    case(
        # #205/AC-2 — The genuine gap: a brace placeholder on a body line, which
        # no scan caught before, unlike its angle-bracket sibling.
        "an unfilled brace placeholder on a body line fails",
        {"p/docs/reference.md": GOOD_DOC + "\n{ describe the concept here }\n"},
        ["body still carries the template placeholder '{ describe the concept here }'"],
    ),
    case(
        # #205/AC-2 — The anchors tolerate surrounding whitespace, as a copied
        # template line often carries.
        "an indented brace-only body line fails",
        {"p/docs/reference.md": GOOD_DOC + "\n   { describe the concept here }   \n"},
        ["body still carries the template placeholder '{ describe the concept here }'"],
    ),
    case(
        # #205/AC-3 — Empty braces are not a placeholder; the interior must hold
        # something for a line to read as unfilled.
        "an empty brace on a body line passes",
        {"p/docs/reference.md": GOOD_DOC + "\n{ }\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        # #205/AC-3 — Braces are legal in prose, unlike angle brackets, so only a
        # line that is nothing but a brace placeholder is a leftover.
        "a brace in the middle of a line of prose passes",
        {"p/docs/reference.md": GOOD_DOC + "\nThe set { a, b } is closed under the operation.\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        # #205/AC-3 — The opening-issues title convention; a double brace is not a
        # leftover.
        "a double-brace placeholder on its own line passes",
        {"p/docs/reference.md": GOOD_DOC + "\n{{ brief summary }}\n"},
        ["no failures"],
        ok=True,
    ),
    case(
        # #205/AC-3
        "a brace placeholder inside a code fence passes",
        {"p/docs/reference.md": GOOD_DOC + '\n```json\n{ "key": "value" }\n```\n'},
        ["no failures"],
        ok=True,
    ),
    case(
        # #205/AC-3
        "a brace placeholder inside inline code passes",
        {"p/docs/reference.md": GOOD_DOC + "\n`{ fill me in }`\n"},
        ["no failures"],
        ok=True,
    ),
    # --- references across plugins -----------------------------------------
    case(
        "a qualified reference into another plugin passes",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/docs/neighbour.md": NEIGHBOUR_DOC,
            "p/rules/bounded.md": qualified("other-plugin:docs/neighbour.md"),
        },
        ["2 artifact(s), no failures"],
        ok=True,
    ),
    case(
        "a qualified reference naming a plugin the marketplace does not list fails",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/docs/neighbour.md": NEIGHBOUR_DOC,
            "p/rules/bounded.md": qualified("ghost-plugin:docs/neighbour.md"),
        },
        ["names 'ghost-plugin', which is not a plugin in the marketplace"],
    ),
    case(
        "a qualified reference into one's own plugin fails",
        {
            "p/docs/reference.md": GOOD_DOC,
            "p/rules/bounded.md": qualified("fixture-plugin:docs/reference.md"),
        },
        ["is inside this plugin; drop the 'fixture-plugin:' prefix"],
    ),
    case(
        "the matrix applies across plugins too",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/skills/doing-things/SKILL.md": GOOD_SKILL.replace(
                "references:\n  - rules/bounded.md\n", ""
            ),
            "p/rules/bounded.md": qualified("other-plugin:skills/doing-things/SKILL.md"),
        },
        ["a rule may not reference a skill"],
    ),
    case(
        "a qualified reference to a path that is not there fails",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/docs/neighbour.md": NEIGHBOUR_DOC,
            "p/rules/bounded.md": qualified("other-plugin:docs/absent.md"),
        },
        ["reference 'other-plugin:docs/absent.md' does not exist"],
    ),
    case(
        "an unqualified reference does not reach into another plugin",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/docs/neighbour.md": NEIGHBOUR_DOC,
            "p/rules/bounded.md": qualified("docs/neighbour.md"),
        },
        ["reference 'docs/neighbour.md' does not exist"],
    ),
    # #121/AC-1
    case(
        "a plugin whose source.path is nested below a parent directory resolves",
        {
            MARKETPLACE_PATH: NESTED_PLUGINS,
            "group/p/docs/reference.md": GOOD_DOC,
            "group/p/rules/bounded.md": GOOD_RULE,
            "group/q/docs/neighbour.md": NEIGHBOUR_DOC,
        },
        ["3 artifact(s), no failures"],
        ok=True,
    ),
    # #121/AC-2
    case(
        "a qualified reference between two plugins nested under one parent passes",
        {
            MARKETPLACE_PATH: NESTED_PLUGINS,
            "group/q/docs/neighbour.md": NEIGHBOUR_DOC,
            "group/p/rules/bounded.md": qualified("other-plugin:docs/neighbour.md"),
        },
        ["2 artifact(s), no failures"],
        ok=True,
    ),
    case(
        "two plugins that reference each other fail as a cycle",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/docs/neighbour.md": NEIGHBOUR_DOC_TO_RULE,
            "p/rules/bounded.md": qualified("other-plugin:docs/neighbour.md"),
        },
        ["plugins depend in a cycle", "fixture-plugin -> other-plugin -> fixture-plugin"],
    ),
    # #159/AC-1
    case(
        "a plugin hosted in another repository is catalogued, not validated here",
        {
            MARKETPLACE_PATH: json.dumps(
                {
                    "name": "fixture",
                    "plugins": [
                        {"name": "fixture-plugin", "source": {"path": "p"}},
                        {
                            "name": "external-plugin",
                            "source": {
                                "source": "git-subdir",
                                "url": "https://example.com/other.git",
                                "path": "elsewhere",
                            },
                        },
                    ],
                }
            ),
            **VALID_CORPUS,
        },
        ["5 artifact(s), no failures"],
        ok=True,
    ),
    # #159/AC-2
    case(
        "an entry with no directory and no source url still fails",
        {
            MARKETPLACE_PATH: json.dumps(
                {
                    "name": "fixture",
                    "plugins": [{"name": "fixture-plugin", "source": {"path": "missing"}}],
                }
            ),
        },
        ["points at 'missing', which is not a directory"],
    ),
    # #159/AC-6
    case(
        "a plugin the tree carries but the marketplace does not list resolves a qualified reference",
        {
            MARKETPLACE_PATH: ONE_PLUGIN,
            "q/.claude-plugin/plugin.json": json.dumps({"name": "other-plugin"}),
            "q/docs/neighbour.md": NEIGHBOUR_DOC,
            "p/rules/bounded.md": qualified("other-plugin:docs/neighbour.md"),
        },
        ["2 artifact(s), no failures"],
        ok=True,
    ),
    # ---------------------------------------------------------------------------
    # #252/AC-1
    case(
        "an agent that references a skill but declares no skills fails",
        {**VALID_CORPUS, "p/agents/specialist.md": UNWIRED_AGENT},
        ["agents/specialist.md", "condition 8: skills does not list 'fixture-plugin:doing-things'"],
    ),
    # #252/AC-1 #252/AC-2
    case(
        "an agent whose skills omit one referenced skill fails, naming the condition",
        {
            **VALID_CORPUS,
            "p/skills/checking-things/SKILL.md": SECOND_SKILL,
            "p/agents/specialist.md": TWO_SKILL_AGENT.replace(
                NO_LOAD_SECTION,
                "## Before you start\n\nBefore doing anything else, invoke each of these with the Skill tool, so its procedure is in your context: "
                "`fixture-plugin:doing-things`, `fixture-plugin:checking-things`.\n\n",
            ),
        },
        ["1 failure(s)", "[frontmatter] condition 8: skills does not list 'fixture-plugin:checking-things'"],
    ),
    # #252/AC-1
    case(
        "a skills list given as a scalar fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": GOOD_AGENT.replace(
                "skills:\n  - fixture-plugin:doing-things\n", "skills: fixture-plugin:doing-things\n"
            ),
        },
        ["condition 8: skills is a list, even with one entry"],
    ),
    # #252/AC-1
    case(
        "a skills entry that does not resolve to a skill fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": wired_agent(
                ["fixture-plugin:doing-things", "fixture-plugin:absent-thing"], NO_LOAD_SECTION
            ),
        },
        ["1 failure(s)", "condition 9: skills entry 'fixture-plugin:absent-thing' does not resolve"],
    ),
    # #252/AC-1
    case(
        "a skills entry naming a plugin the marketplace does not list fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": wired_agent(
                ["fixture-plugin:doing-things", "ghost-plugin:doing-things"], NO_LOAD_SECTION
            ),
        },
        ["condition 9: skills entry 'ghost-plugin:doing-things' does not resolve"],
    ),
    # #252/AC-1
    case(
        "a skills entry that is not plugin-qualified fails",
        {**VALID_CORPUS, "p/agents/specialist.md": wired_agent(["doing-things"], NO_LOAD_SECTION)},
        [
            "condition 9: skills entry 'doing-things' is not plugin-qualified",
            "condition 8: skills does not list 'fixture-plugin:doing-things'",
        ],
    ),
    # #252/AC-1
    case(
        "an agent with no Before you start section fails",
        {**VALID_CORPUS, "p/agents/specialist.md": GOOD_AGENT.replace(NO_LOAD_SECTION, "")},
        ["1 failure(s)", "condition 10: '## Before you start' is missing"],
    ),
    # #252/AC-1
    case(
        "a Before you start section that omits a referenced skill fails",
        {
            **VALID_CORPUS,
            "p/skills/checking-things/SKILL.md": SECOND_SKILL,
            "p/agents/specialist.md": TWO_SKILL_AGENT.replace(
                "  - fixture-plugin:doing-things\n",
                "  - fixture-plugin:doing-things\n  - fixture-plugin:checking-things\n",
            ),
        },
        ["1 failure(s)", "condition 10: '## Before you start' does not name `fixture-plugin:checking-things`"],
    ),
    # #252/AC-1
    case(
        "a Before you start section that never names the Skill tool fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": GOOD_AGENT.replace(" with the Skill tool,", ","),
        },
        ["1 failure(s)", "condition 10: '## Before you start' does not tell the executor to use the Skill tool"],
    ),
    # #252/AC-1
    case(
        "a Before you start section inside a code fence does not count",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": GOOD_AGENT.replace(
                NO_LOAD_SECTION, "```markdown\n" + NO_LOAD_SECTION + "```\n\n"
            ),
        },
        ["condition 10: '## Before you start' is missing"],
    ),
    # #252/AC-1
    case(
        "an agent wired to a skill in another plugin passes",
        {
            MARKETPLACE_PATH: TWO_PLUGINS,
            "q/skills/doing-things/SKILL.md": STUB_SKILL,
            "p/agents/specialist.md": GOOD_AGENT.replace(
                "  - skills/doing-things/SKILL.md\n", "  - other-plugin:skills/doing-things/SKILL.md\n"
            ).replace("fixture-plugin:doing-things", "other-plugin:doing-things"),
        },
        ["2 artifact(s), no failures"],
        ok=True,
    ),
    # #252/AC-1
    case(
        "an agent that references no skill needs neither skills nor the section",
        {
            "p/agents/specialist.md": STUB_AGENT,
        },
        ["1 artifact(s), no failures"],
        ok=True,
    ),
    # #252/AC-11
    case(
        "the pre-#252 athena.md fails the wiring check",
        athena_tree(),
        [
            "agents/athena.md",
            "condition 8: skills does not list 'ahrena-engineering-delivery:orchestrating-delivery'",
            "condition 8: skills does not list 'ahrena-contributing:stacking-pull-requests'",
            "condition 10: '## Before you start' is missing",
            "7 failure(s)",
        ],
    ),
    # #252/AC-11
    case(
        "the pre-#252 athena.md fixture tree is otherwise clean",
        {
            **athena_tree(),
            "d/agents/athena.md": ATHENA_BEFORE_252.replace(
                "---\n\n# Athena",
                "skills:\n"
                + "".join(
                    f"  - {n}\n"
                    for n in (
                        "ahrena-engineering-delivery:orchestrating-delivery",
                        "ahrena-engineering-delivery:routing-concern",
                        "ahrena-engineering-fundamentals:reading-the-component-map",
                        "ahrena-contributing:opening-issues",
                        "ahrena-contributing:planning-changes",
                        "ahrena-contributing:stacking-pull-requests",
                    )
                )
                + "---\n\n# Athena",
                1,
            ).replace(
                "\n## Skills it orchestrates",
                "\n## Before you start\n\nBefore doing anything else, invoke each of these with the Skill tool, so its procedure is in your context: "
                "`ahrena-engineering-delivery:orchestrating-delivery`, `ahrena-engineering-delivery:routing-concern`, "
                "`ahrena-engineering-fundamentals:reading-the-component-map`, `ahrena-contributing:opening-issues`, "
                "`ahrena-contributing:planning-changes`, `ahrena-contributing:stacking-pull-requests`.\n\n"
                "## Skills it orchestrates",
                1,
            ),
        },
        ["no failures"],
        ok=True,
    ),
    # --- the agent body skeleton -------------------------------------------
    # #252/AC-3 #252/AC-7
    case(
        "a skeleton agent passes without the pre-#252 Skills it orchestrates section",
        {**VALID_CORPUS, "p/agents/specialist.md": SKELETON_AGENT},
        ["5 artifact(s), no failures"],
        ok=True,
    ),
    # #252/AC-3
    case(
        "a skeleton agent missing Output fails",
        {**VALID_CORPUS, "p/agents/specialist.md": SKELETON_AGENT.replace(SKELETON_OUTPUT, "")},
        ["1 failure(s)", "'## Output' is missing"],
    ),
    # #252/AC-3
    case(
        "a skeleton agent missing Done when fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace(
                "## Done when\n\nDo not return before the thing is done.\n\n", ""
            ),
        },
        ["1 failure(s)", "'## Done when' is missing"],
    ),
    # #252/AC-3
    case(
        "a skeleton agent missing Example fails",
        {**VALID_CORPUS, "p/agents/specialist.md": SKELETON_AGENT.replace(SKELETON_EXAMPLE, "")},
        ["1 failure(s)", "'## Example' is missing"],
    ),
    # #252/AC-3
    case(
        "a skeleton agent with its sections out of order fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace(SKELETON_OUTPUT, "").replace(
                "## Inputs\n", SKELETON_OUTPUT + "## Inputs\n"
            ),
        },
        ["1 failure(s)", "condition 5: the skeleton sections are out of order"],
    ),
    # #252/AC-3
    case(
        "an Example section without example tags fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace("<example>\n", "").replace("</example>\n", ""),
        },
        ["1 failure(s)", "condition 7: '## Example' holds no <example> ... </example> pair"],
    ),
    # #252/AC-3
    case(
        "an example tag in inline code does not count",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace("<example>\n", "`<example>`\n").replace(
                "</example>\n", "`</example>`\n"
            ),
        },
        ["condition 7: '## Example' holds no"],
    ),
    # #252/AC-3
    case(
        "the example-tag exemption is that tag alone",
        {**VALID_CORPUS, "p/agents/specialist.md": SKELETON_AGENT.replace("<example>\n", "<examples>\n", 1)},
        ["body still carries the template placeholder '<examples>'"],
    ),
    # #252/AC-3 #252/AC-7
    case(
        "an Output template that does not open with a status fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace(
                "## Output\n\n```text\nDONE\n", "## Output\n\n```text\nFinished\n"
            ),
        },
        ["1 failure(s)", "condition 6: an '## Output' template does not open with DONE, BLOCKED or NEEDS_APPROVAL"],
    ),
    # #252/AC-3
    case(
        "an Output section with no fenced template fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace(
                SKELETON_OUTPUT, "## Output\n\nThe thing, done.\n\n"
            ),
        },
        ["1 failure(s)", "condition 6: '## Output' has no fenced template"],
    ),
    # #252/AC-7
    case(
        "a NEEDS_APPROVAL template that does not say how the run resumes fails",
        {
            **VALID_CORPUS,
            "p/agents/specialist.md": SKELETON_AGENT.replace(
                "resume: relaunch with approval; the run resumes at step 2\n", ""
            ),
        },
        ["1 failure(s)", "condition 6: the NEEDS_APPROVAL template has no 'resume:' field"],
    ),
    # #252/AC-7
    case(
        "a NEEDS_APPROVAL template that names nothing to approve fails",
        {**VALID_CORPUS, "p/agents/specialist.md": SKELETON_AGENT.replace("approve: the plan\n", "")},
        ["1 failure(s)", "condition 6: the NEEDS_APPROVAL template has no 'approve:' field"],
    ),
    # #159/AC-6
    case(
        "a plugin the tree carries but the marketplace does not list is still validated",
        {
            MARKETPLACE_PATH: ONE_PLUGIN,
            "q/.claude-plugin/plugin.json": json.dumps({"name": "other-plugin"}),
            "q/docs/neighbour.md": NEIGHBOUR_DOC.replace("summary: A doc that passes.", "summary: TODO <fill this in>"),
            **VALID_CORPUS,
        },
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
