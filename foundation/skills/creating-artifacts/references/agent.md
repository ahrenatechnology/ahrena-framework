---
name: <filename-without-md, noun phrase, kebab-case>
description: <the specialism, then when to hand work to it. Written for the caller deciding whether this is the right specialist.>
type: agent
clade: <plugin-clade>
subclade: <optional>
references:
  - skills/<skill-it-orchestrates>/SKILL.md
  - rules/<rule-it-enforces>.md
  - docs/<doc-it-consults>.md
---

# <Specialist name>

## What this agent is for

The kind of work it takes, in two or three sentences. A caller reads this
to decide whether to route here, so lead with the boundary rather than the
capability.

## Skills it orchestrates

| Skill | When it runs |
|---|---|
| `<skill-name>` | <the condition that selects it> |

An agent chooses between skills. If it is carrying out steps itself rather
than selecting a procedure, the steps belong in a skill and this agent
should invoke it.

## Rules it enforces

The guardrails that bind its output, by path. It applies them; it does not
restate them.

## What it hands back

The shape of the result, and what is deliberately left to the caller.

## What it does not do

The adjacent work it will be asked for, and the specialist that owns it.
