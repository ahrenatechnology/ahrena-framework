---
name: reading-the-component-map
description: Use before naming or creating anything in a project — a folder, a type, an endpoint, a concept. Locates the project's component map, resolves a canonical term to the project's own word, and hands back the vocabulary, conventions and testing tools for the concern at hand, falling back to the framework default only where the project is silent.
type: skill
clade: engineering
subclade: architecture
references:
  - rules/ubiquitous-language.md
  - docs/component-map.md
---

# Reading the component map

This is the procedure an agent runs to satisfy [`rules/ubiquitous-language.md`](../../rules/ubiquitous-language.md): before it names or creates anything, it reads the project's own language and conventions and conforms to them. [`docs/component-map.md`](../../docs/component-map.md) defines the file this procedure reads and the precedence it applies. Run this whenever a name, a folder or a concept is about to be chosen, not once per session.

## 1. Locate the project's component map

Find the map the project committed. Look for it at the repository root and in the conventional configuration locations the project uses, by whatever filename the project gave it.

The recurring failure is concluding "there is no map" too fast. A project may keep its vocabulary in an existing conventions document rather than a file named for this schema; read that as the map. Only when the repository genuinely states no vocabulary, layout or tooling is the project silent — and silence is a conclusion you record, not a step you skip. If you did not look, you have not found the project silent; you have failed condition 1 of the rule.

## 2. Read the concern's slice of the map

Read `glossary`, `components`, `conventions`, `testing` and `delivery`, then narrow to the concern you are about to act in. Match the component by `concern` — `backend`, `frontend` or `data` — and by the `paths` you are working under, so you read the conventions and stack that actually apply rather than another component's.

The failure here is reading the whole map and averaging it. A frontend component's naming convention does not govern a change to the backend. Take the slice for the concern at hand.

## 3. Resolve each canonical term to the project's word

For every concept you are about to name, look it up in `glossary` by its canonical term and use the project's word. Resolve the concept, not the string you first thought of.

```yaml
# canonical -> project; you write the right-hand side
use_case: workflow
aggregate: record
```

A concept absent from the glossary resolves to its canonical term, because the project has sanctioned no alternative — that is the framework default applying to a silent entry, which is correct. A concept present in the glossary resolves to the project's word, always, and is never merged with the canonical one.

## 4. Check any new folder or term against the sanctioned set

Before creating a directory or coining a term, check it against `conventions.folders` and the vocabulary in `glossary`. Create only what the project has sanctioned.

A folder not on the sanctioned list is a folder you do not invent. When the work seems to need a structure the project has not named, that is a question for the owner, not a licence to create `use_cases/` on your own authority. Inventing structure is condition 3 of the rule failing.

## 5. Resolve testing and delivery for the concern

Read the `testing` lane and the `delivery` value that apply, and take the project's `tools` and `philosophy` where stated. These are overridable defaults: a stated entry replaces the framework default for this project rather than running beside it.

Where a lane or `delivery` is absent, the framework default for it applies — that is silence resolving correctly, not a gap to fill with an invention. The full shape of every key, with a worked map, is in [`references/component-map.example.yaml`](references/component-map.example.yaml); open it when an entry's structure is unclear.

## 6. Hand back the resolved vocabulary

Return, for the concern at hand, the resolved terms, the sanctioned folders and naming convention, and the testing tools and delivery style. This is the vocabulary the rest of the work uses, and recording it is what lets a later reviewer check the change against the project's map rather than against the framework's defaults.

## When this skill does not apply

**Deciding whether a concept should exist, or where a boundary belongs.** This procedure resolves whose words are used; the architecture rules in this plugin decide what the words should describe. A question about aggregates, services or boundaries is theirs, in the project's resolved vocabulary.

**Writing or changing the map itself.** This skill reads a project's map. Proposing entries for it, or amending it, is a change to the project the owner consents to, not something an agent does as a side effect of resolving a term.

**Code the project did not author.** Generated files, vendored dependencies and framework scaffolding carry their producer's vocabulary. Resolving them against the domain's glossary and renaming them is out of scope; the map governs the domain model the team owns.

**A greenfield tree with no stated anything.** When step 1 genuinely finds no map and no conventions, there is nothing to resolve against, and the framework defaults apply throughout. Record that the project was silent and proceed; do not manufacture a map to read.

<!--
Directory layout:

skills/reading-the-component-map/
├── SKILL.md
└── references/    the worked schema example a step opens

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
