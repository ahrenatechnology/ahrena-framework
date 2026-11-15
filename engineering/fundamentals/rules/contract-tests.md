---
id: contract-tests
type: rule
clade: engineering
subclade: fundamentals
title: Contracts and integrations are tested against the real thing
statement: Every operation a contract declares has a contract test, and every adapter to a database or an outside service has an integration test against the real one.
enforcement: judgment
references:
  - docs/test-discipline.md
  - docs/contract-first.md
---

# Contracts and integrations are tested against the real thing

Two conditions about the tests that sit at the edges of a system, where a unit test with a fake cannot tell whether the code works. They complete `rules/contract-first.md`, which decides the direction of a contract; this rule decides what is tested against it. The reasons and the origin of each figure are in [`docs/test-discipline.md`](../docs/test-discipline.md). Each condition carries its catalog id from the PR quality rubric (epic 323).

## Conditions

1. **CTR-1: every operation declared in the project's contract folder is exercised by at least one contract test.** The threshold is 100% of the operations. This is condition 3 of `rules/contract-first.md` stated as a rubric condition; the two are one check and this rule adds no second detector. Decided by the set difference between the operation identifiers in the contract and those the contract tests name, a script the consuming project owns because it knows which file is the contract.

2. **CTR-2: every adapter to a database or an outside service has at least one integration test that runs against the real one.** The threshold is one test per adapter. Real means a database engine the adapter will meet in production, or the provider's own test server or sandbox; a fake written for the test, a mock of the client library and an in-memory stand-in for a different engine are not. Decided by a reviewer reading each new or changed adapter for a test that starts the real dependency, and by a script the project owns that lists the adapters named in the layer map and the integration tests beside them.

## Where this stops

**CTR-1 owns no detector of its own.** It is condition 3 of `rules/contract-first.md` under its rubric id, so that rule is the one place the check is defined and a change to it changes both. What it does not cover: an operation with an untested error response or boundary value still counts as exercised once any test calls it, and a surface with no machine-readable contract owes nothing under this condition.

**One test per adapter is the floor.** It shows the adapter can reach the real thing and that its queries or calls are accepted. The adapter's branches are held by the edge coverage figure in `engineering/quality/rules/coverage-by-layer.md`.

**CTR-2 does not require a production-like environment in every pull request.** A container started for the run, or a provider sandbox, is real in the sense the condition uses. Where no sandbox exists, the adapter is named in a decision record that gives the reason and is cited from the adapter with `ADR-N`, and a reviewer reads that record instead.

**A pure library has no adapter and owes no integration test.**

**CTR-1 has its script in `rules/contract-first.md` and no second detector.** CTR-2's script belongs to #332, and until it lands a reviewer reads it.
