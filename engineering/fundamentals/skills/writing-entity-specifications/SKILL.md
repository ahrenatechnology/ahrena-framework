---
name: writing-entity-specifications
description: Write the specification of one aggregate root, entity or value object at its home in the consuming project. Use when an entity is modelled before its code, when one changes its fields, invariants or events, or when a context has code and no written model.
type: skill
clade: engineering
subclade: architecture
references:
  - rules/specification-homes.md
  - rules/domain-model.md
  - rules/aggregates.md
  - rules/domain-services.md
  - rules/contract-first.md
  - docs/specification-homes.md
---

# Writing entity specifications

An entity specification is one file that says what a domain type is, what is always true of it and what leaves its boundary, in words the business would sign. The shape is fixed by `rules/specification-homes.md` and a hook decides it. What the hook cannot decide is whether the answers are the model's, and steps 1, 4 and 5 are where that is settled.

[`docs/specification-homes.md`](../../docs/specification-homes.md) says why the address is fixed and what each section is there to make somebody answer. Read it the first time.

## 1. Name the context and classify the type

Two answers before a file exists.

**The context** is the bounded context the type belongs to, under the name its source directory carries. A type that seems to belong to two is two types sharing a word, and each gets its own file in its own context.

**The classification** is `aggregate root`, `entity` or `value object`. Ask whether anything outside addresses it directly: if so it is a root. If it has a lifecycle and is only ever reached through a root, it is an entity of that aggregate. If two instances with the same contents are the same thing, it is a value object.

The failure that recurs here is classifying by the table it is stored in. A row with a primary key is not thereby a root, and `docs/specification-homes.md` says why the sections mean different things under each answer.

## 2. Find its home

The file is `docs/<context>/entities/<entity>.md`: the context directory in kebab-case, and the entity's PascalCase name in kebab-case. `ScheduledTransfer` in the context `payments` is:

```
docs/payments/entities/scheduled-transfer.md
```

If the file is already there, this is an edit and step 7 is the one that applies. If a directory named `entities` sits directly under `docs/`, the hierarchy is inverted and condition 1 of `rules/specification-homes.md` fails it; move it under its context before adding to it.

## 3. Copy the template and fill it

`references/entity-specification.md` is the skeleton, the prompt for each part and a filled example. Copy what is between its first two rules, replace everything in braces, and keep all seven sections. One with nothing to say reads `None`.

Write `Why it exists` first and show it to somebody who knows the domain before filling the rest. If they do not recognise the type from those sentences, the table under it is describing storage, and no later step repairs that.

## 4. Separate the invariants from the business rules

List every rule the business states about this type, then sort each one.

An **invariant** is true in every state and admits no exception. A **business rule** governs one operation or transition. "The total is never negative" is the first; "an order can be cancelled until it ships" is the second.

Then read each invariant for the roots it names. One that names only this aggregate stays. One that names a second root is the finding this step exists to produce, and it has three honest outcomes:

- the two are one aggregate, and condition 1 of `rules/aggregates.md` moves the boundary
- the two may disagree for a while, and condition 4 of that rule wants the owner, the window and the repair written down as a business rule
- it is one rule of the business that belongs to neither, and `rules/domain-services.md` says where it goes

Do not keep it in `Invariants` unresolved. A specification that lists an invariant its aggregate cannot enforce is promising something the code will not do.

## 5. Name what crosses the boundary

In `Relationships`, every target is `part` or `identity`. A root held as anything but its identifier is condition 3 of `rules/aggregates.md`, caught here for the price of one table cell.

In `Events`, name each fact in the past tense and say what it carries. The identity of the root and the time are owed by condition 5; a whole entity in the payload is refused by condition 6.

Stop at the name. The event's schema and the operations that expose the entity are contracts, authored under `docs/<context>/contracts/` and governed by `rules/contract-first.md`. A payload copied into this file is a second source that nothing validates.

## 6. Run the hook

```sh
python3 engineering/fundamentals/hooks/check-specifications.py
```

Run it from the root of the project, or pass the `docs` directory as the argument. It decides the seven conditions of `rules/specification-homes.md` over every context, so it also finds the placeholder left in a neighbour's file.

## 7. Change it with the model

A change to the fields, the invariants or the events of a type changes this file in the same pull request, before or with the code. `INV` and `BR` numbers are never reused: a rule that is dropped keeps its number and says it was removed, so a test or an error row that cites it does not silently point at another rule.

A specification that trails the code is a report, and the argument `rules/contract-first.md` makes about a generated contract applies to it unchanged.

## When this skill does not apply

**A contract.** An API description, an event schema or an IDL is authored under `docs/<context>/contracts/`, and `rules/contract-first.md` governs it. This skill names the events and stops.

**A capability or a metric.** Both have a home in `rules/specification-homes.md` and no shape in this plugin. Writing one from this template produces an entity table about something that is not an entity.

**A read model, a request body or a persistence record.** None is a domain type. A projection is derived from entities that have their own files, and a payload is the contract's. Specifying them here is how a model ends up shaped by its storage, which is the leak condition 2 of `rules/domain-model.md` exists to catch.

**Deciding where the boundary goes.** Step 4 reports that an invariant spans two roots; it does not redraw the aggregate. That decision is made against `rules/aggregates.md` with the people who own the model, and the specification is rewritten after it.

**Recording why a modelling choice was made.** This file says what the type is. Why the alternative lost is a decision record, and it lives beside the project's other records, not under a context.
