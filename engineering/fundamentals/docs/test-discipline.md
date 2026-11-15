---
id: test-discipline
type: doc
clade: engineering
subclade: fundamentals
title: Test placement, order and traceability
summary: Why a unit test sits beside its file, why it is written red first, why every criterion is traced, and where each of those figures comes from.
references:
  - rules/test-discipline.md
  - rules/contract-tests.md
---

# Test placement, order and traceability

This document explains `rules/test-discipline.md`: TST-1, TST-2 and TST-3 of the PR quality rubric of epic 323.

## Where the figures come from

Every threshold in the rubric is one of three things: measured on a corpus, inherited from a named source, or declared maintainer policy (issue 34's standard). None of the three conditions here is measured, and the document says so rather than dressing them up.

- **TST-1 is maintainer policy.** The owner's directive for every language plugin is that the unit test sits beside its file. It departs from common practice in some ecosystems, and the Go plugin's testing doc measures how far (62% of the files with behaviour in four packages of the Go standard library, 273 files in all, have no test named for them). The policy is held anyway because a reader who opens a file finds its test without a search, and a file with no test is visible by its missing neighbour. The threshold of 100% is on the files the change adds or changes, not the legacy tree, so it cannot be met by a mass rename.
- **TST-2 is maintainer policy**, inherited in shape from test-driven development. A test that has never failed has not been shown able to fail, so the red commit is the evidence that the test tests something.
- **CTR-1 and CTR-2 are inherited and policy.** The 100% of CTR-1 is inherited from `rules/contract-first.md` condition 3, which argues why complete coverage is the only informative figure when the unit is an operation. The one test per adapter of CTR-2 is maintainer policy, the floor that shows the adapter reaches the real dependency; the backend plugin's `driving-with-tdd` asks for the same test at the persistence layer.
- **TST-3 is inherited from `contributing/rules/traceability.md`**, which already decides it with a hook. It appears here only so the whole test rubric reads in one place.

## Why a folder convention is enough for TST-1

The condition reads file names, which is what a script can decide with no judgment in it. It cannot read the quality of the test, and does not try; the coverage and mutation conditions do that.

## Where this stops

This document does not choose a test runner or a naming convention beyond the one beside-the-file rule; those are each language plugin's.
