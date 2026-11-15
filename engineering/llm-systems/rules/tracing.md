---
id: tracing
type: rule
clade: engineering
subclade: llm-systems
title: Every Model and Tool Call Is Traced Without Sensitive Content by Default
statement: Every model and tool call emits a span; a model-call span records the model, tokens and stop reason; content only where the design allows it.
enforcement: judgment
references:
  - docs/observability.md
---

# Every Model and Tool Call Is Traced Without Sensitive Content by Default

An LLM system that misbehaves is diagnosed from its trace: which model was called with what, which tool ran, what it cost and why the run stopped. What to record and how, and the conventions that make traces portable, are in [`docs/observability.md`](../docs/observability.md).

## Conditions

1. **Every model call and every tool call in a run emits a span, and the spans of one run share a trace.** Decided by review, and by a test that runs the component with a stub model and an in-memory exporter.
2. **A model-call span records the model identifier requested, the input and output token counts, and the stop reason.** Decided by review.
3. **A run records how it ended: success, the bound reached, a refusal, a truncation or an error.** Decided by review; the outcomes are those of `rules/loop-bounds.md` condition 5.
4. **Prompt text, model output and tool arguments are not recorded unless the design names where they go, who can read them and for how long; where a framework records them by default, the code turns that off or the design accepts it.** The OpenAI Agents SDK's `trace_include_sensitive_data` defaults to `True`. Decided by review, with the security plugin's exposure rule.
5. **The prompt version and the model identifier of a run can be recovered from its trace, so an evaluation result can be matched to the configuration that produced it.** Decided by review.

## Where this stops

**Dashboards and alerts** on these spans are the observability plugin's. **Where traces are exported** (a vendor, a collector) is the design's, under condition 4.
