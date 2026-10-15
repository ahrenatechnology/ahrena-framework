---
name: graph-doctor
description: Provision the code graph's optional macro tier, or report exactly how to enable it, always leaving the guaranteed light floor answering.
type: command
clade: engineering
subclade: architecture
argument-hint: "[--build] [--install-grammars]"
references:
  - skills/provisioning-the-code-graph/SKILL.md
---

# /graph-doctor

Invoke `provisioning-the-code-graph` with the arguments below.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `--build` | no | (Re)build the macro graph when Graphify is on PATH. Without it, the doctor only inspects and reports |
| `--install-grammars` | no | Install the tree-sitter grammars the detected languages lack, when pip is available, degrading to a precise report when it is not |

Without either flag the doctor inspects and reports only; it never installs
Graphify, which is a personal skill rather than a package.

## What runs

`skills/provisioning-the-code-graph`, from step 1.
