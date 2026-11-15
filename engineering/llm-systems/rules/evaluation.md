---
id: evaluation
type: rule
clade: engineering
subclade: llm-systems
title: Every LLM Component Ships With an Evaluation That Runs
statement: Every component that calls a model has an evaluation set in the repository with a pass threshold, run by one command and rerun on every prompt or model change.
enforcement: judgment
references:
  - docs/evaluation.md
---

# Every LLM Component Ships With an Evaluation That Runs

A unit test with the model stubbed shows the code around the model is right. Only an evaluation against the real model shows the system does its job, and only a rerun shows a change did not make it worse. How to build one, and how to grade with a model, are in [`docs/evaluation.md`](../docs/evaluation.md).

## Conditions

1. **Each component that calls a model has an evaluation set in the repository: cases drawn from real or realistic inputs, including the edge cases the design names, each with what a pass is.** Decided by review.
2. **The evaluation states its pass threshold and its success criteria before it is run, and one command runs it and reports pass or fail against them.** Decided by review, and by running the command.
3. **A change to a prompt, a model identifier, a tool definition or the shape reruns the evaluation, and the pull request shows the result beside the previous one.** Decided by review of the pull request.
4. **A case that failed in production, or that a debugging session found, is added to the set before the fix is merged.** Decided by review.
5. **Where a model grades, the grading prompt is versioned with the set, the grader is not the model being evaluated, and its verdicts have been compared with a person's on a sample the evaluation names, with the agreement recorded.** Decided by review.
6. **The code around the model has deterministic tests with the model stubbed, which run without network or credentials.** Decided by review, and by the project's test run.

## Where this stops

**The size of the set, the threshold and the calibration sample.** None is set here; the evaluation states its own, and the design argues them from the task. `docs/evaluation.md` gives the published starting points.

**Online evaluation** of production traffic is observability ([`docs/observability.md`](../docs/observability.md)); it complements the offline set and does not replace it.
