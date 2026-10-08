---
id: contract-first
type: doc
clade: engineering
subclade: architecture
title: Why the contract is authored and not reported
summary: What a generated contract cannot detect, why complete operation coverage is the only defensible figure, what the CloudEvents envelope buys on a synchronous surface, and when generating the contract is the right answer.
references:
  - rules/contract-first.md
  - docs/solid.md
---

# Why the contract is authored and not reported

This is the companion to [`rules/contract-first.md`](../rules/contract-first.md). The rule states five conditions and names what decides each one; this explains what they are protecting, where the one contested threshold came from, and the cases where a generated contract is correct.

## The property a generated contract cannot have

The argument for generating a contract is that it cannot go stale. That is true and it is the whole problem.

A contract has one job that nothing else in the system does: it fails when the code changes in a way a consumer cannot absorb. It can only do that job if it is capable of disagreeing with the code. A contract generated from the code is incapable of disagreeing with it by construction — the breaking change rewrites the contract in the same commit, the diff shows both, and the pipeline is green. The property the team thought they were buying, that the contract is always accurate, is exactly the property that makes it useless as a gate.

Put the other way: an authored contract is a claim about what the service will keep doing. A generated one is a description of what it currently does. Only the first is a promise, and only a promise can be broken loudly.

This is a dependency-direction argument and it is the same one as `docs/solid.md` makes for policy and mechanism. The contract is policy: it is the stable thing consumers depend on. The handler is mechanism. Generating the contract from the handler points the dependency the wrong way, and the symptom is the one that argument always predicts — the stable thing changes whenever the volatile thing does.

**The generated description still has a job.** It is the other side of the diff in condition 2. Fetching what the service actually serves and comparing it against the reviewed document is how the authored contract stays honest, and it is the only way to detect an implementation that quietly stopped conforming. The rule's objection is not to generation; it is to the generated artifact being the one under review.

## Why byte-equality after canonicalisation

Condition 2 could have been written with a tolerance: ignore descriptions, ignore examples, ignore ordering, ignore additions. Every one of those exclusions is individually reasonable and the aggregate is a gate that never fires.

Drift does not arrive as one large difference. It arrives as a series of small ones, each of which is below whatever threshold was set, and the set of things a semantic diff forgives is where it accumulates. An added optional response field is harmless; twenty of them, and the document no longer describes the same service.

Canonicalisation handles the one difference that is genuinely not a difference — serialisation order and whitespace — and nothing else is forgiven. The cost is that a deliberate change now requires editing the authored contract, which is not a cost: that edit is the review the rule exists to force.

## Complete operation coverage, and why the number is 100

Condition 3 asks for a test per operation, and a threshold of 100 per cent normally deserves suspicion. It is defensible here because of the unit, and the reasoning is worth spelling out so it is not copied somewhere it does not hold.

**Line coverage has a tail and operation coverage does not.** The last few per cent of line coverage are defensive branches, unreachable error paths and generated code, so a 100 per cent target buys tests written to satisfy the metric. The set of operations in a contract has no equivalent tail: every operation is reachable by definition, because it is published, and every one is individually meaningful to a consumer.

**The units are enumerable and few.** A surface has tens of operations, not tens of thousands of lines. A figure like 90 per cent over thirty operations means three untested ones and does not say which, and the three that are untested are not random — they are the newest or the least used, which is to say the ones most likely to be wrong.

**Partial coverage of a contract has a specific failure mode.** An untested operation is one the contract claims and nothing verifies, which is the same position as having no contract for it, with the addition that consumers have been told otherwise. The value of the document is set by its weakest entry, so the only figure that carries information is the complete one.

**What complete operation coverage is not.** It is a floor. One test per operation exercising the success path leaves every declared error response, every boundary value and every authorisation rule unverified, and the contract declares all of those. The condition is written as the thing a script can decide from the contract and the test names; the coverage the surface actually needs is a judgment, and a team that treats the green check as the answer has read the rule as a target rather than a minimum.

