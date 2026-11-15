---
id: evaluation
type: doc
clade: engineering
subclade: llm-systems
title: Evaluating an LLM System
summary: Why an LLM system needs an evaluation beside its tests, what one is made of (tasks, trials, graders, outcomes), how a model grades and how that grader is calibrated, how many cases to start with, and how the evaluation is run on every change; the companion of the evaluation rule.
references:
  - rules/evaluation.md
---

# Evaluating an LLM System

This is the rationale behind [`rules/evaluation.md`](../rules/evaluation.md). A unit test with the model stubbed shows that the code around the model is correct. It cannot show that the system does its job, because the job is done by the model. An evaluation runs the real model on a set of cases and measures the result against criteria written down before the run. It is also the only evidence [`choosing-the-shape.md`](choosing-the-shape.md) accepts for climbing a rung.

## Two kinds of test

| | Tests | Evaluation |
|---|---|---|
| Model | stubbed | real |
| Result | pass or fail, every time | a rate over many cases and trials |
| Runs | on every commit, offline | on every change to a prompt, model, tool or shape, and before a release |
| Catches | wrong parsing, unhandled stop reasons, tool errors, the bound | wrong answers, wrong tool choices, regressions in quality |

Both are written. The tests come first, red, for the code around the call ([`agent-loop.md`](agent-loop.md), "Testing the ending"); the evaluation's first cases are written before the prompt is tuned, so the prompt is tuned to something.

## What an evaluation is made of

Anthropic's post on agent evaluations gives the vocabulary ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)):

- a **task** is one test with defined inputs and success criteria;
- a **trial** is one attempt at it, and a task gets several because outputs vary;
- a **grader** scores some aspect of a trial;
- the **transcript** is the complete record of a trial;
- the **outcome** is the final state of the environment, such as the reservation row that exists, not the agent saying it booked one.

Grade the outcome where there is one. For an agent that changes state, Anthropic found end-state evaluation workable where turn-by-turn analysis was not ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).

Two numbers summarise trials: pass@k, the chance that at least one of k trials succeeds, which rises with k; and pass^k, the chance that all k succeed, which falls with k and measures consistency ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)). A system a person relies on every time is judged on the second.

## Success criteria first

Claude's documentation asks for criteria that are specific, measurable, achievable and relevant, and notes that most uses need several dimensions at once, such as task fidelity, consistency, tone, privacy, latency and price ([develop tests](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)). Writing them before the run is what makes the threshold a decision rather than a description of whatever the first run produced.

## How many cases

Start small and real. Anthropic suggests twenty to fifty simple tasks drawn from real failures as a start ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)), and its research team began with about twenty queries, because early changes have large effects that a small set already shows ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)). Claude's guide prefers volume to hand-polished cases once grading is automated ([develop tests](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)). The set grows from production: every failure found is a new case before it is fixed. Keep part of the set held out, so prompts and tool descriptions are not tuned to the cases that measure them ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)).

## Who grades

- **Code** where the answer can be checked: exact match, a parsed field, a row in a database. Fast and objective, brittle at the edges.
- **A model** where judgment is needed: a rubric, a score, a pass or fail. Flexible and not deterministic, so it is calibrated ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)). Anthropic's research team found one call returning a score from 0.0 to 1.0 and a pass or fail against a rubric the most consistent ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)). Claude's guide advises grading with a different model from the one evaluated ([develop tests](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)); OpenAI's asks for judges calibrated against human labels ([evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)).
- **A person** to set the ground truth the model grader is calibrated against, and to find what the set misses; people testing agents find edge cases evaluations miss ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).

## Capability and regression

A capability evaluation measures something the system cannot yet do well and starts low; a regression evaluation guards what it already does and should pass at close to all of it ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)). The regression set is the one every change runs.

## Where it lives and how it runs

In the repository, beside the component: the cases, the grader prompts, the criteria and the threshold, versioned with the prompt they measure. One command runs it and prints pass or fail against the threshold, so a pull request can show the result next to the last one. Hosted evaluation services are a convenience on top, not the home of the set: OpenAI's Evals platform shuts down on 30/11/2026 ([evals](https://developers.openai.com/api/docs/guides/evals)), and a set that lived there leaves with it. LangSmith ([evaluation](https://docs.langchain.com/langsmith/evaluation)) and Strands Evals ([evals SDK](https://strandsagents.com/docs/user-guide/evals-sdk/)) can run a set kept in the repository.

## Where this stops

This document covers offline evaluation of one component. Watching production traffic is [`observability.md`](observability.md). Red-teaming a system for prompt injection is the security plugin's [`reviewing-model-use`](../../security/skills/reviewing-model-use/SKILL.md), though its attack cases belong in the set once found.
