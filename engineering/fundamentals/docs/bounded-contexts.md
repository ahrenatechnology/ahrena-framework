---
id: bounded-contexts
type: doc
clade: engineering
subclade: architecture
title: The context, the layout and the vocabulary
summary: Why a bounded context is a directory, how that layout supplies the layer map the SOLID rule was missing, why a list of vendor tokens is admissible where a list of generic nouns is not, and what the four audit fields buy.
references:
  - rules/domain-model.md
  - docs/solid.md
  - docs/simplicity.md
  - docs/clean-code.md
---

# The context, the layout and the vocabulary

This is the companion to [`rules/domain-model.md`](../rules/domain-model.md). The rule states five conditions and names what decides each one; this explains what they protect, where the layout and the field set came from, and the cases where each guardrail is wrong.

## Why a bounded context is a directory

A bounded context is a boundary inside which one model holds and one vocabulary means one thing. "Customer" in billing and "customer" in support are two concepts with one word, and the whole value of the idea is refusing to merge them.

That is a modelling claim, and modelling claims are not enforceable. What is enforceable is a layout, so the rule makes one:

```
<context>/
    domain/          the model: types, invariants, the language the business speaks
    application/     use cases: sequences over the domain, one per thing a user does
    adapters/        everything that talks to something outside
```

The directory is not the context. It is the place the context is written down, and it is what lets a script say anything at all.

**The pragmatic argument for choosing a layout rather than describing one.** A configurable layer map is a file, and a file drifts from the tree it describes. When it drifts the check keeps passing, on the wrong partition, and nobody notices because a green check is indistinguishable from a correct one. A convention cannot drift from itself: the directory a module is in is the claim about which layer it belongs to, and moving the file is the only way to change the claim.

The cost is real and it is stated in the rule's boundary: a project laid out differently gets nothing from the detector. That is the trade — a check that works with no configuration for projects that adopt the convention, and no check at all for those that do not, rather than a configurable check that silently describes the wrong tree.

## What this closes

`docs/solid.md` says of dependency inversion that the layer map "is the input the condition needs and this plugin does not ship one, so a reviewer supplies it". `docs/simplicity.md` says it twice, once in its own boundary section: "Until a bounded-context layout artifact exists, a reviewer supplies the map and the condition is only as good as that map."

Condition 1 of `rules/domain-model.md` is that artifact, and the map it supplies is three directory names. Within a project that adopts the layout, condition 6 of `rules/solid.md` is no longer a reviewer's judgment about which modules are policy — it is a path check, and the script runs it.

What remains a reviewer's job is the harder half. The layout says which modules are policy; it does not say whether the right things are in them. A `domain/` directory full of anaemic record types with the logic in `application/` satisfies every path check and has no domain model in it. The map makes the mechanical half mechanical, which is all a map can do.

## Why a vendor list is admissible where a naming list is not

`docs/clean-code.md` refuses to ban `data`, `info`, `temp`, `manager` and `helper` by list, and argues the position at length: a list like that is wrong in both directions, because `data` is the correct name for a parser's payload and a `TemplateManager` that manages templates is named accurately, while the worst names in any codebase are plausible, specific and false.

Condition 2 of `rules/domain-model.md` is a list of tokens matched against names. It has to answer that objection rather than ignore it, and the answer is a difference in kind.

**A generic noun's correctness depends on context; a vendor token's meaning does not.** `data` is a word in English whose fitness is decided by what the thing is. `redis` is the name of a product. `dto` is the name of a layering technique. `avro` is the name of a serialisation format. None of them denotes anything a business does, so a domain name containing one is a name that points outside the domain — which is the exact state the condition describes, not a proxy for it.

**The list is closed and factual rather than judgmental.** Adding to it requires naming a product, protocol, format or technique. There is no argument to have about whether `kafka` belongs, in the way there is an endless argument about whether `manager` does.

**The false positive it does have is a different shape, and it is nameable in advance.** The generic-noun list is wrong unpredictably, case by case. This list is wrong in exactly one situation — when the technology *is* the business — and that situation is a property of the whole context rather than of an individual name. A monitoring product, a data-integration platform and a database vendor each know that about themselves on day one, and the exclusion is one path written down once.

That is the whole argument, and it is worth being suspicious of, because "my list is different" is what everyone says about their list. The check on it is the exclusion: if a project finds itself excluding names one at a time rather than contexts one at a time, the list is behaving like the one `docs/clean-code.md` refused, and it should be dropped the way `docs/simplicity.md` records the indirection condition being dropped.

## What the leak actually looks like

The vendor token is the visible end of a leak and the least harmful end of it. The rule's boundary section says so; this is the longer version, because a reader who fixes only the names has fixed the symptom.

A domain model leaks in three stages. First the names go: `OrderDto`, `SqlOrderGateway`, `json_payload`. Then the shapes go: a type per table rather than per concept, a foreign key modelled as an integer because that is what the column holds, a collection loaded eagerly because the query does. Then the behaviour goes: the invariants move out of the model into the service that saves it, because that is where the transaction is, and what is left is a bag of fields with getters.

The third stage is the one that costs, and the model that reaches it usually has clean names, because somebody did a renaming pass. The condition catches the first stage, which is cheap to fix and is a reliable early signal. The reviewer's question for the third is the only one that works: **would someone who does this business for a living recognise this type, and could they tell you whether a rule in it is right?** A model that cannot be read back to a domain expert is not a domain model, whatever its directory says.

## The entity contract