## CloudEvents on the synchronous surface

The usual arrangement is that the message bus speaks CloudEvents and the HTTP surface does not. The bus gets an envelope because a broker and a dead-letter queue need one; the streaming endpoint gets whatever shape the endpoint's author chose.

That split costs the consumer, and the consumer is the only party who experiences it. A client subscribing to order events over server-sent events and a worker consuming the same events from the bus are reading the same domain facts in two shapes, so every piece of handling code exists twice: two deserialisers, two correlation-id lookups, two ways of asking what kind of event this is. The divergence is invisible from inside the service, because no single team ever holds both.

**What the required four buy.** `type` is how a consumer dispatches without inspecting the payload. `source` plus `id` is how a consumer deduplicates, which is what makes at-least-once delivery survivable. `specversion` is how the envelope itself can change. Those four are the ones that let generic tooling — a router, a replay buffer, a trace correlator — work without knowing the domain, and that is the reason to take a specification's required set rather than inventing four fields with the same names.

**Why the rule stops at the required set.** CloudEvents also defines optional attributes such as `subject`, `time` and `datacontenttype`, and extension contexts for tracing. A project standardising on some of them is doing something sensible. Mandating them here would be this framework publishing a dialect and calling it the standard, and a consumer written against real CloudEvents would then fail against ours — which is the interoperability the envelope existed to provide, spent.

## When generating the contract is the right answer

The rule is a hard gate and it still has cases where the inversion is correct. Naming them is what keeps it from being applied where it does damage.

**A surface with exactly one consumer, inside one deployment unit, changed by one team.** Here the contract's ability to disagree with the code buys nothing, because the change that would break the consumer is made by the same person in the same commit. Authoring a document by hand to describe an internal boundary is ceremony, and the honest version is an internal interface plus a type checker.

**A framework that offers no other route.** Some stacks describe a surface only through decorators on the handler, and the rule's fallback applies: generate, then diff against a reviewed document that a person edits. The generation direction is lost; the review event is kept, and the review event is what the rule is actually protecting.

**An exploratory service before it has consumers.** A contract is a promise, and there is nobody to promise anything to yet. The rule's cost lands the moment the first external consumer appears, and the honest position is that the inversion is a debt with a known due date rather than a permanent arrangement.

**What is not on this list** is the common one: a mature surface with several consumers where authoring the contract is felt to be slow. That is the case the rule exists for, and the slowness is the review.

## The relationship to YAGNI, which looks like a conflict

A contract with one consumer is an interface with one implementation, and `rules/yagni.md` deletes those. The conflict is apparent rather than real, and the resolution is already written down in that rule rather than invented here.

Its boundary section states that the trigger does not reach published API surface, because a library that other repositories consume has consumers the tree cannot see. A published contract is that case in its purest form: the consumers are behind a network boundary and they are the reason the contract exists. Counting them by looking at the repository returns zero and the answer is wrong.

Where the two rules genuinely meet is the single-consumer internal boundary above, and there YAGNI wins, which is why that case heads the list of exemptions.

## Where this stops

**This document does not pick a contract language.** OpenAPI, AsyncAPI, JSON Schema, protobuf and Avro all satisfy every condition in the rule, and their differences are about tooling and deployment rather than about direction. A plugin that commits to one can say more; this one has no basis to.

**It does not cover schema evolution in depth.** Compatibility modes, registry configuration, consumer-driven contracts and the mechanics of running two versions at once are a subject with its own literature, and condition 5 only requires that a breaking change be a version event rather than saying how to carry one.

**It does not cover authentication, authorisation or rate limits.** Those are declared in the same documents and they are a different subject, decided by threat modelling rather than by dependency direction.

**It ships no detector.** Every condition in the rule names a job the consuming project wires into its own pipeline, because each one needs to know which file is the contract and which surfaces are public. The rule's final section sets out why a hook that guessed those would be worse than no hook.
