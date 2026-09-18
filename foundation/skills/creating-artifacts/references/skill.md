---
name: <directory-name, gerund first token, kebab-case>
description: <what it does, then when to use it. This is the only text the platform reads when deciding whether to load the skill, so name the triggers explicitly.>
type: skill
clade: <plugin-clade>
subclade: <optional>
references:
  - rules/<rule-it-applies>.md
  - docs/<doc-it-consults>.md
---

# <Activity, in the gerund>

## 1. <First step>

One outcome per step, in the order they happen. Say what to do, not what
the step is about.

## 2. <Second step>

Name the failures that recur at this step. A step that only describes the
happy path gets skipped when the input is unusual.

## 3. <Step that executes something>

```sh
python3 scripts/<name>.py <args>
```

Material the step reads goes in `references/`. Work the step executes goes
in `scripts/`. A procedure that can be run is worth more than one that has
to be paraphrased.

Inline, a code block holds only the line a person types: the cap is 10
lines and the gate enforces it. Name every file you put in the body from
the step that opens it, or the gate fails it as unreachable.

## When this skill does not apply

The neighbouring cases it will be reached for and should not handle, with
where they go instead.

<!--
Directory layout:

skills/<name>/
├── SKILL.md
├── references/    material the skill reads
└── scripts/       work the skill executes

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
