---
id: naming
type: rule
clade: foundation
title: Artifact names and paths
statement: Artifact names are kebab-case, carry no type or clade prefix, and sit flat in their type directory.
enforcement: hook
enforced-by: hooks/validate-artifacts.py
references:
  - docs/artifact-model.md
---

# Artifact names and paths

## Paths

There are exactly two shapes.

```
<plugin>/rules/<name>.md
<plugin>/docs/<name>.md
<plugin>/agents/<name>.md
<plugin>/commands/<name>.md

<plugin>/skills/<name>/SKILL.md
```

A skill is a directory because it has a body: `references/` for material it reads and `scripts/` for work it executes. The other four are a single file because they have nothing to carry.

## Flat, with no exceptions

No type directory contains subdirectories, and `skills/` is exactly one level deep. `skills/python/creating-modules/SKILL.md` does not work, and the reason is not taste: DeepSeek's local provider does not support recursive `**/SKILL.md` discovery, so a nested skill is invisible to it.

Grouping is expressed by `clade` and `subclade` in frontmatter, and by which plugin the artifact ships in. Never by directory depth.

## Names

A name matches `[a-z0-9]+(-[a-z0-9]+)*`. Lowercase, digits and single hyphens.

**No type prefix.** The directory already says what it is. `rules/rule-naming.md` and `skills/skill-creating-artifacts/` are both failures. So are the predecessor's mythological prefixes.

**No clade prefix.** The plugin already says which clade it is. `rules/foundation-naming.md` is a failure.

**Skills are named for the activity, in the gerund.** The first token ends in `ing`: `creating-artifacts`, `executing-plans`, `reviewing-diffs`. This matches the platform convention and reads correctly at the invocation site, where the name appears as the thing being done.

**Rules, docs and commands are named for the subject**, as a noun phrase: `naming`, `artifact-model`, `new-rule`.

## An agent carries two names

An agent is addressed by people, and the two things a person needs from it pull in opposite directions. A handle has to be short, memorable and unambiguous across a room. A description of scope has to be literal. One string cannot be both without being bad at one of them.

So an agent declares both.

| Field | What it is | Example |
|---|---|---|
| `name` | The handle. How a person invokes it, and what appears in the platform's agent list. | `claudionor` |
| `role` | The subject, as a noun phrase. What the agent actually is. | `artifact-author` |

Both are kebab-case and both obey the no-type-prefix and no-clade-prefix conditions above. `name` matches the filename, as for every other type. `role` is free of the disk.

A persona name is allowed here and nowhere else. A skill is an activity and a rule is a constraint; neither is addressed, so neither has anything to gain from a name people remember.

The cost of the second field is that it can drift from the description. The gate checks its shape, not its truth, so `role` is one of the things a reviewer reads.

The handle is unique across the marketplace, not only within a plugin. A caller or a runtime invokes an agent by its handle, and two agents under one handle leave the platform to pick one of them, with the caller none the wiser.

An agent that hands work to another names it the way the Agent tool lists it: plugin-qualified, `<plugin>:<agent>`, in the `subagent_type` column of its `## Delegation` table. A bare handle depends on which plugins happen to be installed, and a role ("a specialist", "the reviewer") resolves to nothing.

## Identity

The name in frontmatter matches the name on disk.

| Type | Field | Must equal |
|---|---|---|
| rule, doc | `id` | the filename without `.md` |
| agent, command | `name` | the filename without `.md` |
| skill | `name` | the containing directory name |

Rules and docs use `id` because they are ours. Skills, agents and commands use `name` because that is the field the platforms read. The distinction is deliberate and is explained in `docs/artifact-model.md`.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. Every artifact sits at one of the two path shapes above.
2. No `SKILL.md` exists below `skills/<name>/`.
3. Every artifact name matches `[a-z0-9]+(-[a-z0-9]+)*`.
4. No name begins with its own type or its own clade.
5. A skill name's first token ends in `ing`.
6. The identity field matches the name on disk.
7. An agent declares `role`, kebab-case, under the same prefix conditions as its name.
8. No two agents in the marketplace declare the same `name`, in one plugin or across plugins.
9. In an agent's `## Delegation` table, the table has a `subagent_type` column, and every cell of it names, in backticks, only `<plugin>:<agent>` names, each resolving to `agents/<agent>.md` in that plugin of the marketplace. A cell that is not plugin-qualified fails.
10. Every `<plugin>:agents/<name>.md` an agent's body names outside fenced code resolves to an agent in the marketplace.

## Where this stops

**The gerund check is a suffix test, not grammar.** It catches the mistake that actually happens, which is a skill named as a noun phrase (`artifact-creation`, `code-review`). A noun that happens to end in `ing` passes it, and `skills/thing-doer/` is the case in the gate's own test suite. Closing that gap needs a dictionary, which is a dependency this hook will not take for one class of typo. A reviewer catches it.

**Delegation is resolved, not read.** Conditions 9 and 10 check that every named agent exists. Whether the row's brief carries what the child's `## Inputs` asks for, and whether a sentence in prose hands work to an agent the table does not name, is SP-2 of `reviewing-artifacts`.

Files inside a skill body are not artifacts and this rule does not reach them. `references/` and `scripts/` hold whatever the skill needs, named however the language it is written in expects.
