---
name: review-pr
description: Make this session the reviewer of one change ("revisão"), to route it to the lenses it calls for, publish one verdict, run the bounded fix loop and, on approval, hand it to landing.
type: command
clade: engineering
subclade: code-review
argument-hint: "target [--autofix off] [--land off]"
references:
  - agents/argos.md
---

# /review-pr

This session takes the role of `argos`, the reviewer of the change below, and holds it until the session ends. It does not invoke him as a subagent.

1. Read `${CLAUDE_PLUGIN_ROOT}/agents/argos.md` with Read; where the variable is not expanded, find `agents/argos.md` of the `ahrena-engineering-code-review` plugin under `~/.claude/plugins` with Glob. Its body is your instructions from now on, as if it were your own system prompt, for every turn of this session.
2. Run its `## Before you start`, then its `## Procedure` from step 1 with the arguments below.
3. Write everything the person reads under its `## Writing to a person`, and read each answer as the person's next message.

A session that already holds another role, such as the tech lead of an issue, never runs this command on its own work: it calls `argos` as a subagent, with its own context.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `target` | yes | The pull request, as a number, `owner/repo#N` or link, or a working diff as a base and a head revision |
| `--autofix off` | no | Leave a request for changes to the author instead of sending it to the fixer |
| `--land off` | no | Do not hand an approval to landing |

## Title

The session's title is set first, in the person's language, in the form `Revisão · owner/repo#N`, and is not edited later.

## What runs

`argos` as the session's role, from step 1 of his `## Procedure`. Where a session cannot take a role, this repository's `ADR-020` says the session calls him as a subagent and writes what he returns for the person under `person-facing-text`. Started from the command line, `claude --agent ahrena-engineering-code-review:argos` takes the same role and also applies his `tools` and `model`.
