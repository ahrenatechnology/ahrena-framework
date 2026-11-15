---
id: observability
type: doc
clade: engineering
subclade: llm-systems
title: Tracing an LLM System
summary: What a trace of an LLM system records - a span per model call and tool call, the model, tokens and stop reason - in the OpenTelemetry GenAI conventions, what each stack emits, and why prompt and output content stays out of traces unless a design puts it somewhere safe; the companion of the tracing rule.
references:
  - rules/tracing.md
---

# Tracing an LLM System

This is the rationale behind [`rules/tracing.md`](../rules/tracing.md). An agent that did the wrong thing is diagnosed from its trace: which model was called, which tools ran with what result, how many tokens each step took, and why the run stopped. Anthropic's research team reports that full production tracing is what let them find why agents failed ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).

## The shape of a trace

One trace per run; inside it, one span per model call and one per tool call, nested under an agent span when there is one. OpenTelemetry's semantic conventions for generative AI name these, and following them keeps a trace readable by any backend. They are in **Development** status, so names may still change, and the normative text has moved from opentelemetry.io to the project's own repository ([moved notice](https://opentelemetry.io/docs/specs/semconv/gen-ai/), [GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md)):

- **Model call.** Span name `{gen_ai.operation.name} {gen_ai.request.model}`; required `gen_ai.operation.name` and `gen_ai.provider.name`; recommended `gen_ai.response.finish_reasons`, `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens` ([inference spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-inference.md)).
- **Tool call.** Span name `execute_tool {gen_ai.tool.name}`, with the tool's name required and its call id when there is one ([execute tool](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/execute-tool.md)).
- **Agent.** `invoke_agent {gen_ai.agent.name}`, a client span for a remote agent and an internal one in-process ([agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)).

Because the conventions are not stable, a system that adopts them pins the version it follows and says so in its design.

## Content stays out by default

Prompts, outputs and tool arguments carry what users typed and what tools returned: personal data, secrets in a pasted file, another tenant's records if something already went wrong. The GenAI conventions treat them as sensitive and say instrumentations should not capture them by default; for production they recommend storing content externally and recording a reference ([content capture](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md#full-buffered-content)). Anthropic's research team monitored decision patterns and interaction structure rather than conversation contents for the same reason ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).

Stacks disagree here, and the difference is a default to override, not to inherit:

| Stack | What it emits | Content by default |
|---|---|---|
| OpenAI Agents SDK | traces, on by default, to OpenAI's tracing ([tracing](https://openai.github.io/openai-agents-python/tracing/)) | included: `trace_include_sensitive_data` is `True` ([sensitive data](https://openai.github.io/openai-agents-python/tracing/#sensitive-data)) |
| Claude Agent SDK | nothing of its own; the Claude Code process it runs exports metrics, events and, in beta, traces ([SDK observability](https://code.claude.com/docs/en/agent-sdk/observability#how-telemetry-flows-from-the-sdk), [traces](https://code.claude.com/docs/en/monitoring-usage#traces-beta)) | structural only; prompts and tool content are opt-in ([sensitive data](https://code.claude.com/docs/en/agent-sdk/observability#control-sensitive-data-in-exports)) |
| LangChain and LangGraph | LangSmith tracing when enabled by environment ([observability](https://docs.langchain.com/oss/python/langchain/observability)) | the run's inputs and outputs, sent to LangSmith |
| Strands Agents | OpenTelemetry, with an OTLP or console exporter ([traces](https://strandsagents.com/docs/user-guide/sdk/observability-evaluation/traces/#opentelemetry-integration)) | per the instrumentation's configuration |
| Hand-written loop | whatever the code emits | nothing, unless the code adds it |

A token count can also mean different things: Claude Code's `input_tokens` excludes cache tokens, and it does not set the `gen_ai.usage.*` attributes ([mapping to GenAI conventions](https://code.claude.com/docs/en/monitoring-usage#map-input-tokens-to-opentelemetry-genai-semantic-conventions)). A dashboard that adds tokens across stacks normalises them first.

## What else a trace carries

The prompt version and the model identifier, so a regression seen in production is matched to the change that caused it and to the evaluation run of that change. How the run ended, in the outcomes of [`rules/loop-bounds.md`](../rules/loop-bounds.md). Cost, where the stack reports it (the Claude Code metrics include a cost in dollars ([metrics](https://code.claude.com/docs/en/monitoring-usage#metrics))), or tokens from which cost is computed.

## Where this stops

Alerts, dashboards and on-call are the observability plugin's. Where trace data may be sent and for how long is the design's, under the security plugin's exposure rule. Online evaluation (grading a sample of production traffic) uses these traces and is built like the offline set in [`evaluation.md`](evaluation.md).
