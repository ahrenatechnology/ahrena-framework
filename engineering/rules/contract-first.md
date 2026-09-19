---
id: contract-first
type: rule
clade: engineering
subclade: architecture
title: The contract is the source
statement: The contract is authored, the code is derived from it or validated against it, and every operation it declares has a test that exercises it.
enforcement: judgment
references:
  - docs/contract-first.md
---

# The contract is the source

Five conditions. Each names a detectable state and what decides it, and every one of those detectors is a job the consuming project runs or a document a reviewer reads — none of them is a parser this plugin could ship. The final section says why that makes this a judgment rule. `docs/contract-first.md` explains what each condition prevents, where the thresholds came from, and the situations in which a generated contract is the right answer.

The subject is direction. A contract can be an input to the build or an output of it, and the two arrangements produce the same artifact with opposite properties. An authored contract is a decision: it can be reviewed before code exists, disagreed with, and held stable while the implementation behind it is replaced. A generated one is a report: it describes whatever the code currently does, it agrees with the code by construction, and it therefore cannot detect the change that broke a consumer — because the change rewrote the contract too.

None of these conditions adds an abstraction, so the abstraction trigger in condition 1 of `rules/yagni.md` does not gate any of them. The question it raises anyway is answered in the boundary section below, because a contract with one consumer looks like the exact shape that rule deletes and is not.

## Conditions

1. **No build step takes code as input and the contract as output.** The state is a generator whose source is the application's types or handlers and whose product is the committed OpenAPI document, event schema or IDL. The permitted directions are the other two: a generator reading the contract and emitting code, or a test reading the contract and asserting the code conforms. Decided by a reviewer reading the build configuration, and by a pipeline that fails when the generation step's inputs include application source. There is no threshold; the direction is binary.

2. **The published contract and the committed contract are byte-equal after canonical serialisation.** Canonical means keys sorted and whitespace normalised, so formatting is not a difference and nothing else is forgiven. Decided by a pipeline job that starts the service, fetches the description it serves, canonicalises both sides and diffs them. Equality rather than a tolerance is deliberate: a semantic-diff allowance is where drift accumulates, because every individual difference is small at the moment it is introduced.

3. **Every operation the contract declares is exercised by at least one contract test.** The threshold is all of them. Decided by the set difference between the operation identifiers in the contract and the operation identifiers the test suite names — a script the consuming project owns, because it needs to know which file is the contract and how its tests are addressed. `docs/contract-first.md` argues why complete coverage is the only figure that carries information when the unit is an operation.

4. **An event published on any surface carries the CloudEvents required attributes.** Those are `specversion`, `id`, `source` and `type`, and the set is the CloudEvents 1.0 specification's, taken unchanged. The condition applies to the synchronous surface — server-sent events, webhooks, a streaming endpoint — and not only to the asynchronous bus, because a consumer reading the same domain event over two transports should not have to parse two shapes. Decided by the specification's own JSON Schema, run against a captured event inside the contract test that condition 3 requires.

5. **A change that removes or narrows anything in the contract ships under a new version.** The state is a diff against the previous committed contract containing any of: an operation deleted, a field removed from a response, a field added as required to a request, an enum value removed, or a type narrowed. The classification is the standard breaking-change set, taken from the schema-diff tools rather than invented here. Decided by such a tool in the pipeline, or by a reviewer comparing the two documents where none is wired.

## Where this stops

**Condition 1 does not forbid generating the contract at all.** It forbids the committed contract being the generated one. Emitting a description from a running service is useful — it is how condition 2 gets the other side of its diff — and the distinction is which of the two artifacts is under review and which is derived for comparison.

**Condition 1 does not reach a codebase whose framework offers no other route.** Some stacks can only describe a surface through decorators on the handler, and rewriting the stack to satisfy a rule is not a trade this plugin will ask for. The fallback is condition 2 applied against a contract that a person edits and a test enforces: the generated description is diffed against the reviewed one, and a difference fails the build. That recovers the property that matters — a contract change is a visible, reviewable event — without the generation direction the condition prefers.

**Condition 2 does not reach a surface that has no machine-readable description.** A library's public API, a CLI's arguments and a database schema consumed by another team are all contracts and none of them serves a document to fetch. The condition is written for the surfaces that do; for the others the property survives and the detector does not, which means a reviewer.

**Condition 3 asks for complete coverage and that number is only defensible because of the unit.** Operations are enumerable, small in number, and individually meaningful; a line-coverage target of 100 is a bad idea for reasons that do not apply here. What the condition does not claim is that a test per operation is *sufficient*: one call exercising the happy path leaves every error response, every boundary value and every authorisation case untested, and the contract declares those too. Complete operation coverage is the floor the gate can decide, not the coverage the surface deserves.

**Condition 4 does not reach an internal event.** An event that never leaves the process, or that crosses a boundary inside one deployment unit with no other consumer, gains nothing from an envelope specification, and a domain that wraps every internal message in CloudEvents has bought the ceremony without the interoperability. The condition is about published surfaces, and the test of whether a surface is published is whether anyone outside the team can subscribe to it.

**Condition 4 takes the required set and stops there.** CloudEvents also defines optional attributes and extension contexts, and a project that standardises on some of them is doing something sensible that this rule has no opinion about. Mandating more than the specification requires would be this framework inventing a dialect and calling it a standard.

**Condition 5 does not reach a change that is breaking and correct.** A contract that documents a behaviour the service never had is wrong, and fixing it narrows the contract. Versioning that would preserve a fiction nobody implements. The rule's position is that the change still ships as a version event — announced, dated, and visible to consumers — rather than silently, and the version number is a judgment the person who owns the surface makes once.

**Condition 5 does not decide the versioning scheme.** Path versions, header negotiation, a schema registry's compatibility mode and a date-stamped revision are all answers, and they have different costs in different deployments. The condition requires that a breaking change be a version event; which mechanism carries it is a decision the consuming project makes.

**This rule declares judgment rather than a hook, and the reason is not effort.** Every detector named above is real and runnable, and none of them is a parse over source. Each needs an input this plugin does not have and cannot guess: which file is the contract, which surfaces are public, which generator runs, and where the previous version lives. A hook claiming to decide conditions 1 to 5 would have to hard-code a project layout, and the first project that arranged itself differently would get a gate that is confidently wrong — which `docs/simplicity.md` records as the failure that gets gates switched off, and it cost the KISS rule a condition. The search for a parser-decidable fragment turned up only framework-specific shapes, and a detector for one web framework belongs with the plugin for that framework. So the rule takes the judgment route, its statement is injected, and the detectors it names are jobs the consuming project wires into its own pipeline. `rules/solid.md` reaches the same conclusion from a different direction, and its final section sets out the trade.
