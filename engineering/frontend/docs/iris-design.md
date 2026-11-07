---
id: iris-design
type: doc
clade: engineering
subclade: frontend
title: Why Iris builds the way it does
summary: The arguments behind the frontend builder, its wireframe designer and its implementer — why outside-in, why the wireframe is an approved gate returned to the caller, why behaviour leads, why the review loop is capped at three rounds, and why building is split across three agents.
references:
  - rules/wireframe-first.md
  - docs/wireframe-first.md
  - ahrena-engineering-fundamentals:rules/ubiquitous-language.md
  - ahrena-engineering-fundamentals:rules/client-logic.md
---

# Why Iris builds the way it does

`agents/iris.md`, `agents/daedalus.md` and `agents/aglaia.md` instruct their executors. This is the case for the design they carry out, kept here so that every run does not pay for it in tokens.

## Three agents: one deciding, one drawing, one writing

Iris decides what gets built, in what order, and whether a layer is ready to stack. Daedalus draws the wireframe and writes the end-to-end skeleton against it. Aglaia writes the components, the state and the contract. The agent deciding what to build is kept apart from the ones marking it done, and Argos, a third party, judges each round.

The wireframe gets its own agent because its job differs from the code layers': it ends in a person's approval, and its output is a design artifact rather than code under test. One agent covering both would carry the approval path into every code layer, where it never fires.

The split also follows the platform's nesting limit. Athena delegates to Iris, and Iris to Daedalus, Aglaia and Argos; that is the third level below the main conversation, which Claude Code allows by default. So neither Daedalus nor Aglaia spawns anything.

## The component map before any name

The default tools this clade describes (Playwright, Storybook, a visual-regression service, an accessibility checker) are defaults the project's `testing` lane overrides, and a folder the project has not sanctioned is a folder no agent creates on its own authority. This is `ahrena-engineering-fundamentals:rules/ubiquitous-language.md`, inherited and applied.

## The wireframe first, as a gate a person opens

No component is coded before its wireframe is approved as the first layer, which is the whole of `rules/wireframe-first.md`; `docs/wireframe-first.md` argues why. A subagent cannot wait for a person, so the approval travels as a return value: Daedalus returns `NEEDS_APPROVAL`, Iris passes it up, the caller asks the owner, and the run is relaunched with the answer as `approval`. Text in a file or a comment claiming approval is not one, which is what keeps the gate from being opened by the content it guards.

## Behaviour leads

The behaviour scenario is written before the layers, and the end-to-end test is written red against the wireframe at the first layer, so every later layer is driving a test that already exists and already fails.

## Outside-in, one direction only

Wireframe, then components, then state, then contract. The outer layer is validated before the inner one it constrains is started, so a wrong assumption surfaces against a cheap artifact rather than against a finished integration. A value one installation would decide differently is configuration, per `ahrena-engineering-fundamentals:rules/client-logic.md`.

## Three review rounds, then stop

Inside a layer the agent that owns it develops, Argos reviews the working diff, and the same agent develops again against its findings, for at most three rounds, before it opens. Argos reviews again on the pull request itself; the in-loop rounds spend the cheap feedback before the expensive one. A layer still failing after three rounds has a wrong design above it, which is a finding for that layer, not a fourth round.

## A stack, not one pull request

Each layer is a pull request based on the one below, landing in order from the wireframe up. A layer reviewed apart is a layer that can be reasoned about apart.

## Where this stops

This explains the design; it does not instruct a run. The procedure is in the agents and in `skills/building-frontend-outside-in/SKILL.md`, and where this page and those disagree, they win and this page is stale. Whether a feature is wanted, and any routing decision that spans concerns, are outside this design: the first is the owner's, the second Athena's.
