---
name: <directory-name, lowercase letters, numbers and single hyphens, at most 64 characters, no "anthropic" or "claude">
description: <third person: what the skill does, then "Use when" the situations that trigger it. Non-empty, at most 1024 characters, no angle brackets.>
---

# <Title>

## 1. <First step>

One outcome per step, in order. Keep the body under 500 lines.

## 2. <Step that needs detail>

Detail Claude reads only in this step goes in a file linked straight from
here: [the schema](references/schema.md). One level deep, forward slashes.

## 3. <Step that executes something>

Run `scripts/check.py <input>`. A script's code never enters context, only
its output, so say whether Claude runs the file or reads it.

<!--
Folder layout:

<name>/
├── SKILL.md
├── references/    documentation read on demand
├── scripts/       code that is run
└── assets/        templates and static files

Portable profile fields: name, description, license, compatibility
(at most 500 characters), metadata, allowed-tools. Nothing else.
Check it with: python3 foundation/hooks/validate-anthropic-skill.py <folder>
-->
