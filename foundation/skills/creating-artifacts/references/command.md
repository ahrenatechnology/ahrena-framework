---
name: <filename-without-md, kebab-case>
description: <one line shown in the invocation list>
type: command
clade: <plugin-clade>
subclade: <optional>
argument-hint: <optional, platform field, e.g. "[artifact-type] [name]">
references:
  - skills/<skill-it-invokes>/SKILL.md
---

# /<name>

Invoke `<skill-or-agent>` with the arguments below.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `<arg>` | yes | <what it selects> |

## What runs

A single line naming the skill or agent this hands off to.

<!--
A command holds no logic. It may reference a skill or an agent and nothing
else: no rule, no doc.

If this file is explaining how to do the work rather than who does it, the
work is a skill that does not exist yet. Write that skill and point here.
-->
