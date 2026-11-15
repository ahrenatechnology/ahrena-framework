---
id: simplest-shape
type: rule
clade: engineering
subclade: llm-systems
title: An LLM System Takes the Lowest Rung That Works
statement: An LLM system above a single call names the rung below it and the evaluation evidence that it fails; with no such evidence it takes the lower rung.
enforcement: judgment
references:
  - docs/choosing-the-shape.md
---

# An LLM System Takes the Lowest Rung That Works

The four rungs are a single call, a fixed workflow in code, one autonomous agent, and several agents, in that order. The ladder, and the evidence each step up needs, are in [`docs/choosing-the-shape.md`](../docs/choosing-the-shape.md).

## Conditions

1. **A design names its rung, and a change that adds a model call states which rung the component it belongs to sits on.** Decided by review of the design or the pull request.
2. **A rung above the first names the rung below and the evidence that it fails: an evaluation run, the cases that failed, and why they trace to the shape rather than to the prompt, the retrieval or the tools.** "It may need to grow", a diagram, and the organisation of the code are not evidence. Decided by review.
3. **A loop in which the model chooses the next tool (rung 3) exists only where the step order cannot be written before the run.** A loop whose tool sequence is the same on every evaluation case is a workflow written as an agent. Decided by review against the evaluation's traces.
4. **A second agent (rung 4) exists only where one agent with the same tools has been run against the evaluation set and its failure is recorded.** Decided by review.

## Where this stops

**A vendor's finished assistant** used as is, with no prompt or tool of the system's own, has no shape to choose.

**A prototype** made to learn whether a task is possible at all may start on any rung; condition 2 applies when it is proposed for production, and the prototype's runs are then the evidence.

**Migrating down** is not required of a system that predates its design; a reviewer reports the simpler shape (condition 2) and the owner decides when to move.
