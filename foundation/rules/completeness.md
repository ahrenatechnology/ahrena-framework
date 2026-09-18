---
id: completeness
type: rule
clade: foundation
title: Artifact completeness
statement: An artifact carries no unfilled marker or placeholder, and every section its type requires.
enforcement: hook
enforced-by: hooks/validate-artifacts.py
references:
  - docs/artifact-model.md
---

# Artifact completeness

## Nothing left unfilled

No frontmatter field and no line of prose carries `TODO`, `TBD`, `FIXME`, `XXX`, or an unreplaced template placeholder in angle brackets.

The scan skips fenced blocks and inline code. `<plugin>` on a command line is what the reader substitutes, and a backticked `TODO` is prose about markers. Both are correct authoring, and both would be rejected by a scan that read code.

## The sections each type owes

| Type | Required `##` sections |
|---|---|
| **rule** | `Conditions`, `Where this stops` |
| **doc** | `Where this stops` |
| **skill** | at least one numbered step, `When this skill does not apply` |
| **agent** | `What this agent is for`, `Skills it orchestrates`, `What it does not do` |
| **command** | `What runs` |

Headings are matched outside code, so an example of a heading is not a heading.

These are the sections that carry the artifact's boundary. `Where this stops` is what separates a rule from dogma; `When this skill does not apply` is what stops a skill being reached for in the wrong situation; `What it does not do` is what keeps an agent from absorbing its neighbours. `docs/artifact-model.md` argues the case.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. No frontmatter value contains a marker or an angle-bracket placeholder.
2. No body line outside code contains a marker or an angle-bracket placeholder.
3. Every section required for the artifact's type is present as an `##` heading outside code.
4. A skill has at least one numbered `##` step.

## Where this stops

**Presence, not substance.** A `Where this stops` section reading "nothing to say here" satisfies condition 3. The gate checks that the reader was given the section; only a reviewer checks that it was given an answer.

**The marker list is closed.** `TODO`, `TBD`, `FIXME` and `XXX` are caught because they are conventional and unambiguous in uppercase. A lowercase "todo" in a sentence is not, and chasing it would reject English prose.

**Angle brackets outside code are always a failure here**, even when an author meant one literally. That costs an author the occasional backtick and buys a detector with no judgment in it. If a literal angle bracket ever needs to sit in prose, the rule grows an exception then, with the case that forced it.
