---
id: framework-adoption
type: rule
clade: engineering
subclade: llm-systems
title: An Agent Framework Is Adopted Only With a Recorded Need and Cost
statement: An agent framework enters a project only with a need that holds today, its version pinned and its costs accepted in writing; otherwise the provider's SDK.
enforcement: judgment
references:
  - docs/frameworks.md
---

# An Agent Framework Is Adopted Only With a Recorded Need and Cost

The default is the model provider's SDK with no framework. Which framework fits which problem, and the four costs a framework brings, are in [`docs/frameworks.md`](../docs/frameworks.md).

## Conditions

1. **A dependency on an agent framework (the Claude Agent SDK, the OpenAI Agents SDK, LangChain, LangGraph, Strands Agents, or any other library that runs the model loop) arrives with a written decision naming the need it meets today and the evidence for it.** An anticipated need, such as a second provider not in use, is not one. Decided by review of the manifest change and the design or decision record it cites.
2. **The decision names the costs from `docs/frameworks.md` that apply (abstraction over the prompt, upgrade churn, defaults that are not the system's, lock-in) and accepts each.** Decided by review.
3. **The framework's version is pinned in the manifest or lockfile, so an upgrade is a change someone reviews.** Decided by review, and by the project's lockfile check where one runs.
4. **Every framework default that changes the system's behaviour, at least the loop bound and where traces are sent, is set explicitly in code.** Decided by review; the loop bound is also `rules/loop-bounds.md`.

## Where this stops

**The provider's own client SDK** (`anthropic`, `openai`, and their equivalents) is not a framework here. It sends requests; it does not run the loop. Its helpers that do run the loop, such as the Claude SDK's tool runner, fall under condition 4 and not condition 1.

**Libraries around the model call** (an HTTP client, a schema validator, an evaluation or tracing library) are ordinary dependencies, governed by the project's dependency rules.
