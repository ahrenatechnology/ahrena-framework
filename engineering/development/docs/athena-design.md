---
id: athena-design
type: doc
clade: engineering
subclade: development
title: How Athena decides
summary: The arguments behind the tech-lead's procedure - why it reads the component map first, opens the issue before the plan, routes deterministic-first, treats an unreachable Clef as not confident, runs a bounded loop inside each layer, delegates rather than builds, keeps nesting at three levels, and returns to a person instead of waiting for one.
references:
  - docs/clef-decision-gate.md
  - docs/platform-bindings.md
---

# How Athena decides

`agents/athena.md` is a system prompt: it tells the executor what to do and leaves out why. This is the why. Read it when the procedure looks wrong, before changing it.

## The component map comes before the plan

A plan typed against the project's components, and a concern routed by the project's paths, keep the orchestration inside the boundaries the project drew. Routing a concern in the framework's generic terms is routing it to the wrong builder in the project's own layout.

## The issue comes before the plan

The branch, the stack and every pull request carry the issue's number, so there is nothing to name the work by until the issue exists. A small issue that is one pull request stays one; the plan is for a change that genuinely splits, and a plan manufactured for a one-layer issue is ceremony.

## Deterministic-first routing, and a Clef that cannot be reached

A deterministic rule is reproducible and auditable, a probability is neither, so the route table runs first and the Clef gate only where a fixed rule cannot decide. [`clef-decision-gate.md`](clef-decision-gate.md) says what the gate is. This framework ships no client for it: no tool, endpoint or command reaches Clef. An agent told to "consult Clef" with nothing to call would invent a result, which is the low-confidence routing that looks settled. So an inconclusive route is treated as one Clef is not confident on, and goes to the person with the candidate clades and a recommendation. The description keeps the three-stage cascade because that is the design; the body says what the executor can actually do today.

## The plan is approved before anything is created

The planning skill confirms the whole decomposition before creating a unit, because a plan confirmed one unit at a time drifts. A subagent cannot ask and wait, so the confirmation is a `NEEDS_APPROVAL` return and a relaunch that resumes at the creation step. Folding the undecided routes into the same question costs the person one decision instead of two.

## The loop is bounded, and inside the layer

The build agent develops, Argos reviews the working diff, the build agent develops again, for at most three rounds before the layer opens. The in-loop rounds spend the cheap feedback before the expensive pull-request review. A layer still failing after three rounds has a wrong plan or a wrong route, which is a person's decision, not a fourth round.

Erodos applies fixes to a pull request under a published review. Between in-loop rounds there is no pull request yet, only a working diff, so the build agent applies the fixes itself.

## Nesting stops at three levels

Claude Code bounds how deep subagents may spawn subagents with the environment variable `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, whose default is 3 levels below the main conversation ([sub-agents](https://code.claude.com/docs/en/sub-agents), [environment variables](https://code.claude.com/docs/en/env-vars)). That figure was read from those pages, not measured in a run; a project that changes the variable changes the bound this section relies on. Athena is one, a build agent or Argos two, an implementer or the in-loop Argos three, and the third level spawns nothing. That is why the build agents run their Argos at `autofix: off`: an Argos at the third level that spawned Erodos would be a fourth. Erodos runs only under the Argos Athena calls on a pull request, at the third level. Codex's default `max_depth` is lower still; [`platform-bindings.md`](platform-bindings.md) records how that binding flattens.

## It delegates the build

Each routed layer goes to the build agent that owns it, and that agent owns the order of its own layers and their discipline. The agent deciding what to build is kept apart from the one writing it, so a reviewer of the plan is not also defending the code.

## It returns rather than waits

An exhausted loop and an undecided route end at a person, and the person's decision is final. A pending check is a return state, because a subagent that polls CI spends its context waiting on something it cannot speed up. Landing a stack is a person's call or, in a round, the Tech Lead's under `round-roles.md` of `ahrena-engineering-delivery` condition 3, so Athena lands only with `land` on and the person's approval of each merge.

## Where this stops

**It does not change the procedure.** The steps are `agents/athena.md` and the skills it loads. This doc argues them; editing it changes nothing an executor does.

**It does not specify Clef.** What the gate is, takes and returns is `clef-decision-gate.md`. A future client for it would change step 4 of the agent, and this doc's section on it.
