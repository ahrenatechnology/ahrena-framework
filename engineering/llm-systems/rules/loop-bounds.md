---
id: loop-bounds
type: rule
clade: engineering
subclade: llm-systems
title: Every Agent Loop Has a Bound and a Defined End
statement: An agent loop has a turn or budget bound set by the system, ends on a stop reason it handles, and reaching the bound returns a defined outcome.
enforcement: hook
enforced-by: hooks/check-loop-bounds.py
references:
  - docs/agent-loop.md
  - docs/frameworks.md
---

# Every Agent Loop Has a Bound and a Defined End

A loop in which the model decides whether to call another tool stops for one of two reasons: the model is done, or a limit the system set is reached. Both ends are written in the code, and neither is left to a framework's default. Why, and what each stack offers, are in [`docs/agent-loop.md`](../docs/agent-loop.md) and in the bound table of [`docs/frameworks.md`](../docs/frameworks.md).

## Conditions

1. **A hand-written loop that calls a model is a `for` over a bound, never `while True`.** Decided in Python by `hooks/check-loop-bounds.py`; in any other language by review.
2. **A Claude Agent SDK run sets `max_turns` or `max_budget_usd`.** The SDK applies no limit to either by default. Decided in Python by `hooks/check-loop-bounds.py`, on `ClaudeAgentOptions`; in TypeScript by review, on `maxTurns` and `maxBudgetUsd`.
3. **A framework's bound is set or kept, never removed: the Claude SDK's tool runner is given `max_iterations`, the OpenAI Agents SDK's runner is not given `max_turns=None`, a Strands agent is given `limits`, and a LangGraph or LangChain agent states its `recursion_limit`.** The first two are decided in Python by `hooks/check-loop-bounds.py`; the last two, and every case in another language, by review.
4. **Reaching the bound returns a defined outcome to the caller: a typed failure, a partial result marked as partial, or a hand-off to a person, never the last model message presented as an answer.** Decided by review, and by a test that runs the loop with a stub model that always calls a tool and asserts on the outcome.
5. **The loop ends as success only on the stop reason that means the model finished (`end_turn` on the Claude API, a final output with no tool call on the OpenAI Agents SDK); a truncation, a refusal or a full context window is handled as its own outcome.** On the Claude API those are `max_tokens`, `refusal` and `model_context_window_exceeded`. Decided by review.

## Where this stops

**A single call and a fixed workflow.** A workflow's step count is the code's, so it has no agent loop. An evaluator-optimiser loop is a loop, and condition 1 reads it.

**The size of a bound.** No number is set here, because none is attributable across tasks; the design states its bound and the evaluation set shows the task completes inside it. A bound that the evaluation keeps hitting is a finding for the design, not for this rule.

**Cost limits outside the loop.** A spend cap on the provider's account, or a rate limit, is operations, not code.
