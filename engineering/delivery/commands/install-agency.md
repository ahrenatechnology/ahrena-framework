---
name: install-agency
description: Make the agency the default path for build work on this platform, or report what is missing — writing the entry directive into the always-loaded instruction file idempotently.
type: command
clade: engineering
subclade: delivery
argument-hint: "[--check] [--platform claude|codex]"
references:
  - skills/installing-the-agency/SKILL.md
---

# /install-agency

Invoke `installing-the-agency` with the arguments below.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `--check` | no | Report whether the entry directive is present and current, writing nothing. Without it, the directive is written or refreshed |
| `--platform claude\|codex` | no | Override the auto-detected platform when the repository carries both `CLAUDE.md` and `AGENTS.md` |

Without `--check` the skill ensures the directive is in place; the write is
idempotent, so a re-run on an already-installed repository changes nothing.

## What runs

`skills/installing-the-agency`, from step 1.
