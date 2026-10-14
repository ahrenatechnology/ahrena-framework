---
name: building-frontend-outside-in
description: Use when a user-facing feature is being built or extended. Builds it outside-in as four stacked layers — wireframe, components, state, contract — with the behaviour scenario leading, the wireframe approved first, each layer delegated to a specialist and looped through review before it opens, and the layers landing as a stack.
type: skill
clade: engineering
subclade: frontend
references:
  - rules/wireframe-first.md
  - skills/designing-wireframes/SKILL.md
  - skills/testing-frontend/SKILL.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:skills/querying-the-code-graph/SKILL.md
  - ahrena-contributing:skills/stacking-pull-requests/SKILL.md
---

# Building frontend outside-in

A feature is built from the outside in, in four layers that nest: the wireframe fixes what the user sees, the components fill it, the state drives them, the contract feeds the state. Each layer is validated before the one it constrains is started, each is delegated to a specialist, and each lands as its own pull request in a stack. [`rules/wireframe-first.md`](../../rules/wireframe-first.md) holds the first layer to being an approved gate.

## 1. Read the component map and conform to it

Before naming or creating anything, run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md). Take the project's words, its sanctioned folders, the frontend component's stack, and — this is the one this clade leans on hardest — its `testing` lane.

The recurring failure is building in this clade's default vocabulary. The tools named in `testing-frontend` are framework defaults the project's map overrides; a folder the project has not sanctioned is a folder you do not invent. If you did not read the map, you have not earned the right to name a folder.

Beside the map, query the actual structure through [`ahrena-engineering-fundamentals:skills/querying-the-code-graph/SKILL.md`](../../../fundamentals/skills/querying-the-code-graph/SKILL.md): `locate` the paths this feature will touch to find which existing component owns them, and `deps` to read what they depend on and what depends on them, so the change is placed and scoped before a line is written. The map is the structure the project declares; the graph is the structure that is. Where the two disagree, surface the drift rather than resolving it here.

## 2. Lead with the behaviour scenario

Write the behaviour the feature must exhibit, in the project's scenario style, before any layer. The scenario is what the wireframe is drawn to serve and what the end-to-end test is written against. A layer with no behaviour above it is a layer building toward a target nobody wrote down.

## 3. The loop every layer runs before it opens

Inside each of the four layers, the delegated specialist develops, Argos reviews the working diff, the specialist develops again — for at most three rounds — and then the layer opens as a pull request. Between rounds, Erodos applies the mechanically applicable findings so the specialist's next round starts from them.

Three rounds is the cap, not the target. A layer that is clean in one round opens in one. A layer still failing Argos after three rounds is a layer whose design is wrong, which is a finding for the layer above it, not a fourth round here. Argos reviews again on the pull request itself, outside this loop; the in-loop rounds spend the cheap feedback before the expensive one, they do not replace it.

## 4. Layer one — the wireframe

Delegate to the Designer, through [`skills/designing-wireframes/SKILL.md`](../designing-wireframes/SKILL.md). It produces the wireframe as an artifact, hands it back for the owner's approval, and writes the Playwright end-to-end skeleton red against it. No component is coded until that approval exists — this is the gate `rules/wireframe-first.md` names. The approved wireframe and the red skeleton are the first pull request in the stack.

## 5. Layer two — the components

Delegate the components that realise the approved wireframe. The per-layer test arc for this layer is in [`skills/testing-frontend/SKILL.md`](../testing-frontend/SKILL.md): a workbench story, a snapshot, a visual-regression check and an accessibility check per component, in the project's tools. Run the loop in step 3, then stack this layer on the wireframe layer.

## 6. Layer three — the state

Delegate the state that drives the components. Its test arc is the interaction tests and the unit tests on the state, per `skills/testing-frontend/SKILL.md`. The end-to-end skeleton from layer one is still red, and this layer moves it closer to green without yet completing it. Run the loop, then stack this layer on the components layer.

## 7. Layer four — the contract

Delegate the contract that feeds the state. Its test arc takes the end-to-end test green and adds the page-level accessibility check, per `skills/testing-frontend/SKILL.md`. This is where the behaviour scenario from step 2 is finally satisfied end to end. Run the loop, then stack this layer on the state layer.

## 8. Stack the layers

Open and land the four layers as a stack, through [`ahrena-contributing:skills/stacking-pull-requests/SKILL.md`](../../../../contributing/skills/stacking-pull-requests/SKILL.md): each layer based on the one below, each closing its own issue, landing in order from the wireframe up. A layer reviewed and landed apart is a layer that can be reasoned about apart.

## When this skill does not apply

**A change with no new behaviour.** A refactor that moves code without changing what the user sees, a dependency bump, a copy fix the owner already signed off — none opens a design question, so none needs the four-layer gate. Make the change against trunk and skip the stack.

**Backend, data or cross-concern work.** This procedure builds the frontend layers. A change that reaches the backend, the data layer or another clade is routed by Athena, not absorbed here. Build the frontend layer and name the boundary.

**Deciding whether the feature should exist.** This builds the feature outside-in; whether it is wanted, and whether the approach is right, are the owner's to settle. The procedure starts once the behaviour is agreed.

<!--
Directory layout:

skills/building-frontend-outside-in/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
