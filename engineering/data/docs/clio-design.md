---
id: clio-design
type: doc
clade: engineering
subclade: data
title: Why Clio builds the way it does
summary: The arguments behind the data builder and its implementer — why source→product, why the contract is authored first, why quality is a gate, why every mart reconciles to its source, why the review loop is capped at three rounds, why the builder and the implementer are two agents, and why the clade ships one rule.
references:
  - rules/reconciliation.md
  - docs/reconciliation.md
  - ahrena-engineering-fundamentals:rules/contract-first.md
  - ahrena-engineering-fundamentals:rules/ubiquitous-language.md
---

# Why Clio builds the way it does

`agents/clio.md` and `agents/mnemosyne.md` instruct their executors. This is the case for the design they carry out, kept here so that every run does not pay for it in tokens.

## Two agents, one deciding and one writing

Clio decides what gets built, in what order, and whether a layer is ready to stack. Mnemosyne writes one layer. The agent deciding what to build is kept apart from the one marking it done, and Argos, a third party, judges each round.

The split also follows the platform's nesting limit. Athena delegates to Clio, and Clio to Mnemosyne and Argos; that is the third level below the main conversation, which Claude Code allows by default. So Mnemosyne spawns nothing.

## The component map before any name

The concepts this clade leans on (bronze, silver and gold, the data contract, the mart, the expectation) are canonical terms the project's glossary overrides. If the project calls a mart a `view` or gold a `serving` layer, the build produces what the project named, and a folder the project has not sanctioned is a folder no agent creates on its own authority. This is `ahrena-engineering-fundamentals:rules/ubiquitous-language.md`, inherited and applied.

## Source→product, one direction only

Schema, then medallion, then expectations, then marts. The dependency runs from the source outward to the product, and each layer is tested green before the one that depends on it is started, so a wrong contract or a wrong transform surfaces against a cheap test rather than against a finished mart a consumer is already reading.

## The contract first, and the layers evolve from it

The data contract is the first artifact, authored, not generated, and the data-contract test is written red against it before any transform exists. The medallion carries data toward the shape it pins, the expectations gate against the invariants it declares, and the mart satisfies it end to end. This is `ahrena-engineering-fundamentals:rules/contract-first.md`, applied to data: a contract that can disagree with the pipeline is the only one that can catch the change that breaks a consumer.

## Quality is a gate, not a report

The expectations layer (freshness, uniqueness, nullability, accepted ranges) is a bar the data clears before it flows on, not a dashboard read after the fact. A layer whose expectations are red does not hand data to the layer above it.

## Every mart reconciles to its source

No mart opens without a reconciliation that ties its figures back to the source the contract pinned, which is `rules/reconciliation.md`; `docs/reconciliation.md` argues why. A mart can pass its schema contract test and still carry wrong numbers.

## Three review rounds, then stop

Inside a layer the implementer develops, Argos reviews the working diff, and the implementer develops again against its findings, for at most three rounds, before the layer opens. Argos reviews again on the pull request itself; the in-loop rounds spend the cheap feedback before the expensive one. A layer still failing after three rounds has a wrong model below it, which is a finding for that layer, not a fourth round.

## One rule of its own

The strongest data guardrail on shape, that the contract is authored and the pipeline validated against it, already lives in `ahrena-engineering-fundamentals:rules/contract-first.md`, so the clade applies it rather than restating it. It ships its own rule only for the guardrail fundamentals does not reach: a mart's figures reconciling to its source, a content check no shape contract decides.

## A merge is refused, not put to a person

The controls in `ahrena-foundation:skills/writing-system-prompts/references/controls.md` have an agent return `NEEDS_APPROVAL` when it is asked for an irreversible action its procedure does not name. Clio and Mnemosyne deviate from that on purpose. No step of theirs ever merges, lands, force-pushes, deletes a branch or closes an issue, and no approval could make them do it, so a `NEEDS_APPROVAL` would offer the person a choice that does not exist. They refuse instead and name the owner: the builder under `left:`, an implementer as `BLOCKED`. Landing belongs to the review on the pull request, run by the caller.

## Why the implementers run on Sonnet

Mnemosyne take `model: sonnet` because their work is one bounded layer, driven by tests and reviewed by Argos every round, which makes it most of the run's tokens and needs none of the orchestration judgment the builder keeps on `opus`.

## Where this stops

This explains the design; it does not instruct a run. The procedure is in the agents and in `skills/building-data-contract-first/SKILL.md`, and where this page and those disagree, they win and this page is stale. Whether a data product is wanted, whether its contract models the right grain, and any routing decision that spans concerns are outside this design: the first two are the owner's, the third Athena's.
