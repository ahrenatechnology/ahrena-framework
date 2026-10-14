---
name: routing-concern
description: Route a concern to the clade that owns it, deterministic-first. Use when a change, a layer or a finding has to be placed with the frontend, backend or data clade, or split across them. Applies a route table first, consults the Clef decision gate when the table is inconclusive, and escalates to a human when Clef is not confident — never guessing a routing it cannot decide.
type: skill
clade: engineering
subclade: delivery
references:
  - docs/clef-decision-gate.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:skills/querying-the-code-graph/SKILL.md
---

# Routing a concern

A concern is a piece of work that has to be placed with the clade that owns it before anyone builds it: the frontend, the backend, the data layer, or a split across them. Routing it wrong sends the work to a builder that cannot finish it and surfaces only after effort is spent, so the placement is decided deliberately and in a fixed order. The order is deterministic-first: a route table a person wrote, then the Clef gate, then a human. Each stage runs only when the one before it could not decide.

## 1. Read the concern in the project's own vocabulary

Before placing anything, run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md). Take the project's `components`, their `concern` values and their `paths`, so the concern is matched against the boundaries the project drew, not this clade's defaults. A concern described in the project's words, against the project's component paths, is one the route table can actually decide; a concern read in the framework's generic terms is one the table will mismatch.

## 2. Apply the deterministic route table first

Match the concern against the route table: its stated kind and the paths it touches, mapped to a clade by rules a person wrote. When a rule matches, the table decides, and you route there without consulting Clef. The table is where most concerns are placed, because a deterministic rule is reproducible and auditable in a way a probability is not.

```yaml
# concern signal        -> clade
paths: "web/**, ui/**"  -> frontend
paths: "api/**, src/**" -> backend
paths: "models/**, dbt/**, marts/**" -> data
kind: "screen | component | wireframe" -> frontend
kind: "schema | mart | pipeline"       -> data
```

Keep the table's own rules short and decidable. A longer worked table, with multi-signal rows and the cross-concern cases, is in [`references/route-table.example.yaml`](references/route-table.example.yaml); open it when a concern carries more than one signal or spans two components.

Ground the table's path rows in the actual structure, not a glob alone. Through [`ahrena-engineering-fundamentals:skills/querying-the-code-graph/SKILL.md`](../../../fundamentals/skills/querying-the-code-graph/SKILL.md), `locate` each path the concern changes to the component that owns it, and route to that component's concern. This strengthens the deterministic tier — not Clef — by mapping a path to a clade by what actually imports it. A path the graph places in one component and the table's globs place in another is drift to surface, not a tie to hand to Clef.

## 3. Consult the Clef gate when the table is inconclusive

When no table rule matches, or two match and disagree, the concern is inconclusive, and it goes to the Clef decision gate — not to a widened table rule. Clef is Cloudflare's probabilistic decision model, consulted as a gate; [`docs/clef-decision-gate.md`](../../docs/clef-decision-gate.md) says what it is, what it takes in and what it returns. Pass it the concern's description, the paths it touches and the clades the table left open. It returns a decision — the clade, or a cross-concern split — and a confidence.

## 4. Escalate to a human when Clef is not confident

Read Clef's confidence against the threshold. At or above it, route to the clade Clef returned. Below it, escalate to a human, who decides the routing, and that decision is final for the concern — do not re-run Clef for a number that clears the bar. A low-confidence routing is escalated, never guessed, because a concern placed on a near-guess is wrong work that looks assigned.

## 5. Hand back the placement and the stage that made it

Return the clade the concern was routed to and which stage decided it: the table rule that matched, Clef's decision and confidence, or the human the concern was escalated to. Recording the stage is what lets a later reviewer see that the cascade was followed in order and that nothing skipped the table or routed under the threshold.

## When this skill does not apply

**A concern already placed.** A layer already delegated to a build clade, or a finding whose owning clade the review already named, is routed; re-routing it is churn, not placement.

**Deciding whether the concern should exist.** This places a concern with its clade; whether the work is wanted, and whether its criteria are right, is gate 1's question, settled before routing. The cascade starts once the concern is agreed worth doing.

**Setting the route table's rules or Clef's threshold.** This skill applies the table and the threshold; authoring the table's rows and tuning the threshold are changes to the project its owner consents to, not something routing does as a side effect.

<!--
Directory layout:

skills/routing-concern/
├── SKILL.md
└── references/    the longer worked route table a step opens

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
