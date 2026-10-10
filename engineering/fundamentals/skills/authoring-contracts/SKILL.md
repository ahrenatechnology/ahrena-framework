---
name: authoring-contracts
description: Use when a published surface is about to gain or change an operation or an event and the contract has to exist first: an OpenAPI document and an event schema, written and reviewed before the code.
type: skill
clade: engineering
subclade: architecture
references:
  - rules/contract-first.md
  - rules/aggregates.md
  - docs/contract-first.md
  - skills/detecting-contract-breaks/SKILL.md
  - skills/comparing-published-contracts/SKILL.md
---

# Authoring contracts

`rules/contract-first.md` says the contract is an input to the build and never an output of it. That is a statement about order, and an order is only kept by a procedure: this is the one that produces the document the rule's five conditions are then decided against.

The end state is specific. A contract is committed, a consumer has read it, and the code that implements it does not exist yet. Every step works towards that moment or protects it afterwards.

The rule picks no contract language and [`docs/contract-first.md`](../../docs/contract-first.md) says why. A procedure has to write something, so this one writes OpenAPI for a request and response surface and JSON Schema over a CloudEvents envelope for an event. Step order holds for any other language; the two skeletons and the check do not.

## 1. Decide that the surface is published, and stop if it is not

A surface is published when someone outside the team that owns it can call it or subscribe to it without asking first. That is the test `skills/detecting-contract-breaks/SKILL.md` uses, and it is used here for the same reason: it is the only case in which the contract can disagree with the code on somebody's behalf.

`docs/contract-first.md` lists three cases where authoring a contract is ceremony: one consumer inside one deployment unit, a framework that describes a surface only from its handlers, and an exploratory service nobody consumes yet. In the first and the third, stop and say which case it is. In the second, the contract is still written by a person and step 8 is what enforces it.

## 2. Name the operations and the events before writing a schema

List them in the consumer's vocabulary, one line each, and get the list agreed before any field exists. A field argued over inside an operation nobody needed is the expensive way to find that out.

**An operation is something a consumer does**: place an order, cancel it, read it back. Take the list from what the consumer is trying to get done, not from the tables or the handlers that will serve it, because a surface derived from the storage publishes the storage. Give each one an identifier now. It is the name a contract test will carry, and condition 3 of the rule is a set difference over those names.

**An event is a fact the domain announces**, named in the past tense for the state change that produced it: an order was placed, an order was cancelled. One type per fact. A single "order changed" event with a field saying what changed makes every consumer parse the payload to learn what happened, which is the question the `type` attribute exists to answer.

Then separate the events anyone outside can subscribe to from the ones that never leave the deployment unit. Only the first set gets a schema here; the rule's boundary section says why an envelope around an internal message buys nothing.

## 3. Write the OpenAPI document

Copy `references/openapi-skeleton.json` and replace its resource. It is three operations over one resource, small enough to read in a sitting, and it shows the four things every operation declares: its `operationId`, what the request must carry, what a success returns, and what a refusal returns.

Three decisions deserve more time than the rest, because condition 5 makes each a version event to undo:

- **What a request requires.** A field added as required later is a break, and one made optional later is not. Require what the operation cannot run without.
- **What a response promises.** A field removed later is a break, and one added later is not. Return what a consumer needs now.
- **Every enum and every range.** A value removed or a range tightened is a break.

Declare the refusals alongside the successes. A consumer writes as much code against a 404 and a 422 as against a 200, and an error response the document does not declare is one the contract tests in step 7 cannot hold the service to.

This step chooses no status-code policy, pagination scheme, naming convention or error format. The skeleton's error body is the problem-details shape only so that it has one.

## 4. Write the event schema

Copy `references/event-skeleton.json`, one file per event type. It is a JSON Schema for the whole event as a consumer receives it: the CloudEvents envelope with the payload under `data`.

**The envelope requires `specversion`, `id`, `source` and `type`.** That is condition 4, and the set is the specification's. Pin `type` to the one value this schema describes, so a consumer can dispatch on it and a validator can tell two events apart.

**The payload carries the identity of the aggregate and the time it happened.** Condition 5 of `rules/aggregates.md` requires both on every domain event. Past those two, the reasoning in step 3 applies unchanged: a consumer can absorb a field that appears and cannot absorb one that goes.

**One schema per event, whatever carries it.** The same document describes the event on the bus, in a webhook and on a server-sent stream. A second schema for the synchronous surface is the split condition 4 exists to prevent.

Where the project keeps an AsyncAPI document, it is where channels and bindings are declared, and its message payloads point at these schemas instead of restating them.

## 5. Check what the later conditions key on

```sh
python3 scripts/check-contract.py --openapi openapi.json --event order-placed.json
```

It decides two things: every operation declares an `operationId` that no other shares, and every event schema requires the four envelope attributes. It exits 0 when both hold, 1 when one does not, and 2 when a document could not be read. `scripts/test-check-contract.py` is its suite, and it runs the check against both skeletons as shipped.

It reads JSON, because the standard library reads nothing else and this plugin takes no dependencies. That is also why the skeletons are JSON. A project that authors in YAML keeps doing so and converts with its own toolchain before the check; a YAML document handed over directly is reported as not checked, which is not a pass.

It is not a validator for either specification. Whether the document is valid OpenAPI or a valid JSON Schema is decided by the specification's own tooling, and the project picks which.

## 6. Put the contract up for review before the implementation exists

Commit the documents on their own and open the review with nothing else in it. The readers who matter are the consumers, and what they are asked is narrow: can you build against this, and is there anything here you would have to work around.

This is the step the rule exists for and the one that gets skipped. A contract reviewed beside its implementation is approved by people reading the code, and a disagreement at that point costs a rewrite, so it tends not to be raised.

## 7. Build from the contract, in one of the two permitted directions

Condition 1 allows two. A generator reads the contract and emits code, or a test reads the contract and asserts that hand-written code conforms. Either way the committed document is the input.

Write one contract test per `operationId` as the implementation lands, which is condition 3, and validate a captured event against its schema inside the test for the operation that emits it, which is condition 4. The identifiers and schemas from steps 3 and 4 are what those tests name.

## 8. Change the contract first, every time after

A change to the surface starts as an edit to the committed document, goes through step 6, and reaches the code after. The order is the same on the fortieth change as on the first, and that is all "keeping the contract current" means.

Two procedures hold that order in place once nobody is watching. `skills/comparing-published-contracts/SKILL.md` compares what the running service serves with the committed document, so a change made in the code first shows up as a difference. `skills/detecting-contract-breaks/SKILL.md` reads an edit that removes or narrows something and asks whether it ships as a version.

## When this skill does not apply

**A surface that is not published.** Step 1 ends there, and an internal interface with a type checker is the honest version.

**A contract in another language.** Protobuf, Avro and a GraphQL schema all satisfy the rule, and steps 1, 2, 6, 7 and 8 hold for them. The skeletons and the check are OpenAPI and JSON Schema and say nothing about the others.

**Choosing the conventions of the surface.** Resource naming, status codes, pagination, error bodies and authentication are decisions the project makes and declares in the document. This procedure says when they get written down, not what they are.

**Choosing how a version is carried.** Condition 5 requires a version event and declines to pick the mechanism, and so does this.

**Reviewing a change to a contract that already exists.** That is `skills/detecting-contract-breaks/SKILL.md`, whose input is the base version and the head.
