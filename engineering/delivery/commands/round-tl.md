---
name: round-tl
description: Start the Tech Lead of the day's round ("Tech Lead da rodada") from its Round issue, to run one Athena session per approved issue and land what Argos approved, on green checks, after the PM's acceptance.
type: command
clade: engineering
subclade: delivery
argument-hint: "project round-issue"
references:
  - agents/hermes.md
  - skills/dispatching-sessions/SKILL.md
---

# /round-tl

Invoke `hermes` with the arguments below. It dispatches the round's activities through `dispatching-sessions`.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `project` | yes | The project whose round this is |
| `round-issue` | yes | The open Round issue, by number or link. Its Activities table is the list of work, and its newest work context, when there is one, is where the session starts |

## Title

The session's title is set first, in the form `Tech Lead da rodada · Projeto · dd/mm/aaaa`: the project argument for `Projeto` and today's date, never edited later.

## What runs

`hermes`, reading the Round issue, then `skills/dispatching-sessions` from step 1 for each approved activity not yet dispatched. The PM starts this command only when the round holds two or more build issues in parallel, or an infrastructure operation beside one.
