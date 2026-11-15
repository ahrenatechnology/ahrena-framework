---
id: anthropic-skill-format
type: doc
clade: foundation
title: Anthropic's Agent Skills format
summary: What Anthropic documents about a skill folder - the frontmatter fields and their limits, the folder layout, progressive disclosure and where a skill loads - with the page that states each limit, and how this framework's own skill shape differs.
references:
  - docs/artifact-model.md
  - rules/frontmatter.md
---

# Anthropic's Agent Skills format

A skill in Anthropic's standard is a folder with a `SKILL.md`, loaded by Claude Code, claude.ai, the Skills API and the Claude Agent SDK. Claudionor writes one when the caller asks for it, and `hooks/validate-anthropic-skill.py` decides the limits below. Each limit names the page that states it; nothing here rests on memory. Pages read on 2026-11-15.

Sources:

- **Overview**: [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- **Best practices**: [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- **Claude Code**: [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- **Spec**: [Agent Skills specification](https://agentskills.io/specification), which the Claude Code page names as the source of `license` and `compatibility`

## Frontmatter

Two fields are required: `name` and `description` (Overview, "Skill structure"). The Claude Code page lists every field as optional, with `description` recommended, and says Claude Code ignores unrecognized fields. The same page says claude.ai uploads and the Skills API accept only six fields, and that any other field is a hard validation error there. So the checker has two profiles:

| Profile | Fields it accepts | Source |
|---|---|---|
| `portable` (default) | `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` | Claude Code, "Using skill frontmatter outside Claude Code"; Spec, "Frontmatter" |
| `claude-code` | the six above plus `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell` | Claude Code, "Frontmatter reference" |

Default to `portable`: a skill that passes it loads everywhere. Choose `claude-code` only when the caller says the skill is for Claude Code alone and needs a field the portable set lacks.

A framework field (`type`, `clade`, `subclade`, `references`) is in neither profile. That is the difference between the two shapes, below.

## Limits

| Field | Limit | Source |
|---|---|---|
| `name` | at most 64 characters | Overview, "Skill structure"; Best practices, "Skill structure" |
| `name` | lowercase letters, numbers and hyphens only | Overview, "Skill structure" |
| `name` | no XML tags | Overview, "Skill structure" |
| `name` | must not contain the reserved words `anthropic` and `claude` | Overview, "Skill structure" |
| `name` | must not start or end with a hyphen, no consecutive hyphens, must match the parent directory name | Spec, "`name` field" |
| `description` | non-empty, at most 1,024 characters | Overview, "Skill structure" |
| `description` | no XML tags | Overview, "Skill structure" |
| `description` | written in the third person, saying what the skill does and when to use it | Best practices, "Writing effective descriptions" |
| `compatibility` | at most 500 characters | Claude Code, "Frontmatter reference"; Spec, "`compatibility` field" |
| `SKILL.md` body | under 500 lines | Best practices, "Progressive disclosure patterns"; Claude Code, "Add supporting files" |

The Claude Code page adds that `description` and `when_to_use` together are cut at 1,536 characters in the skill listing. That cap only binds the `claude-code` profile, and the 1,024 cap on `description` is stricter.

## Folder layout

```text
my-skill/
├── SKILL.md
├── references/
├── scripts/
└── assets/
```

`SKILL.md` is required. `scripts/`, `references/` and `assets/` are the optional directories the Spec lists ("Optional directories"): code Claude runs, documentation it reads on demand, and static resources such as templates. The Overview and Best practices pages show the same idea with reference files beside `SKILL.md` and a `scripts/` folder; they do not name `assets/`. Reference files link directly from `SKILL.md`, one level deep, because Claude may read only the head of a file that a referenced file points to (Best practices, "Avoid deeply nested references"). A reference file over 100 lines opens with a table of contents (Best practices, "Structure longer reference files with a table of contents"). Paths use forward slashes (Best practices, "Anti-patterns to avoid").

## Progressive disclosure

Three levels, loaded at different times (Overview, "How Skills work"):

1. **Metadata**: `name` and `description`, always loaded, about 100 tokens per skill.
2. **Instructions**: the `SKILL.md` body, loaded when the skill triggers, under 5,000 tokens.
3. **Resources**: files and scripts, read or run as needed. A script's code never enters context, only its output.

This is why the description carries the trigger: it is all Claude has when it chooses among skills.

## Where it loads

A skill in a Claude Code plugin sits at `skills/<skill-name>/SKILL.md` and is invoked as `/plugin-name:skill-name` (Claude Code, "Choose where skills load" and "How a skill gets its command name"). A plain plugin is a folder with `.claude-plugin/plugin.json` and that `skills/` directory, with no framework fields and no marketplace of this repository. claude.ai takes the skill folder as a zip, the Skills API takes it through `/v1/skills`, and the Claude Agent SDK reads it from the filesystem. Skills do not sync across these surfaces (Overview, "Cross-surface availability").

## How it differs from the framework's shape

| | Framework skill | Anthropic skill |
|---|---|---|
| Frontmatter | `name`, `description`, `type`, `clade`, `references`, plus optional `subclade` | only the fields of one profile above |
| Where it lives | `skills/<name>/SKILL.md` of a plugin in this marketplace | the folder the caller names, outside any plugin this gate walks |
| Checked by | `hooks/validate-artifacts.py` | `hooks/validate-anthropic-skill.py` |
| Name | gerund first token (`rules/naming.md`) | gerund recommended (Best practices, "Naming conventions"), not required |
| Body | 10-line code cap and reachable files (`rules/progressive-disclosure.md`) | under 500 lines, links one level deep |

The shapes do not mix. A framework skill never carries Anthropic-only fields, and an Anthropic skill never carries framework fields: the `validate-artifacts.py` gate would not know the second and the portable surfaces would reject the first. The caller states the shape in the request, and a request that does not state it gets the framework shape.

## What a script cannot decide

`validate-anthropic-skill.py` decides the fields, the name, the description's length, tags and person, the compatibility cap, the body length and whether each relative link resolves inside the folder. It cannot decide whether the description says when to use the skill, whether the body repeats what Claude already knows, or whether the skill fires on the request it was written for. `skills/reviewing-artifacts` carries those.

## Where this stops

This page covers a skill. An agent, a command or a hook in Anthropic's shape, and building AI agents as products, are outside it. Anthropic's pages change; the date above is when these limits were last read, and a limit that differs on the page is the page's, not this one's.
