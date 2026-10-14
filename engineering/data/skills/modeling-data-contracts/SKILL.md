---
name: modeling-data-contracts
description: Use at the first layer of a source→product build, to author the data contract the later layers evolve from. Fixes the schema, the types, the keys, the freshness and SLAs, and the source the contract pins — as an authored artifact reviewed before any transform exists, against which the data-contract test is written red.
type: skill
clade: engineering
subclade: data
references:
  - rules/reconciliation.md
  - ahrena-engineering-fundamentals:rules/contract-first.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
---

# Modeling data contracts

The data contract is the first artifact of a source→product build, and the one every later layer evolves from. It is authored before any transform — a decision that can be reviewed, disagreed with, and held stable while the pipeline behind it changes — not generated from whatever a query currently returns. This skill is how that contract is written.

## 1. Read the component map and resolve the vocabulary

Run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md) and take the data component's glossary, sanctioned folders, stack and `delivery` surface. The contract is written in the project's words: a dataset, a column, a key and a mart are named as the project names them, not as this clade's defaults do. A term absent from the glossary resolves to its canonical name, and nothing is coined that the project has not sanctioned.

## 2. Author the schema, types and keys

Fix the dataset's shape: its columns, each column's type, the primary key that identifies a row, and the foreign keys that tie it to other datasets. Write it as an artifact a reviewer reads and approves before a transform exists, because a contract that is authored first is a contract that can disagree with the pipeline later — which is the whole of [`ahrena-engineering-fundamentals:rules/contract-first.md`](../../../fundamentals/rules/contract-first.md). A schema reverse-engineered from a sample is a report of what the data happens to be, not a promise of what it will stay.

## 3. Pin the source the contract derives from

State, in the contract, the source every downstream layer resolves against: the bronze landing or the external system of record the dataset derives from. This is the independent truth the mart's reconciliation will tie back to, per [`rules/reconciliation.md`](../../rules/reconciliation.md), so pinning it here — at the first layer — is what fixes the reconciliation's target before the transforms that could bias it are written. A contract that names no source leaves the last layer nothing independent to check against.

## 4. Declare the freshness and the SLAs

State how current the data must be and how often it is produced: the freshness window a consumer may rely on, the schedule the dataset is refreshed on, and the completeness it guarantees for a period. These are part of the promise, not an operational detail — a consumer reading a mart depends on its data being as recent as the contract says, and a freshness SLA with no stated figure is a promise that cannot be broken loudly.

## 5. Declare the breaking-change policy

State what counts as a breaking change to this contract — a column removed, a type narrowed, a key changed, an enum value dropped — and that such a change ships under a new version rather than silently, per `ahrena-engineering-fundamentals:rules/contract-first.md`. A consumer built against the contract needs the change that would break them to be an announced version event, not a quiet edit discovered in production.

## 6. Hand the contract to the test and the later layers

Hand the authored contract to the schema layer's data-contract test, which is written red against it, and to the layers above, which evolve from it: the transforms carry data toward the shape it pins, the expectations gate against its invariants, and the mart satisfies it and reconciles to the source it named. The contract is the single source the rest of the build reads; recording it is what lets a reviewer check every later layer against the promise rather than against the code.

## When this skill does not apply

**Writing the transforms.** This skill authors the contract the transforms must satisfy. How bronze becomes silver becomes gold is the medallion layer's subject, driven by its own tests, not settled here.

**Choosing the contract language or tooling.** Which schema format, which registry, which contract-test tool a project uses is stated in its component map and resolved by reading it. This skill fixes what the contract must declare, not the mechanism that carries it.

**Generating a contract where the stack offers no other route.** A source that can only describe itself by introspection falls under the contract-first rule's fallback: generate, then diff against a reviewed document a person edits. The authored direction is preferred; where it is impossible, the review event is what must survive.

<!--
Directory layout:

skills/modeling-data-contracts/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
