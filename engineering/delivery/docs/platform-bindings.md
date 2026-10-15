---
id: platform-bindings
type: doc
clade: engineering
subclade: delivery
title: Binding the agency to each platform
summary: The portable manager/worker spec and how each platform binds it — Claude Code as the Athena agent plus an optional Workflow, Codex as custom subagents with the AGENTS.md trigger and the max_depth cap, and LangGraph named as the out-of-scope runtime binding — plus the entry directive that makes the agency always used.
references:
  - docs/clef-decision-gate.md
---

# Binding the agency to each platform

The agency's orchestration is one shape, written once and bound many ways. This
doc states that shape, then says how each platform runs it and how a platform is
made to *always* run it. The orchestration artifacts themselves — the Athena
agent and the `orchestrating-delivery` and `routing-concern` skills — are the
portable spec; nothing here changes them. What changes per platform is the
binding: the mechanism that spawns the manager and its workers, and the one
directive that routes build work through them.

## The portable spec is manager/worker

The shape is a manager and its workers. The manager plans an issue into typed
layers, routes each concern to the clade that owns it, delegates each layer to
the build agent that can finish it, runs the develop→review loop at most three
rounds before each layer opens, stacks the layers, and escalates what the loop or
the cascade cannot settle. It never writes production code, passes a review
verdict, or applies a fix. In this framework the manager is Athena and the
workers are Iris, Apollo and Clio, with Argos reviewing and Erodos applying
findings in the loop.

That description names no runtime. It is true of a Claude Code agent, a Codex
subagent and a LangGraph supervisor alike, which is why the spec is portable and
the binding is thin. The routing step inside it consults the Clef decision gate
when its route table is inconclusive; [`docs/clef-decision-gate.md`](clef-decision-gate.md)
says what that gate is and why it is a gate and not a persona, and the binding
does not change it either.

## Claude Code: the agent, plus an optional Workflow

The default Claude Code binding is the Athena agent. She is discovered through the
plugin manifest like any agent, addressed as `athena`, and she delegates to the
build agents the same way a person would. This binding needs nothing beyond the
plugins being installed and the entry directive being present.

The optional binding is a **Workflow** script. Claude Code's Workflow tool runs a
deterministic JavaScript fan-out that spawns subagents, so Athena's loop — plan,
then build-and-review each layer, then stack — can be encoded as phases with
`agent()`, `pipeline()` and `parallel()` primitives. The Workflow is opt-in: it
is a reference a project adapts when it wants the loop run deterministically
rather than agent-driven, not a thing that fires on its own. The illustrative
script is the skill's `athena.workflow.js` reference.

## Codex: custom subagents, triggered from AGENTS.md

Codex binds the spec as custom subagents (GA around March 2026) in a manager/worker
arrangement: the manager plans and delegates and integrates and never writes code
— which is Athena — and the workers are the build agents it spawns.

**The TOML home.** A Codex custom agent is a TOML file, personal under
`~/.codex/agents/` or per-project under `.codex/agents/`. A markdown persona in
this framework maps onto one directly: the agent's `name` and `role` become the
agent's identity, the `description` becomes its selection text, and the body
becomes its system prompt. The portable persona is the source; the TOML is the
binding Codex reads.

**The AGENTS.md trigger.** A Codex subagent is either spawned explicitly or
triggered from `AGENTS.md` (or a skill). `AGENTS.md` is Codex's always-loaded
instruction file, so it is where the entry directive goes — the same role
`CLAUDE.md` plays for Claude Code.

**The caps, and the depth gotcha.** Codex bounds recursion and concurrency with
`agents.max_threads` (default 6) and `agents.max_depth` (default 1). The depth cap
is the one to design around. Athena spawning a build agent is already depth 1, so
a build agent that spawned its own stage subagent would be depth 2 and exceed the
default. The binding resolves this by **flattening**: Athena spawns the build
agents directly, and the build agents do their layer's work in their own thread
rather than sub-spawning. That runs inside `max_depth=1` on a stock install. A
project that wants build agents to fan out into their own stage subagents raises
`agents.max_depth` to 2 — one named setting, opted into, rather than a default the
binding silently depends on.

## LangGraph: the out-of-scope runtime binding

LangGraph (LangChain) is the third binding and it is deliberately out of scope
here. The manager/worker shape maps cleanly onto a LangGraph supervisor with
cycles for the review loop and a human-in-the-loop node for escalation, which is
why it is worth naming. But LangGraph is the runtime — it lives in `ahrena-agents`,
not in these framework artifacts — so this doc records the mapping and ships no
LangGraph code. The spec is what is portable; the LangGraph graph that executes it
is a runtime concern the agents repository owns.

## The directive is what makes it always used

A bound agent is available, not used. The lever that makes build work *enter*
through the agency is one entry directive written into the platform's always-loaded
instruction file — `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex. It states,
in one line plus the route, that build work enters through the `athena` agent, who
plans the issue, routes the concern, and delegates each layer to iris, apollo or
clio while running the develop→Argos loop before each stacked pull request, and
that build work is not implemented directly. Being always-loaded is the point: it
is the one place that reaches every request before an agent is chosen. The
`installing-the-agency` skill writes it, between markers, idempotently.

The default binding is the local harness with API inference. A local-model path —
Ollama or vLLM behind the same harness — is a one-line documented extension point,
not implemented here.

## Where this stops

**It does not change the spec.** Athena and her two skills are the portable
orchestration, authored once. This doc binds them to platforms; it does not
re-specify the plan→route→delegate→loop→stack procedure, which is
`skills/orchestrating-delivery/SKILL.md`'s.

**It does not implement a runtime.** The LangGraph mapping is recorded, not built,
and the local-model path is named, not wired. Both are runtime concerns the
`ahrena-agents` repository owns, kept out of these framework artifacts on purpose.

**It does not write the install.** How the directive is ensured, checked and kept
from clobbering surrounding content is the `installing-the-agency` skill and its
`install.py` script. This doc says what the bindings are; the skill is the
procedure that applies them.

**It does not set Codex's config.** The `max_threads` and `max_depth` values are
the project owner's to set in Codex's own configuration. This doc names the depth
gotcha and the one value to change for a deeper tree; changing it is the owner's
act, not a side effect of binding.
