---
id: frontmatter
type: rule
clade: foundation
title: Artifact frontmatter
statement: Every artifact opens with frontmatter carrying the fields its type requires and nothing undeclared.
enforcement: hook
enforced-by: hooks/validate-artifacts.py
references:
  - docs/artifact-model.md
---

# Artifact frontmatter

## Shape

Every artifact begins on line 1 with `---`, closes the block with `---`, and holds a flat map. Values are scalars or lists of scalars.

```yaml
---
key: a scalar
list:
  - first
  - second
---
```

Field names are kebab-case, matching `[a-z][a-z0-9-]*`. That is what the platforms already use (`allowed-tools`, `argument-hint`) and what this framework uses everywhere else, so there is no second convention to remember.

Nested maps, inline collections and multi-line scalars are rejected. The restriction is what lets `hooks/validate-artifacts.py` run on a stdlib-only Python with no YAML dependency, which is what lets a consumer run the same gate the repository runs.

## Required fields

| Field | rule | doc | skill | agent | command |
|---|---|---|---|---|---|
| `id` | ● | ● | | | |
| `name` | | | ● | ● | ● |
| `type` | ● | ● | ● | ● | ● |
| `clade` | ● | ● | ● | ● | ● |
| `title` | ● | ● | | | |
| `summary` | | ● | | | |
| `description` | | | ● | ● | ● |
| `role` | | | | ● | |
| `statement` | ● | | | | |
| `enforcement` | ● | | | | |

`role` is the agent's subject as a noun phrase, beside the persona in `name`. `rules/naming.md` explains why an agent carries two.

`subclade` and `references` are optional on every type. `enforced-by` is required when `enforcement` is `hook` and rejected when it is `judgment`.

Rules and docs use `id`, `title` and `summary` because nothing outside this framework reads them. Skills, agents and commands use `name` and `description` because the platforms do, and a parallel set of our own fields would be a second thing to keep in sync.

## Undeclared fields

**On a rule or a doc, an undeclared field fails.** The schema is closed because we own both ends of it.

**On a skill, an agent or a command, an undeclared field passes.** These files are read by four platforms that add fields on their own schedule. `allowed-tools`, `model` and `argument-hint` are theirs, they will not be the last, and a gate that rejects them would break on someone else's release.

## `statement`

A rule's `statement` is the one line that reaches the agent. It goes into the platform instruction file with a link to the rule's full text, and nothing else from the rule does.

It is a single line of at most 160 characters. A statement that will not fit is carrying rationale, and rationale belongs in the rule's doc companion.

This is what keeps the always-loaded footprint bounded: one line per judgment rule, zero per hook rule.

## `enforcement`

The value is `hook` or `judgment`.

`hook` means a script decides the condition. `enforced-by` names it, as a plugin-relative path, and the file must exist.

`judgment` means the condition needs a reader.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. The file opens with a frontmatter block on line 1 and closes it.
2. The block parses as a flat map of scalars and lists of scalars.
3. Every field required for the artifact's type is present and non-empty.
4. A rule or a doc carries no field outside the declared set.
5. `statement` is one line of at most 160 characters.
6. `enforcement` is `hook` or `judgment`, and `enforced-by` is present exactly when it is `hook`.

## Where this stops

The gate checks that a field is present and well-shaped. It does not read it. A `description` that describes the wrong skill passes, and only a reviewer catches it.
