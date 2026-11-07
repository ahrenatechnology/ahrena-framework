---
id: apollo-design
type: doc
clade: engineering
subclade: backend
title: Why Apollo builds the way it does
summary: The arguments behind the backend builder and its implementer — why inside-out, why the domain is driven red-first, why acceptance closes at the API, why the review loop is capped at three rounds, why the builder and the implementer are two agents, and why the clade ships no rule of its own.
references:
  - ahrena-engineering-fundamentals:rules/domain-model.md
  - ahrena-engineering-fundamentals:rules/aggregates.md
  - ahrena-engineering-fundamentals:rules/domain-services.md
  - ahrena-engineering-fundamentals:rules/contract-first.md
  - ahrena-engineering-fundamentals:rules/solid.md
  - ahrena-engineering-fundamentals:rules/clean-code.md
  - ahrena-engineering-fundamentals:rules/ubiquitous-language.md
---

# Why Apollo builds the way it does

`agents/apollo.md` and `agents/hephaestus.md` instruct their executors. This is the case for the design they carry out, kept here so that every run does not pay for it in tokens.

## Two agents, one deciding and one writing

Apollo decides what gets built, in what order, and whether a layer is ready to stack. Hephaestus writes one layer. The split keeps the agent deciding what to build apart from the one marking it done, and Argos, a third party, judges each round. A builder that approved its own layer would spend the one thing a second party is for.

The split also follows the platform's nesting limit. Athena delegates to Apollo, and Apollo to Hephaestus and Argos; that is the third level below the main conversation, which Claude Code allows by default. So Hephaestus spawns nothing.

## The component map before any name

The concepts this clade leans on (the aggregate, the use case, the port, the repository) are canonical terms the project's glossary overrides. If the project calls a use case a `workflow`, the build produces a `workflow`. A folder the project has not sanctioned is a folder neither agent creates on its own authority; it becomes a question for the owner. This is `ahrena-engineering-fundamentals:rules/ubiquitous-language.md`, inherited and applied.

## Inside-out, one direction only

Domain, then use cases, then OLTP, then API. The dependency runs inward: the domain depends on nothing outward and the adapters depend inward, which is `ahrena-engineering-fundamentals:rules/domain-model.md`. The inner layer is tested green before the outer one that depends on it is started, so a wrong model surfaces against a cheap unit test rather than against a finished endpoint.

## Behaviour first, the domain red-first

The behaviour scenario is written before the layers. At the domain the unit test is written red against the aggregate before the aggregate exists, so every later layer is driving tests that already exist and already fail. Each layer owns its arc: unit TDD at the domain, use-case tests with test doubles for the ports, integration tests against a real database and its migrations at the OLTP, BDD acceptance at the API.

## Acceptance closes at the API

The outermost layer takes the story's acceptance criteria as Given/When/Then scenarios, each naming its criterion with a token such as `#412/AC-1`, so the behaviour is green and traceable to the requirement it satisfies. That token is the framework's traceability convention, enforced by `ahrena-contributing:rules/traceability.md`.

## Three review rounds, then stop

Inside a layer the implementer develops, Argos reviews the working diff, and the implementer develops again against its findings, for at most three rounds, before the layer opens. Argos reviews again on the pull request itself; the in-loop rounds spend the cheap feedback before the expensive one, they do not replace it. A layer still failing after three rounds is a layer whose model is wrong, which is a finding for the layer below it, not a fourth round.

## A stack, not one pull request

Each layer is a pull request based on the one below, landing in order from the domain up. A layer reviewed apart is a layer that can be reasoned about apart.

## No rule of its own

The clade declares no rule, and that is a decision. Its strongest guardrail, the domain depending on nothing outward, already lives in `ahrena-engineering-fundamentals:rules/domain-model.md`, and duplicating it would put one constraint in two places that drift. The layers apply `ahrena-engineering-fundamentals:rules/aggregates.md` and `ahrena-engineering-fundamentals:rules/domain-services.md` to the domain, `ahrena-engineering-fundamentals:rules/contract-first.md` to the API's authored contract, `ahrena-engineering-fundamentals:rules/solid.md` and `ahrena-engineering-fundamentals:rules/clean-code.md` to the code at every layer, and the ubiquitous-language rule to every name.

## Where this stops

This explains the design; it does not instruct a run. The procedure is in the agents and in `skills/building-backend-inside-out/SKILL.md`, and where this page and those disagree, they win and this page is stale. Whether a capability is wanted, and any routing decision that spans concerns, are outside this design: the first is the owner's, the second Athena's.
