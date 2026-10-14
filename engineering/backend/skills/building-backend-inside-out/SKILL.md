---
name: building-backend-inside-out
description: Use when a backend capability is being built or extended. Builds it inside-out as four stacked layers — domain, use cases, OLTP, API — with the behaviour scenario leading, the domain driven out red-first, each layer delegated to a specialist and looped through review before it opens, and the layers landing as a stack.
type: skill
clade: engineering
subclade: backend
references:
  - skills/driving-with-tdd/SKILL.md
  - skills/specifying-with-bdd/SKILL.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:skills/querying-the-code-graph/SKILL.md
  - ahrena-engineering-fundamentals:rules/aggregates.md
  - ahrena-engineering-fundamentals:rules/domain-model.md
  - ahrena-engineering-fundamentals:rules/contract-first.md
  - ahrena-contributing:skills/stacking-pull-requests/SKILL.md
---

# Building backend inside-out

A capability is built from the inside out, in four layers that nest: the domain holds the rules, the use cases drive the domain, the OLTP persists it, the API exposes it. The dependency runs one way — inward — so [`ahrena-engineering-fundamentals:rules/domain-model.md`](../../../fundamentals/rules/domain-model.md) holds the domain to importing no mechanism and [`ahrena-engineering-fundamentals:rules/aggregates.md`](../../../fundamentals/rules/aggregates.md) draws the boundary each root defends. Each layer is tested green before the one that depends on it is started, each is delegated to a specialist, and each lands as its own pull request in a stack.

## 1. Read the component map and conform to it

Before naming or creating anything, run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md). Take the project's words, its sanctioned folders, the backend component's stack, and its `testing` lanes.

The recurring failure is building in this clade's default vocabulary. The use case, the aggregate, the port and the repository are canonical terms; the project's glossary overrides them, and if the project calls a use case a `workflow`, that is the word and the folder. A directory the project has not sanctioned — a `use_cases/` you invented — is condition 3 of the ubiquitous-language rule failing. If you did not read the map, you have not earned the right to name a folder.

Beside the map, query the actual structure through [`ahrena-engineering-fundamentals:skills/querying-the-code-graph/SKILL.md`](../../../fundamentals/skills/querying-the-code-graph/SKILL.md): `locate` the paths this capability will touch to find which existing component owns them, and `deps` to read what they depend on and what depends on them, so the change is placed and scoped before a line is written. The map is the structure the project declares; the graph is the structure that is. Where the two disagree, surface the drift rather than resolving it here.

## 2. Lead with the behaviour scenario

Write the behaviour the capability must exhibit, in the project's scenario style, before any layer. The scenario is what the domain's first unit test is driven toward and what the API's acceptance scenarios will assert. A layer with no behaviour above it is a layer building toward a target nobody wrote down.

## 3. The loop every layer runs before it opens

Inside each of the four layers, the delegated specialist develops, the reviewer reviews the working diff, the specialist develops again — for at most three rounds — and then the layer opens as a pull request. Between rounds, the mechanically applicable findings are applied so the specialist's next round starts from them.

Three rounds is the cap, not the target. A layer that is clean in one round opens in one. A layer still failing review after three rounds is a layer whose model is wrong, which is a finding for the layer below it, not a fourth round here. The reviewer reviews again on the pull request itself, outside this loop; the in-loop rounds spend the cheap feedback before the expensive one, they do not replace it.

## 4. Layer one — the domain

Delegate the aggregates, value objects, domain services and events that model the business, driven out with [`skills/driving-with-tdd/SKILL.md`](../driving-with-tdd/SKILL.md): the unit test is written red against the aggregate before the aggregate exists. The domain imports no mechanism, per `ahrena-engineering-fundamentals:rules/domain-model.md`, and its boundaries are drawn by invariants, per `ahrena-engineering-fundamentals:rules/aggregates.md`. Run the loop in step 3; the tested domain is the first pull request in the stack.

## 5. Layer two — the use cases

Delegate the use cases that orchestrate the domain. Their test arc, per `skills/driving-with-tdd/SKILL.md`, is use-case tests that stand test doubles in for the ports the use case depends on, so the use case is exercised without a database or a network. Each use case loads, calls one aggregate and saves; behaviour whose terms name two roots is a domain service, not a use case. Run the loop, then stack this layer on the domain layer.

## 6. Layer three — the OLTP

Delegate the persistence: the repository implementations behind the ports, the schema and its migrations. Its test arc is integration tests against a real database with the migrations applied, which catch what a test double cannot — a constraint, a transaction boundary, a mapping that drifts from the aggregate. Run the loop, then stack this layer on the use-cases layer.

## 7. Layer four — the API

Delegate the API that exposes the use cases. Its test arc, per [`skills/specifying-with-bdd/SKILL.md`](../specifying-with-bdd/SKILL.md), is the story's acceptance criteria as Given/When/Then scenarios — each naming its criterion with `#<issue>/AC-n` — plus consumer-driven contract tests. The contract is authored, not generated, per [`ahrena-engineering-fundamentals:rules/contract-first.md`](../../../fundamentals/rules/contract-first.md). This is where the behaviour scenario from step 2 is finally satisfied end to end. Run the loop, then stack this layer on the OLTP layer.

## 8. Stack the layers

Open and land the four layers as a stack, through [`ahrena-contributing:skills/stacking-pull-requests/SKILL.md`](../../../../contributing/skills/stacking-pull-requests/SKILL.md): each layer based on the one below, each closing its own issue, landing in order from the domain up. A layer reviewed and landed apart is a layer that can be reasoned about apart.

## When this skill does not apply

**A change with no new behaviour.** A refactor that moves code without changing what the system does, a dependency bump, a config change the owner already signed off — none introduces a model, so none needs the four-layer build. Make the change against trunk and skip the stack.

**Frontend, cross-service or cross-concern work.** This procedure builds the backend layers. A change that reaches the frontend, another service or another clade is routed by Athena, not absorbed here. Build the backend layer and name the boundary.

**Deciding whether the capability should exist.** This builds the capability inside-out; whether it is wanted, and whether the model is right, are the owner's to settle. The procedure starts once the behaviour is agreed.

<!--
Directory layout:

skills/building-backend-inside-out/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
