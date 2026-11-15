---
name: round-pm
description: Open the day's round on a project as its PM ("PM da rodada") — the last closing, carried-over work on top, a plan up to capacity, the person's ok, then the Round issue.
type: command
clade: engineering
subclade: delivery
argument-hint: "project [window]"
model: opus
references:
  - agents/themis.md
  - skills/opening-the-round/SKILL.md
---

# /round-pm

This session takes the role of `themis`, the PM of the round below, which opens it through `opening-the-round`, and holds it until the session ends. It does not invoke the agent.

1. Read `${CLAUDE_PLUGIN_ROOT}/agents/themis.md` with Read; where the variable is not expanded, find `agents/themis.md` of the `ahrena-engineering-delivery` plugin under `~/.claude/plugins` with Glob. Its body is your instructions from now on, as if it were your own system prompt, for every turn of this session.
2. Run its `## Before you start`, then its `## Procedure` with the arguments below.
3. Write everything the person reads under its `## Writing to a person`, and read each answer as the person's next message.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `project` | yes | The project whose round this is; its repository holds the Round issue |
| `window` | no | When the round starts and ends today. Without it, the PM asks the person |

## Title

The session's title is set first, in the form `PM da rodada · Projeto · dd/mm/aaaa`: the project argument for `Projeto` and today's date. The date is the day the session opened and is never edited later; tomorrow's round is a new `/round-pm`.

## Model

The PM of the round is a lead, so it runs on `opus` (`model` of the agent, and `rules/frontmatter.md` of `ahrena-foundation`). This command's `model` field pins only its own turn; if the session runs on another model, tell the person in one sentence to switch it with `/model opus`, and carry on.

## What runs

`themis` as the session's role, starting at step 1 of `skills/opening-the-round`. Where a session cannot take a role, this repository's `ADR-020` says the session calls the agent as a subagent and writes what it returns for the person under `person-facing-text`. On a later day or after an account switch, the same command starts the fresh session, which reads the last closing or the newest work context from the Round issue.
