---
id: coverage-by-layer
type: doc
clade: engineering
subclade: quality
title: Coverage by layer and why the domain is mutated
summary: Where each coverage figure comes from, why a coverage percentage alone cannot hold the domain, and what a mutation score adds.
references:
  - rules/coverage-by-layer.md
---

# Coverage by layer and why the domain is mutated

This document explains `rules/coverage-by-layer.md`: COV-1 to COV-5 of the PR quality rubric of epic 323.

## Where the figures come from

Every threshold in the rubric is measured, inherited from a named source, or declared maintainer policy (the standard of issue 34). Nothing in this rule is measured on a corpus. The figures were declared by the maintainer on 14 November 2026 and are policy: 90% of new lines, 80% total, 100% of the domain, 80% of the domain's mutants killed, and 75% at the edge. They are not defaults borrowed from a tool, and a project that wants different ones declares them, with the reason, in its own rules.

The split into new and total is deliberate. A legacy tree under the limit would block every pull request if the limit applied to it, so the limit is on what the change adds and the total is only held from falling.

## Why coverage alone does not hold the domain

A line is covered when a test executed it. A test that calls a function and asserts nothing covers every line it reaches and would pass if the function returned the wrong answer. At 100% coverage that test is indistinguishable from a good one, and the domain, which holds the rules the business pays for, is the layer where it matters.

A mutation run answers the question coverage cannot: it changes the code in small ways, flipping a comparison or deleting a statement, and runs the tests again. A mutant the tests still pass was not noticed. The share of mutants killed is the share of changes the tests would catch. That is why the domain carries both a full coverage figure and a mutation score, and why the other layers carry only coverage: mutation testing is slow, and its cost is justified where an unnoticed change is expensive.

## Why the edge is lower

The edge is code that talks to something else: a socket, a database, a provider. A line there is only meaningfully exercised against the real thing, so the figure is held lower, at 75%, and is reached through the contract and integration tests of `engineering/fundamentals/rules/contract-tests.md` rather than through fakes that would raise the number and prove nothing.

## Where this stops

This document does not choose a coverage tool, a mutation tool or a report format. Those are the project's, and each language plugin's testing doc names the ones it recommends.
