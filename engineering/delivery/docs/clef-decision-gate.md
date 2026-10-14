---
id: clef-decision-gate
type: doc
clade: engineering
subclade: delivery
title: The Clef decision gate
summary: What Clef is and is not, where it sits in the routing cascade — after the deterministic route table, before human escalation — what it takes in and returns, and the confidence threshold below which a concern is escalated to a human rather than guessed.
---

# The Clef decision gate

Athena routes every concern it receives to the clade that owns it, and that routing is a cascade with three stages: a deterministic route table first, the Clef gate when the table is inconclusive, and a human when Clef is not confident. This doc is about the middle stage. `skills/routing-concern/SKILL.md` is the procedure that consults it; this explains what the stage is, why it is a gate and not a persona, and what its output means.

## Clef is a gate, not an agent

Clef is Cloudflare's probabilistic decision model, reached as a service. It is not a persona in this framework, it has no agent file, and it is never addressed, delegated to, or asked to orchestrate anything. It is a function Athena calls: a concern goes in, a decision and a confidence come back. The predecessor's "Decidor" was imagined as a persona that deliberated; this framework replaces that with a gate, because a routing decision does not need a character, it needs a classifier and a threshold.

The distinction matters for the artifact model. An agent is addressed and carries authority over a subject; a gate is a checkpoint a procedure passes a value through. Clef is the second. That is why it lives here as a doc and is realized in the `routing-concern` skill, and why there is no `agents/clef.md`. Making it an agent would invite callers to route *to* it, when its only job is to be consulted *by* Athena's routing step and return a value Athena then acts on.

## Where it sits in the cascade

The cascade is deterministic-first, and the order is not arbitrary.

**The route table runs first.** A route table maps concrete, decidable signals — the concern's stated kind, the paths it touches — to a clade, by rules a person wrote and can read. When a signal matches a rule, the table decides, and Clef is never consulted. A deterministic rule is cheaper, reproducible across two identical runs, and auditable after the fact, so it is the stage that should decide most concerns.

**Clef runs only when the table is inconclusive.** Some concerns carry no signal the table has a rule for: a vaguely worded request, a change that plausibly belongs to two clades, a concern whose paths span boundaries. Rather than widen the table with a weaker and weaker rule until it matches everything — the same failure as a reconciliation tolerance quietly turned up until it cannot fail — the cascade hands the undecided concern to Clef, whose probabilistic judgment is built for exactly the inputs a fixed rule cannot cover.

**A human runs when Clef is not confident.** Clef returns a confidence with its decision. Below the threshold, the concern is escalated to a human rather than routed on Clef's guess. This is the stage that keeps a low-confidence probability from being laundered into a decision that looks settled.

## What it takes in and returns

Clef takes the concern Athena could not place deterministically: its description, the paths it touches, and the candidate clades the table left open. It returns two things.

- **A decision** — the clade the concern is routed to: frontend, backend, data, or a cross-concern split Athena then plans.
- **A confidence** — a probability the decision is right, which is what the threshold is applied to.

The decision alone is never enough, because a probabilistic model returns a decision even when it is nearly guessing. The confidence is what lets the cascade tell a decision Clef is sure of from one it is not, and route the first and escalate the second.

## The confidence threshold

The cascade carries a threshold, and Clef's confidence is read against it. At or above it, Athena routes to the decision Clef returned. Below it, Athena escalates to a human, who decides the routing, and that human decision is final for that concern — Athena does not re-run Clef to try for a number that clears the bar.

The threshold is a project setting, named in the component map where the project states one and defaulting otherwise, not a constant this doc fixes. What this doc fixes is the shape of the rule: there is a threshold, it is applied to Clef's returned confidence, and a concern under it is escalated and never guessed. A cascade that routed on Clef's decision without reading its confidence would have no stage that catches the low-confidence case, which is the one most likely to be routed wrong while looking routed.

## Where this stops

**It does not set the route table's rules.** Which paths and concern kinds map to which clade is the route table's content, stated in `skills/routing-concern/SKILL.md` and its reference, and it is a per-project fact. This doc says the table runs first and Clef runs when it is inconclusive; it does not enumerate the table's rows.

**It does not fix the threshold's number.** A project tunes how readily it escalates, and where it says nothing the default applies. The rule is that the threshold exists and is applied; the value is the owner's, made once and visible.

**It does not implement Clef.** Clef is a Cloudflare service, and calling it — the endpoint, the credentials, the request shape — is an integration detail the project supplies. This doc argues what the gate is for in the cascade; it is not the client.

**It does not decide the concern's merit.** Routing places a concern with the clade that owns it; whether the concern is worth building, and whether its criteria are right, is gate 1's question, answered before Athena routes. Clef routes a concern that was already judged worth doing.

**It is one stage, not the whole of routing.** The deterministic table decides most concerns, the human decides the ones Clef is unsure of, and Clef decides only the inconclusive-but-confident middle. Clef's value is that middle band; it is not a replacement for the rules above it or the person below it.
