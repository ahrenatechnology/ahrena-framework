---
id: cost-and-latency
type: doc
clade: engineering
subclade: llm-systems
title: Cost and Latency
summary: Where an LLM system's cost and latency come from (tokens, calls, the shape), the levers that reduce them in order of how much they change the system - fewer calls, fewer tokens, caching, batching, a smaller model - and how both are measured before and after a change.
references:
  - docs/choosing-the-shape.md
---

# Cost and Latency

An LLM system is paid for in tokens and waited for in calls. Both grow with the rung on the ladder: agents trade latency and cost for better task performance ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents#when-and-when-not-to-use-agents)), using about four times the tokens of a chat, and several agents about fifteen ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)). So the largest lever is the shape itself, and it is pulled first, in [`choosing-the-shape.md`](choosing-the-shape.md).

## Measure before changing

Record per run the input tokens, output tokens, cached tokens, number of model calls and wall time, from the trace ([`observability.md`](observability.md)). OpenAI's latency guide asks for time to first token and end-to-end latency at the 50th and 95th percentile ([latency optimisation](https://developers.openai.com/api/docs/guides/latency-optimization)). Claude's token-counting endpoint estimates a request's input tokens before it is sent, at no charge; it is an estimate, and newer Claude models count the same text as more tokens than older ones, so counts are not reused across models ([token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting)). A cost change is judged with the evaluation run beside it, since a cheaper system that fails more is not cheaper.

## Levers, from structural to tactical

OpenAI's guide lists seven principles; most apply to any provider: process tokens faster, generate fewer, use fewer input tokens, make fewer requests, parallelise, make users wait less, and do not default to an LLM ([seven principles](https://developers.openai.com/api/docs/guides/latency-optimization#seven-principles)). In the order a design reaches for them:

1. **Do not call a model for what code can do.** A lookup, a format, a rule.
2. **Fewer calls.** A lower rung; merging steps of a chain that a single call handles; a router that sends easy inputs to a cheaper path.
3. **Parallel calls** where steps are independent: latency falls, cost does not.
4. **Fewer tokens.** Shorter prompts, bounded tool results ([`tools.md`](tools.md)), cleared context ([`context-and-memory.md`](context-and-memory.md)), and asking for shorter output, since output tokens are generated one at a time.
5. **Cache the stable prefix.** On the Claude API, `cache_control` caches the prefix in the order tools, system, messages; a cache read costs a tenth of base input or less, depending on the model, and a write costs more than base input, so caching pays when the prefix is reused within its lifetime, and it improves time to first token for long prompts ([prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)). OpenAI caches automatically for supported models and discounts cached input heavily ([prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching#why-prompt-caching-matters)). Either way, stable content goes first and anything that changes per request goes last.
6. **Batch what nobody waits for.** Claude's Message Batches API charges half the standard price, most batches finish within an hour and a batch expires at 24 hours ([batch processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing#pricing)); OpenAI's Batch API also discounts by half, within 24 hours ([batch](https://developers.openai.com/api/docs/guides/batch)). Evaluations and back-office jobs are the usual candidates.
7. **A smaller model** for the steps the evaluation shows it handles. OpenAI's guide suggests establishing a baseline with the most capable model, then trying smaller ones ([practical guide, p. 8](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)). The evaluation decides, step by step.

## Hidden costs

Thinking tokens are billed as output ([context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)). Server-side compaction is its own sampling call ([compaction usage](https://platform.claude.com/docs/en/build-with-claude/compaction-threshold#understanding-usage)). Chaining responses with `previous_response_id` on OpenAI still bills every earlier input token ([conversation state](https://developers.openai.com/api/docs/guides/conversation-state)). Clearing tool results invalidates the cache from that point ([context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)). A design that adopts one of these counts it.

## Where this stops

Prices and model capabilities change; this document names the levers and links the pages that carry the numbers, and a design reads those pages on the day it decides. Spending limits on the provider account and rate limits are operations. The agent's own budget bound is [`agent-loop.md`](agent-loop.md).