**Identity belongs to the root.** An aggregate is a consistency boundary with one thing the outside world addresses, and that thing carries the identity. Entities inside it are reached through the root, which is why giving each of them a globally addressable identifier dissolves the boundary: once anything outside can hold a reference to an inner entity, the root can no longer enforce an invariant across the aggregate, because the inner entity can be changed without going through it.

**The audit stamp is four fields, and the number is argued rather than chosen.** An audit trail answers two questions — when did this change, and who changed it. Every stored record has two events worth recording under that heading: it came into existence, and it was last changed. Two questions times two events is four fields, and there is no fifth that follows from the same reasoning.

That is also why `deleted_at` is not in the set, although it is in most versions of this contract. Soft deletion is a storage strategy: it answers "how do we keep the row", not "when did this change and who changed it". A domain that does not soft-delete would carry a field that is always empty, and a field that is always empty is a field readers learn to ignore — including on the records where it is not.

**What the four do not give you.** They record the last change, not the history of changes. A domain that needs to answer what a record looked like in March needs an event log or a temporal table, and a stamp is not a cheap version of one — it is a different thing that answers a smaller question well. Treating the stamp as an audit log is the mistake this section exists to prevent.

## `entity_type` and `domain_entity`

Two spellings were in use for one attribute, which costs more than either spelling does: every search finds half the occurrences, and every new file has to guess. The rule settles it at `domain_entity`, and the reasoning is short enough to record.

`entity_type` is two nouns from two vocabularies. "Entity" is the domain's word; "type" is the schema's. The compound reads as metadata about a row, and an attribute that reads as metadata attracts every other classification anyone later needs, so it ends up holding a mixture of the concept, the storage variant and a feature flag.

`domain_entity` names the thing the record is. It is not a classification of the row; it is the answer to "what is this". It is also the spelling that makes the wrong content obvious: nobody puts a storage variant in a field called `domain_entity` without noticing.

The rule does not say every model needs such an attribute. Most do not, and a discriminator column often arrives with a single-table storage decision that has leaked into the model — which is condition 2's subject arriving in a different disguise.

## Client names and personal data in source

**Why this is in a domain rule at all.** It looks like a security concern and it is partly one, but the reason it sits here is that it is the same defect as the vendor token, with a different thing leaking. A domain model that names a customer has been shaped by that customer. The first tenant's quirks become fields, the first tenant's workflow becomes the invariant, and the second tenant arrives to find that the model is not of the business but of one account.

**The literal is the part that is checkable, and it is also the part with the sharpest consequences.** A name, an account identifier, an email address or a national identity number written into source cannot be rotated, cannot be scoped to an environment, outlives the relationship it came from, and is copied to every machine that clones the repository. Test fixtures, seed files and migrations are where it usually is, because those feel like they do not count.

**What the detector can be.** Emails, national identity numbers and account identifiers have shapes a scanner matches; client names do not, and the list of them is the project's. So the rule names the project's scanner as the detector rather than shipping one, and the reviewer covers the rest. This is the same position `rules/contract-first.md` takes about its own conditions: a real detector the consuming project runs beats a guessed one shipped from here.

**Where it stops.** Data the system is about is not a literal in the system. A domain whose subject is people holds personal data at runtime and should. And a public identifier that is a fact about the world — a regulator's registration number, a statutory code — is not a client datum, and treating it as one makes the code worse for no gain.

## What these detectors are evidence of

`docs/clean-code.md` and `docs/value-semantics.md` each report a false-positive count measured over 2,291 lines of the framework's own Python. This document cannot, for a reason that is structural rather than an oversight: that corpus is two gate scripts and their tests, it has no `domain/` directory, and both shipped conditions key off one. Running them returns zero findings and the number carries no information.

What backs them is the fixture suite, which pins each condition in both directions — the domain module that imports an adapter and the one that imports its own siblings, the vendor token inside `domain/` and the same token outside it — and the carve-outs, which are stated in the rule before they are encountered rather than after.

**What would change the picture** is a run against a service laid out this way. Until then these two are held to a lower standard of evidence than the detectors in `hooks/check-structure.py` that were measured, and a reader wiring the hook into a pipeline should know which is which. `rules/cross-cutting-concerns.md` carries the same caveat.

## Where this stops

**This document does not teach DDD.** Context mapping, the strategic patterns and ubiquitous language as a practice are assumed rather than taught. Evans' *Domain-Driven Design* and Vernon's *Implementing Domain-Driven Design* are the sources. The tactical vocabulary this plugin does state — where the consistency boundary falls, what may cross it and what an event carries — is `rules/aggregates.md`, with `docs/aggregates.md` behind it; this document covers the layout the context sits in and the contract an entity owes.

**It does not decide how contexts integrate.** Shared kernel, customer-supplier, conformist, published language and the rest are the question of what happens between two contexts, and the rule says only that a context does not reach into another's internals. The integration patterns are a strategic decision per pair, and this plugin has no basis to pick one.

**It does not cover events as a modelling device.** Domain events are how most of these contexts would communicate. Their place in the model — what an event carries, and why it is inseparable from the boundary it leaves — is now `rules/aggregates.md`; their shape on the wire remains `rules/contract-first.md`'s subject; and what happens to one when it crosses from this context into another is the integration question the previous paragraph declines.

**It says nothing about how big a context should be.** That is the question everyone asks first and it has no threshold. A context is as large as one model that holds, and finding the seam is done by listening to where the same word starts meaning two things — which is why the practice is a conversation and not a metric.
