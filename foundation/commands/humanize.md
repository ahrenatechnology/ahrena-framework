---
name: humanize
description: Rewrite a text so it reads as written by a person, or analyze it and report what reads as machine-written without changing it.
type: command
clade: foundation
argument-hint: "[analyze|rewrite] [file, path or pasted text]"
references:
  - skills/rewriting-ai-prose/SKILL.md
---

# /humanize

Invoke `rewriting-ai-prose` with the arguments below.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `mode` | no | `analyze` reports the verdict, every tell with its excerpt and fix, and the facts to keep, and changes nothing. `rewrite` returns the edited text. Defaults to `rewrite` |
| `target` | yes | A file, a path or the pasted text. With none, the skill asks for one and stops |

## What runs

`skills/rewriting-ai-prose`, from step 1.
