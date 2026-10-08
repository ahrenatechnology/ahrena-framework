---
id: specification-homes
type: doc
clade: engineering
subclade: architecture
title: Why a specification has one address
summary: Why specifications sit under the context and not under their kind, why the layout is fixed, why four kinds, and what each of the entity specification's seven sections is there to make somebody answer.
references:
  - rules/specification-homes.md
  - rules/domain-model.md
  - rules/aggregates.md
  - rules/contract-first.md
  - docs/bounded-contexts.md
  - docs/aggregates.md
  - docs/patterns.md
---

# Why a specification has one address

This is the companion to [`rules/specification-homes.md`](../rules/specification-homes.md). The rule states where each kind of specification sits and what an entity specification carries; this says why, and does not repeat the table.

## Why the address is a rule at all

A specification that cannot be found is worse than none, because the next author writes a second one. That is the whole defect, and it is why location passes the test `foundation/docs/artifact-model.md` sets for a rule: a document in the wrong place is not merely different, it is a document the reader who needed it did not read.

The second reason is the one [`docs/bounded-contexts.md`](./bounded-contexts.md) gives for the source layout. A convention is checkable where a description is not. Nothing can decide whether "the entity documentation" is complete; a script can decide whether the files under `docs/<context>/entities/` carry their sections, and anything built later on the assumption that a specification exists — a readiness check, a review step — has a path to look at and not a search to run.

## Why the context comes first

`docs/<context>/<kind>/` and `docs/<kind>/<context>/` hold the same files. They differ in what a reader does with them.

A change is almost always a change to one context: an entity gains a field, the contract that exposes it gains a property, the event that announces it gains a payload member. Under the context those are three files in one directory tree and one glob in a review. Under the kind they are three trees, and the context — the unit [`rules/domain-model.md`](../rules/domain-model.md) makes a directory in source for exactly this reason — has no directory in the documentation at all.

It also keeps the two trees parallel. A context is `billing/` in source and `docs/billing/` here, so the name is learned once.

## Why the layout is not configurable

The predecessor of this framework let a project declare its specification paths in a settings file, and then removed the keys. The reason is the one `docs/bounded-contexts.md` gives about a configurable layer map: the file drifts from the tree, the check keeps passing against the wrong place, and a green check is indistinguishable from a correct one.

The cost is real. A project with another layout gets nothing from the hook. It also fails nothing, and that asymmetry is the point: the convention is an offer, not a migration.

## Why four kinds, and why two of them are empty

**Entity and contract are the two the plugin already has rules about.** The model is [`rules/domain-model.md`](../rules/domain-model.md) and [`rules/aggregates.md`](../rules/aggregates.md); the surface is [`rules/contract-first.md`](../rules/contract-first.md). Each needed somewhere to be written down before code, and neither rule said where.

**`contracts/` is one directory, not one per format.** The predecessor had `oas/` for the API description and `events/` for the events. `rules/contract-first.md` treats an OpenAPI document, an event schema and an IDL as one thing — an authored contract that code is derived from or validated against — and a directory named for a format is a name the first project on another format has to work around. What goes inside, and how it is named, is that rule's subject and the project's.

**Capability and metrics are named so that they are not chosen twice.** Nothing in this plugin says what a capability specification contains or how a success measure is written. Their addresses are fixed anyway, because the alternative is that whatever defines them later also picks a location, and the layout then has two authors.

**There is no single domain-model document.** The model is spread across the entity files, deliberately. One file for the whole context is the shape that is written once, at the start, and is wrong by the third change — because editing it means re-reading all of it, and nobody does.

## What the seven sections make somebody answer

The template is in `skills/writing-entity-specifications`. Each section exists because a rule in this plugin asks a question that has to be answered before the type is written, and an answer given in a document can be disagreed with more cheaply than one given in code.

| Section | The question | Where the answer is judged |
|---|---|---|
| **Why it exists** | Would somebody who does this business recognise it? | the reviewer's question in `docs/bounded-contexts.md` |
| **Fields** | What does it hold, in the domain's words? | conditions 2 to 4 of `rules/domain-model.md` |
| **Invariants** | What is true at every commit, and does it name only this aggregate? | condition 1 of `rules/aggregates.md` |
| **Business rules** | What does it refuse, and when? | a reader who knows the domain |
| **Relationships** | What does it own, and what does it only point at? | condition 3 of `rules/aggregates.md` |
| **Events** | What fact leaves the boundary when it changes? | conditions 5 and 6 of `rules/aggregates.md` |
| **Errors** | What is a caller told when a rule refuses? | the contract, under `rules/contract-first.md` |

**Invariants and business rules are separate on purpose.** An invariant holds in every state and admits no exception; a business rule governs a transition and may depend on the state it starts from. Kept in one list, the invariants are diluted by rules that are true only sometimes, and the list stops being what [`docs/aggregates.md`](./aggregates.md) needs it to be: the thing the boundary is drawn around. An invariant whose terms reach a second root is the most useful finding the document can produce, and it is produced by writing the list, not by any script.

**The header carries the classification because the sections mean different things under each.** A root declares identity and is what `Relationships` and `Events` are about; an entity inside an aggregate is reached through its root; a value object has no identity, no stamp and no events, and says `None` three times. The reader needs to know which before reading the table.

**What was left out.** The predecessor's template opened `Fields` with six rows every entity repeated — an identifier format, a type discriminator, a version, three timestamps including a soft-delete marker. They are one organisation's entity contract, and two of them are positions `rules/domain-model.md` refuses in its conditions 3 and 4. A `Size` column went with them: a bound belongs in the type, where it is stated once. A `References` section listing rule names went too, because every specification carried the same list.

## Where this stops

**A specification here is a document, not the Specification pattern.** [`docs/patterns.md`](./patterns.md) has an entry under that name for an object carrying one selection rule in two languages. The word is the same and nothing else is; an entity specification may well describe a type that uses one.

**It does not say when to write one.** Whether an entity earns a document before its code, and how much of a context is specified before work starts, is a process question and belongs to whatever defines readiness for the consuming project. This plugin fixes the address and the shape, and stops.

**It does not cover the documents a project keeps beside its specifications.** Decision records, guides and runbooks live under `docs/` too. Condition 2 of the rule reads only a directory that holds a kind, so they are not contexts and the hook does not see them.

**The layout is argued, not measured.** No corpus of consuming projects was run against it. What backs it is the predecessor's use of the same order and the fixture suite in `hooks/test-check-specifications.py`.
