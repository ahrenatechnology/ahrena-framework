---
id: component-map
type: doc
clade: engineering
subclade: architecture
title: The component map
summary: The schema of the per-project manifest an agent reads before naming or creating anything — its glossary, components, conventions, testing lanes and delivery style — and the rule that the project's values override the framework defaults.
references:
  - rules/ubiquitous-language.md
  - docs/ubiquitous-language.md
---

# The component map

This defines the component map: the one file a project writes to tell an agent how it speaks and how it is built, so that [`rules/ubiquitous-language.md`](../rules/ubiquitous-language.md) is satisfied by reading a manifest rather than by guessing. [`docs/ubiquitous-language.md`](ubiquitous-language.md) argues why an agent conforms to a project's vocabulary at all; this says what the agent reads to do it.

The map is **per project and not shipped by the framework.** The framework ships the schema and the defaults; each project writes its own map, in its own words, and commits it to its own repository. There is no framework-wide map, because the whole point is that every project differs. A project with no map is a project that has said nothing, and the agent then uses the framework defaults throughout — which is a valid state, not an error.

## Precedence, stated once

Every key below is read under one rule: **a value the project states wins; the framework default applies only where the project is silent.** The map is where a project states its values. An absent key, or an absent entry within a key, is silence, and silence resolves to the default. A present entry overrides the default for that project, and is never merged with it. The sections below note, per key, what the default is when the project says nothing.

## `glossary` — canonical term to project term

A flat map from the framework's canonical term to the word this project uses for it. This is the heart of the map: it is what lets an agent resolve a concept it knows by one name to the name the project sanctions.

```yaml
glossary:
  use_case: workflow
  aggregate: record
  repository: store
```

The left side is always the framework's canonical term, drawn from the vocabulary the architecture rules use. The right side is the project's word, taken from the project's own code and stakeholders. An agent resolving `use_case` reads `workflow` and uses `workflow` everywhere — in folders, in types, in prose. **Default when silent:** the canonical term itself. A concept absent from the glossary is named by its canonical term, because the project has sanctioned no alternative.

## `components` — the parts of the system

A list of the system's components. Each entry names a part, says which concern it serves, where it lives, what human language its domain is written in, and what it is built with.

```yaml
components:
  - name: api
    concern: backend
    paths: [services/api]
    language: pt-BR
    stack: [nestjs, prisma]
```

`concern` is one of `backend`, `frontend` or `data`. `paths` is the list of directories the component occupies, already in the project's own layout. `language` is the natural language of the domain vocabulary in that component — a Brazilian fintech's backend may think in `pt-BR` even when its code is English. `stack` is the frameworks and libraries in use, which tell an agent which conventions and testing tools actually apply. **Default when silent:** the agent treats the whole repository as one unlabelled component and infers concern and stack from what it finds, which is strictly worse than being told.

## `conventions` — how the project is laid out

The structural rules the project already follows, expressed in the project's translated terms, not the framework's.

```yaml
conventions:
  layout: feature-first
  folders: [workflows, records, stores]
  naming: snake_case
```

`layout` names the organising principle — `feature-first`, `layer-first`, or whatever the project calls its own. `folders` is the set of top-level folders the project sanctions, written in the vocabulary from `glossary`; this is the list an agent checks before it dares create a directory, and a folder not on it is a folder the agent does not invent. `naming` is the identifier convention. **Default when silent:** the framework's default layout and the canonical folder names, used only because the project named none.

## `testing` — the lanes and their tools

A map from testing lane to that lane's philosophy and tools. The lanes are `contract`, `workbench`, `visual`, `e2e`, `a11y` and `quality`. Each is an **overridable default**: the framework has an opinion about each lane, and the project's entry replaces that opinion for the project.

```yaml
testing:
  contract:
    philosophy: author the contract, test against it
    tools: [pact]
  e2e:
    philosophy: critical paths only
    tools: [playwright]
```

An entry carries `philosophy`, one line on how the project treats that lane, and `tools`, the list it uses. **Default when silent:** the framework's default philosophy and tools for that lane apply. These are defaults in the strong sense — a project that states `contract.tools: [pact]` gets Pact, and the framework's default contract tool is discarded for that project, not run alongside it.

## `delivery` — how the system is reached

A single value naming the primary delivery surface: one of `rest`, `grpc`, `graphql`, `cli` or `tui`. It tells an agent what kind of contract the system exposes and therefore which contract conventions apply.

```yaml
delivery: rest
```

**Default when silent:** `rest`, because it is the most common surface and the safest assumption to state out loud so a project can correct it.

## A map in full

The keys compose into one file. A minimal real map states only what differs from the defaults and lets silence carry the rest.

```yaml
glossary:
  use_case: workflow
components:
  - name: api
    concern: backend
    paths: [services/api]
    language: pt-BR
    stack: [nestjs]
conventions:
  folders: [workflows]
  naming: snake_case
testing:
  e2e:
    philosophy: critical paths only
    tools: [playwright]
delivery: rest
```

## Where this stops

**The schema is fixed; the values are not.** This document defines the keys and their shapes. It says nothing about which glossary entries, components or tools a given project should have — those are the project's to state, and an agent never writes them on the project's behalf without the project's consent.

**It is not a configuration format for the framework.** The map configures how an agent reads one project. It does not turn framework rules on or off, and a project cannot use its map to opt out of an architecture rule; the map carries vocabulary and layout, not exemptions.

**It does not say how the map is located.** Where the file sits and how an agent finds it is procedure, and that belongs to the skill that reads it rather than to this schema. [`rules/ubiquitous-language.md`](../rules/ubiquitous-language.md) names the reading skill.

**Silence is defined here but judged there.** This document defines an absent key as silence resolving to a default. Whether a project is genuinely silent or the agent simply failed to read the map is a distinction the reading procedure draws, not the schema.
