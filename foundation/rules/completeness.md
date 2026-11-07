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

No frontmatter field and no line of prose carries `TODO`, `TBD`, `FIXME`, `XXX`, or an unreplaced template placeholder in angle brackets. The one angle-bracket token a body may carry in prose is the `<example>` tag that opens an agent's worked example; its closing tag never read as a placeholder. A line of prose that is nothing but a brace placeholder `{ … }` is a leftover too; a brace in the middle of a line is not, because braces are ordinary in prose.

The scan skips fenced blocks and inline code. `<plugin>` on a command line is what the reader substitutes, and a backticked `TODO` is prose about markers. Both are correct authoring, and both would be rejected by a scan that read code.

**These four markers are banned in an artifact's own text, and nowhere else.** The same four tokens in a consumer's source are governed by condition 1 of [`debt-markers.md`](../../engineering/fundamentals/rules/debt-markers.md) in the engineering plugin, which permits one that names an issue — because source is where work in progress legitimately lives and a finished artifact is not. The two rules take the same four tokens and the same backtick escape, so they never disagree about what a marker is, only about what one means.

## The sections each type owes

| Type | Required `##` sections |
|---|---|
| **rule** | `Conditions`, `Where this stops` |
| **doc** | `Where this stops` |
| **skill** | at least one numbered step, `When this skill does not apply` |
| **agent** | `What this agent is for`, `Inputs`, `Procedure`, `Delegation`, `Done when`, `When blocked`, `Output`, `What it does not do`, `Example`, in that order, with `Before you start` second when the agent orchestrates a skill |
| **command** | `What runs` |

Headings are matched outside code, so an example of a heading is not a heading.

**Until #252 lands its rewrites, the agent row binds an agent that has `## Procedure`.** An agent without one is held to the shape every agent had before #252: `What this agent is for`, `Skills it orchestrates`, `What it does not do`. That is the 11 agents in this marketplace that predate the skeleton, and the escape goes when they are rewritten. `Before you start` is in the order but not in the row's required set, because condition 10 of [`frontmatter.md`](frontmatter.md) already requires it exactly when the agent orchestrates a skill.

**An agent's `Output` is a literal template.** Each fenced block under `## Output` opens with `DONE`, `BLOCKED` or `NEEDS_APPROVAL` on its first line, and a `NEEDS_APPROVAL` block carries an `approve:`, a `recommendation:` and a `resume:` field, because a run that needs a person's approval returns and stops instead of waiting. Its `Example` holds at least one worked example between `<example>` and `</example>` tags outside code.

These are the sections that carry the artifact's boundary. `Where this stops` is what separates a rule from dogma; `When this skill does not apply` is what stops a skill being reached for in the wrong situation; `What it does not do` is what keeps an agent from absorbing its neighbours. `docs/artifact-model.md` argues the case.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. No frontmatter value contains a marker or an angle-bracket placeholder.
2. No body line outside code contains a marker, an angle-bracket placeholder, or a brace placeholder that is the whole line.
3. Every section required for the artifact's type is present as an `##` heading outside code.
4. A skill has at least one numbered `##` step.
5. In an agent that has `## Procedure`, the skeleton sections it carries appear in the order of the agent row.
6. In such an agent, `## Output` holds at least one fenced block; every fenced block there opens with `DONE`, `BLOCKED` or `NEEDS_APPROVAL`, and one that opens with `NEEDS_APPROVAL` has lines starting `approve:`, `recommendation:` and `resume:`.
7. In such an agent, `## Example` holds an `<example>` tag followed by an `</example>` tag, outside code.

## Where this stops

**Presence, not substance.** A `Where this stops` section reading "nothing to say here" satisfies condition 3. The gate checks that the reader was given the section; only a reviewer checks that it was given an answer.

**The marker list is closed.** `TODO`, `TBD`, `FIXME` and `XXX` are caught because they are conventional and unambiguous in uppercase. A lowercase "todo" in a sentence is not, and chasing it would reject English prose.

**Angle brackets outside code are a failure here, with one exception**, even when an author meant one literally. That costs an author the occasional backtick and buys a detector with no judgment in it. The exception is the `<example>` tag, forced by #252: an agent's worked example is fenced off from its instructions by that tag, and putting it in a code block instead would put a whole example under the 10-line cap of [`progressive-disclosure.md`](progressive-disclosure.md). The exception is that one token; `<examples>` or `<input>` still fails.

**The skeleton is checked for presence, order and the shape of the status line.** Whether a `Procedure` step names its output, whether `Delegation` names an agent that exists, or whether the example is one the agent would actually return is read by [`reviewing-artifacts`](../skills/reviewing-artifacts/SKILL.md), not by conditions 5 to 7.

**A brace is a leftover only when it is the whole line.** Angle brackets are read anywhere outside code, but braces are ordinary — in prose, in code, and in the `{{ … }}` title placeholder of [`opening-issues`](../../contributing/skills/opening-issues/SKILL.md) — so only a body line that is nothing but a single brace placeholder is read as unfilled, and a double brace never is. A brace placeholder in a frontmatter value never reaches this check: [`frontmatter.md`](frontmatter.md) rejects a value that opens with `{` as an inline collection first, so the field that #202 moved to the `{ … }` notation is already guarded.
