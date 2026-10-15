---
name: building-data-contract-first
description: Use when a data capability is being built or extended. Builds it source→product as four stacked layers — schema, medallion, expectations, marts — with the data contract authored first and the later layers evolving from it, the contract test driven red at the schema, each layer delegated to a specialist and looped through review before it opens, and the layers landing as a stack reconciled to its source.
type: skill
clade: engineering
subclade: data
references:
  - skills/modeling-data-contracts/SKILL.md
  - skills/testing-data/SKILL.md
  - rules/reconciliation.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:rules/contract-first.md
  - ahrena-contributing:skills/stacking-pull-requests/SKILL.md
---

# Building data contract-first

A capability is built from source to product, in four layers that stack: the schema pins the data contract, the medallion transforms carry the data from bronze through silver to gold, the expectations gate its quality, the marts serve it. The contract is authored first and the later layers evolve from it, so [`ahrena-engineering-fundamentals:rules/contract-first.md`](../../../fundamentals/rules/contract-first.md) governs the whole build: a contract that can disagree with the pipeline is the only one that catches the change that breaks a consumer. Each layer is tested green before the one that depends on it is started, each is delegated to a specialist, and each lands as its own pull request in a stack.

## 1. Read the component map and conform to it

Before naming or creating anything, run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md). Take the project's words, its sanctioned folders, the data component's stack, its `testing` lanes and its `delivery` surface.

The recurring failure is building in this clade's default vocabulary. The bronze, silver and gold layers, the data contract, the mart and the expectation are canonical terms; the project's glossary overrides them, and if the project calls a mart a `view` or gold a `serving` layer, that is the word and the folder. A directory the project has not sanctioned — a `marts/` you invented — is condition 3 of the ubiquitous-language rule failing. If you did not read the map, you have not earned the right to name a folder.

## 2. Lead with the data contract

Author the data contract the capability must satisfy before any transform, through [`skills/modeling-data-contracts/SKILL.md`](../modeling-data-contracts/SKILL.md): the schema, the types, the keys, the freshness and the source it pins. The contract is what the schema layer's data-contract test is driven toward and what the mart will finally satisfy. A layer with no contract above it is a layer transforming toward a shape nobody wrote down.

## 3. The loop every layer runs before it opens

Inside each of the four layers, the delegated specialist develops, the reviewer reviews the working diff, the specialist develops again — for at most three rounds — and then the layer opens as a pull request. Between rounds, the mechanically applicable findings are applied so the specialist's next round starts from them.

Three rounds is the cap, not the target. A layer that is clean in one round opens in one. A layer still failing review after three rounds is a layer whose model is wrong, which is a finding for the layer below it, not a fourth round here. The reviewer reviews again on the pull request itself, outside this loop; the in-loop rounds spend the cheap feedback before the expensive one, they do not replace it.

## 4. Layer one — the schema

Delegate the data contract and the schema that realises it, with the data-contract test written red against the contract before the schema exists, per [`skills/testing-data/SKILL.md`](../testing-data/SKILL.md). The contract is authored, not generated, per `ahrena-engineering-fundamentals:rules/contract-first.md`, and it pins the source every later layer resolves against. Run the loop in step 3; the pinned contract is the first pull request in the stack.

## 5. Layer two — the medallion

Delegate the transforms that carry the data from bronze landing through silver cleansing to gold aggregation. Their test arc, per `skills/testing-data/SKILL.md`, is unit tests on each transform — a join that must not fan out, a filter that must not drop a segment, a dedup that must collapse exactly the duplicates — so a transform defect surfaces against a small fixture rather than against a finished mart. Run the loop, then stack this layer on the schema layer.

## 6. Layer three — the expectations

Delegate the data-quality expectations that gate the layers: freshness, uniqueness, nullability and accepted ranges, in the project's quality tool. These are a gate, not a report — a layer whose expectations are red does not hand data to the layer above it. Each expectation states an invariant of a single dataset against itself; the cross-dataset content check is the next layer's reconciliation. Run the loop, then stack this layer on the medallion layer.

## 7. Layer four — the marts

Delegate the marts that serve the product. Its test arc is the mart's contract test — every operation the contract declares exercised, per `ahrena-engineering-fundamentals:rules/contract-first.md` — plus the reconciliation that ties the mart's figures back to the pinned source, per [`rules/reconciliation.md`](../../rules/reconciliation.md). This is where the contract from step 2 is finally satisfied and the data is proven faithful, not just well-shaped: a mart that passes its schema contract and fails to reconcile is defective. Run the loop, then stack this layer on the expectations layer.

## 8. Stack the layers

Open and land the four layers as a stack, through [`ahrena-contributing:skills/stacking-pull-requests/SKILL.md`](../../../../contributing/skills/stacking-pull-requests/SKILL.md): each layer based on the one below, each closing its own issue, landing in order from the schema up. A layer reviewed and landed apart is a layer that can be reasoned about apart.

## When this skill does not apply

**A change with no new data product.** A refactor that moves a model without changing what it produces, a dependency bump, a config change the owner already signed off — none introduces a contract or a figure, so none needs the four-layer build. Make the change against trunk and skip the stack.

**Backend, frontend, cross-service or cross-concern work.** This procedure builds the data layers. A change that reaches the backend, the frontend, another service or another clade is routed by Athena, not absorbed here. Build the data layer and name the boundary.

**Deciding whether the data product should exist.** This builds the capability source→product; whether it is wanted, and whether the contract models the right grain, are the owner's to settle. The procedure starts once the data product is agreed.

<!--
Directory layout:

skills/building-data-contract-first/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
