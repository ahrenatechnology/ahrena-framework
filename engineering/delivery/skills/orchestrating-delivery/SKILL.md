---
name: orchestrating-delivery
description: Take an issue from plan to a landed stack of pull requests. Use when a tech-lead must turn a received issue into reviewed, tested, merged work — planning it into typed layers, routing each to the build clade that owns it, running the develop→review loop before each layer opens, stacking the layers, and escalating when the loop is exhausted. It orchestrates; it does not implement, review or fix.
type: skill
clade: engineering
subclade: delivery
references:
  - skills/routing-concern/SKILL.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-contributing:skills/planning-changes/SKILL.md
  - ahrena-contributing:skills/stacking-pull-requests/SKILL.md
---

# Orchestrating delivery

An issue arrives and has to become merged work. This is the procedure a tech-lead runs to get it there: plan the issue into typed layers, route each layer to the build clade that owns it, run a develop→review loop on each layer before it opens, and stack the layers so they land in order. The procedure orchestrates specialists and gates; it writes no production code, passes no review verdict, and applies no fix. Each of those belongs to an agent this procedure delegates to and names in prose, never to the orchestrator.

## 1. Read the component map before planning or routing

Before splitting or placing anything, run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md). The project's `components`, their `concern` values and `paths`, and its vocabulary are what the plan is typed against and what each layer is routed by. Planning and routing in the project's own words is what makes the layers match the boundaries the project drew, not the framework's defaults.

## 2. Plan the issue into typed, ordered layers

Turn the issue into a plan through [`ahrena-contributing:skills/planning-changes/SKILL.md`](../../../../contributing/skills/planning-changes/SKILL.md): decide whether it needs a plan at all, split it into typed units, order them by what each waits on, and confirm the whole decomposition with the person before creating anything. A small issue that is one pull request needs no plan, and the planning skill says so; do not manufacture layers an issue does not have.

## 3. Route each layer to the clade that owns it

For each layer, place it with its build clade through [`skills/routing-concern/SKILL.md`](../routing-concern/SKILL.md): the deterministic route table first, the Clef gate when the table is inconclusive, a human when Clef is not confident. A layer that spans clades is not forced onto one builder; it is split into further layers, each routed in turn. Routing is where a layer is matched to the specialist that can finish it, so a misroute here wastes the whole layer below.

## 4. Delegate each layer to its build agent

Hand each routed layer to the build clade's agent — the frontend builder, the backend builder or the data builder — which owns the order its own layers are built in and the per-language discipline they follow. The orchestrator decides which agent gets the layer and in what order the layers go; it does not reach into a layer and write its code. The agent deciding what to build is kept separate from the one writing it.

## 5. Run the develop→review loop before each layer opens

Inside each layer, the build agent develops, the reviewer reviews the working diff, the build agent develops again — for at most three rounds — and then the layer opens as a pull request. Between rounds, the reviewer's mechanically applicable findings are applied by the fixer so the next round starts from them.

Three rounds is the cap, not the target. A layer clean in one round opens in one. A layer still failing review after three rounds is a layer whose plan or routing is wrong, and that is an escalation — step 7 — not a fourth round. The reviewer reviews again on the pull request itself, outside this loop; the in-loop rounds spend the cheap feedback before the expensive one, they do not replace it.

## 6. Stack the layers and land them in order

Open and land the layers as a stack through [`ahrena-contributing:skills/stacking-pull-requests/SKILL.md`](../../../../contributing/skills/stacking-pull-requests/SKILL.md): each layer based on the one below, each closing its own issue, landing from the lowest up. A layer reviewed and landed apart is a layer that can be reasoned about apart, and the stack is what keeps the order the plan recorded.

## 7. Escalate when the loop is exhausted or the routing is not confident

Escalate to a human, rather than pressing on, in two cases: a layer still failing review after its three rounds, and a concern the routing cascade could not place with confidence. Escalation is the honest end of an exhausted loop or an unplaceable concern, and a human's escalation decision is final — do not re-open the loop or re-run the routing to get past it.

## When this skill does not apply

**A change that is one pull request.** An issue small enough for a single pull request against trunk has no layers to plan, route or stack. The build agent for its clade takes it directly; this procedure is for a change that splits.

**Building a layer's code.** This procedure places and sequences layers; how a layer is built — its own internal order, its tests, its language discipline — is the build clade's skill, invoked by the agent this procedure delegates to.

**Reviewing, fixing or merging a layer.** The review verdict, the applied fix and the landing are the reviewer's, the fixer's and the gate's. This procedure runs the loop and reads its outcome; it does not pass the verdict, write the fix or approve the merge.

<!--
Directory layout:

skills/orchestrating-delivery/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
