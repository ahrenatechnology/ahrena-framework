---
name: round-pm
description: Open the day's round on a project as its PM ("PM da rodada") — the last closing, carried-over work on top, a plan up to capacity, the person's ok, then the Round issue.
type: command
clade: engineering
subclade: delivery
argument-hint: "project [window]"
references:
  - agents/themis.md
  - skills/opening-the-round/SKILL.md
---

# /round-pm

Invoke `themis` with the arguments below. It opens the round through `opening-the-round`.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `project` | yes | The project whose round this is; its repository holds the Round issue |
| `window` | no | When the round starts and ends today. Without it, the PM asks the person |

## Title

The session's title is set first, in the form `PM da rodada · Projeto · dd/mm/aaaa`: the project argument for `Projeto` and today's date. The date is the day the session opened and is never edited later; tomorrow's round is a new `/round-pm`.

## What runs

`themis`, starting at step 1 of `skills/opening-the-round`. On a later day or after an account switch, the same command starts the fresh session, which reads the last closing or the newest work context from the Round issue.
