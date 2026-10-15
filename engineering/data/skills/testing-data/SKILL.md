---
name: testing-data
description: Use to know what tests each source→product layer owes — the data-contract test written red at the schema, unit tests on each transform at the medallion, data-quality expectations for freshness, uniqueness and nullability at the expectations layer, and the mart's contract test plus a reconciliation to the pinned source going green at the marts — in the tools the project's component map names.
type: skill
clade: engineering
subclade: data
references:
  - rules/reconciliation.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:docs/component-map.md
---

# Testing data

Each source→product layer owes a specific red-to-green test arc, and the arc completes across the four layers: the data-contract test is written red at the schema and the capability is not green until the mart's contract test and reconciliation pass. The tools below are this clade's defaults; the project's component map overrides them, and reading it is step one.

## 1. Resolve the tools from the component map

Run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md) and read the data component's `testing` lanes — the contract, transform-unit and quality lanes — and its `delivery` surface. [`ahrena-engineering-fundamentals:docs/component-map.md`](../../../fundamentals/docs/component-map.md) defines each lane and states the precedence: a lane the project fills replaces this clade's default for that lane, and is not run beside it.

The defaults named in the steps below — dbt tests and a warehouse unit-test harness for the transforms, Great Expectations for the quality lane, a hand-written SQL assertion for reconciliation — apply only where the project's lane is silent. The recurring failure is running the default tool when the project named another; a stated lane wins every time.

## 2. Schema layer — the data-contract test, red first

Write the data-contract test against the authored contract, in the project's contract tool, and confirm it fails. It asserts that a dataset conforming to the contract has exactly the contract's columns, types and keys, and it is red because the dataset does not exist yet. Confirm it fails for that reason — the dataset is absent — rather than a typo in the test. A contract test that passes the moment it is written tested nothing.

## 3. Medallion layer — unit tests on each transform

For each transform that carries data from bronze through silver to gold, write a unit test against a small fixture that exercises the defect that transform owns: a join that must not fan out, a filter that must not drop a segment, a dedup that must collapse exactly the duplicates, a cast that must not silently null. The transform is driven red-first against the fixture, then made to pass. These catch at a small, legible scale the content errors that are invisible once the data is at full volume.

## 4. Expectations layer — data-quality checks

Author the data-quality expectations in the project's quality tool: freshness against the contract's SLA, uniqueness of the declared key, nullability of each column the contract marks required, and accepted ranges where the contract states them. Each expectation is a statement about one dataset against its own declared invariants, and the layer is a gate — red expectations stop the data flowing on, they are not a dashboard read afterward.

The failure here is checking only the columns that are easy. The freshness window and the key's uniqueness are the expectations a stale partition or a fan-out join breaks first, and a layer that asserts nullability but not freshness has gated the tidy failure and missed the common one.

## 5. Marts layer — the contract test and reconciliation go green

Take the mart's contract test to green — every operation the contract declares exercised by at least one test — and add the reconciliation that ties the mart's figures back to the source the contract pinned, per [`rules/reconciliation.md`](../../rules/reconciliation.md). The reconciliation recomputes the mart's key measures from the pinned source, not from a derived layer, and asserts agreement within the stated tolerance. This is the point the capability is proven both well-shaped and faithful: a mart whose contract test is green and whose reconciliation is red is defective, not done.

## When this skill does not apply

**Choosing the tools.** This skill resolves the arc against the tools the project already named. Deciding what a project's testing lanes should be is a change to its component map, which its owner consents to, not something settled here.

**Authoring the contract.** This skill tests against the contract; writing the contract — its schema, keys, freshness and pinned source — is `modeling-data-contracts`' subject, and the data-contract test in step 2 is written against the contract that skill produced.

**A change with no new data product.** A refactor or a dependency bump that changes nothing a consumer reads opens no new test; it must keep the existing suite, expectations and reconciliation green, and that is all.

<!--
Directory layout:

skills/testing-data/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
