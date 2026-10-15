---
name: testing-frontend
description: Use to know what tests each outside-in layer owes — the red end-to-end skeleton at the wireframe, stories with snapshot, visual-regression and accessibility checks at the components, interaction and unit tests at the state, and the end-to-end going green with a page-level accessibility check at the contract — in the tools the project's component map names.
type: skill
clade: engineering
subclade: frontend
references:
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:docs/component-map.md
---

# Testing frontend

Each outside-in layer owes a specific red-to-green test arc, and the arc completes across the four layers: the end-to-end test is written red at the wireframe and does not go green until the contract. The tools below are this clade's defaults; the project's component map overrides them, and reading it is step one.

## 1. Resolve the tools from the component map

Run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md) and read the frontend component's `testing` lanes: `e2e`, `workbench`, `visual`, `a11y` and `quality`. [`ahrena-engineering-fundamentals:docs/component-map.md`](../../../fundamentals/docs/component-map.md) defines each lane and states the precedence — a lane the project fills replaces this clade's default for that lane, and is not run beside it.

The defaults named in the steps below — Playwright, a component workbench such as Storybook with snapshots, a visual-regression service such as Chromatic, an accessibility checker such as axe — apply only where the project's lane is silent. The recurring failure is running the default tool when the project named another; a stated lane wins every time.

## 2. Wireframe layer — the red end-to-end skeleton

Write the end-to-end test against the approved wireframe, in the project's `e2e` tool, and confirm it fails. It asserts the finished behaviour in terms of the wireframe's screens and flow. It is red on purpose and stays red until step 5.

## 3. Components layer — stories, snapshot, visual regression and accessibility, per component

For each component that fills the wireframe, author a workbench story in the project's `workbench` tool, a snapshot of its rendered output, a visual-regression check in the project's `visual` tool against every state the wireframe drew, and an accessibility check in the project's `a11y` tool. The component is not done until every one of its wireframe states has a story and passes all four.

The failure here is covering only the populated state. The empty, loading and error states the wireframe fixed each need their own story and their own checks, because those are the states a snapshot and a visual diff most often catch regressions in.

## 4. State layer — interaction and unit tests

For the state that drives the components, write interaction tests that exercise the components through their real behaviour — a user filling a field, a control toggling, a flow advancing — and unit tests on the state logic itself. The end-to-end skeleton from step 2 moves closer to green here but does not yet pass, because the data feeding the state is not wired until the contract.

## 5. Contract layer — the end-to-end goes green, plus page-level accessibility

Wire the contract, and take the end-to-end test from step 2 to green: the behaviour scenario is now satisfied end to end. Add a page-level accessibility check over the fully assembled page, which catches the problems only composition reveals — focus order across components, landmark structure, contrast in real content — that a per-component check in step 3 cannot see.

## When this skill does not apply

**Choosing the tools.** This skill resolves the arc against the tools the project already named. Deciding what a project's testing lanes should be is a change to the project's component map, which its owner consents to, not something settled here.

**Backend or contract-provider tests.** The contract layer's end-to-end test exercises the frontend against the contract. The provider side of the contract — its own unit, integration and contract-verification tests — belongs to the backend clade, not here.

**A change with no new behaviour.** A refactor or a dependency bump that changes nothing a user experiences does not open a new test arc; it must keep the existing suite green, and that is all.

<!--
Directory layout:

skills/testing-frontend/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
