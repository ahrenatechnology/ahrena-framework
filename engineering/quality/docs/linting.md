---
id: linting
type: doc
clade: engineering
subclade: quality
title: Linters, formatters and type checkers by language
summary: The tool each language uses for the three static checks the linting rule requires, and why every limit is zero.
references:
  - rules/linting.md
---

# Linters, formatters and type checkers by language

This document explains `rules/linting.md`: LNT-1 to LNT-3 of the PR quality rubric of epic 323.

## The tool per language

The rule does not name a tool; it names the three kinds of check, and a project uses the one its ecosystem treats as standard.

| Language | Linter | Formatter | Type checker |
|---|---|---|---|
| TypeScript | ESLint or Biome | Prettier or Biome | `tsc --noEmit --strict` |
| Go | `go vet`, `golangci-lint` | `gofmt` | the compiler |
| Python | `ruff` | `ruff format` | `mypy --strict` |
| Protocol buffers | `buf lint` | `buf format` | the compiler of the target language |
| OpenAPI | Spectral | | |

## Why every limit is zero

The limits are maintainer policy (the standard of issue 34), not measured: a linter either accepts the code or it does not, and a count above zero is a choice to carry known findings. They apply to what the change adds, so a legacy tree with warnings is not blocked, and the count of its warnings may not rise.

## Why silencing and loosening are conditions of their own

A rule switched off in the line or in the configuration passes LNT-1 by construction. Without LNT-2 and LNT-3 the cheapest way to turn a pull request green is to remove the check, so the two conditions close the two ways of doing that. A pointer makes the exception a recorded decision that can be reviewed and revisited, instead of a private one.

## Where this stops

This document does not pick the rules a linter enables. That is each language plugin's, and a project's own configuration.
