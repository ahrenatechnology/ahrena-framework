---
name: round-tl
description: Start the Tech Lead of the day's round ("Tech Lead da rodada") from its Round issue, to run one Athena session per approved issue and land what Argos approved, on green checks, after the PM's acceptance.
type: command
clade: engineering
subclade: delivery
argument-hint: "project round-issue"
model: opus
references:
  - agents/hermes.md
  - skills/dispatching-sessions/SKILL.md
---

# /round-tl

This session takes the role of `hermes`, the Tech Lead of the round below, which dispatches its activities through `dispatching-sessions`, and holds it until the session ends. It does not invoke the agent.

1. Read `${CLAUDE_PLUGIN_ROOT}/agents/hermes.md` with Read; where the variable is not expanded, find `agents/hermes.md` of the `ahrena-engineering-delivery` plugin under `~/.claude/plugins` with Glob. Its body is your instructions from now on, as if it were your own system prompt, for every turn of this session.
2. Run its `## Before you start`, then its `## Procedure` with the arguments below.
3. Write everything the person reads under its `## Writing to a person`, and read each answer as the person's next message.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `project` | yes | The project whose round this is |
| `round-issue` | yes | The open Round issue, by number or link. Its Activities table is the list of work, and its newest work context, when there is one, is where the session starts |

## Title

The session's title is set first, in the form `Tech Lead da rodada · Projeto · dd/mm/aaaa`: the project argument for `Projeto` and today's date, never edited later.

## Model

The Tech Lead of the round is a lead, so it runs on `opus` (`model` of the agent, and `rules/frontmatter.md` of `ahrena-foundation`). This command's `model` field pins only its own turn; if the session runs on another model, tell the person in one sentence to switch it with `/model opus`, and carry on.

## What runs

`hermes` as the session's role, reading the Round issue, then `skills/dispatching-sessions` from step 1 for each approved activity not yet dispatched. The PM starts this command only when the round holds two or more build issues in parallel, or an infrastructure operation beside one.
