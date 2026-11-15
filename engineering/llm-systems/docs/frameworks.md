---
id: frameworks
type: doc
clade: engineering
subclade: llm-systems
title: With or Without a Framework
summary: Whether an LLM system is built on the provider's SDK alone or on an agent framework, which framework fits which problem, what each one costs, and when it is the wrong choice; the default is the provider's SDK with no framework.
references:
  - docs/choosing-the-shape.md
---

# With or Without a Framework

This is the second decision a design makes, after the shape ([`choosing-the-shape.md`](choosing-the-shape.md)). The default is **the provider's SDK and direct API calls, with no framework**. A framework is adopted only when something it brings is needed now, and the design writes down what it costs. Every statement here about a framework links the framework's own documentation, read on 15/11/2026; a framework changes faster than this page, so a design re-reads the linked page before relying on a detail.

## Why no framework is the default

Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents#when-and-how-to-use-frameworks) suggests that developers start by using LLM APIs directly, warns that frameworks create extra layers of abstraction that can obscure the underlying prompts and responses, and asks that anyone who does use one understand the code underneath. The argument holds for every vendor, not only Anthropic's:

- **Rungs 1 and 2 of the ladder need nothing a framework adds.** A single call is one request. A fixed workflow is ordinary code calling that request in sequence, in parallel or behind a router; the control flow is the language's own.
- **A tool loop is short.** With the Claude API the model answers with `stop_reason: "tool_use"` and one or more `tool_use` blocks, the code runs each tool and sends back a `tool_result` matched by `tool_use_id`, and the loop ends when the answer has no tool call ([Claude: how tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview#how-tool-use-works)). The OpenAI Responses API has the same shape, a `function_call` item answered by a `function_call_output` with the same `call_id` ([OpenAI: function calling](https://developers.openai.com/api/docs/guides/function-calling)). Written by hand, the loop is a few dozen lines the team can read, test and bound.
- **The provider's SDK already validates tool input.** Claude's `strict: true` on a tool definition guarantees that the tool's `input` follows its `input_schema` ([strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use)); OpenAI's strict mode does the same for function arguments, with `additionalProperties: false` and every property required ([function calling](https://developers.openai.com/api/docs/guides/function-calling)).

## What a framework costs

The design names each of these for the framework it picks, or says why one does not apply.

- **Abstraction over the prompt.** What is actually sent to the model is assembled by code the team did not write. Debugging a wrong answer starts by finding the prompt.
- **Upgrade churn.** Frameworks change defaults between minor versions. LangGraph's default recursion limit, the bound on an agent's steps, became 10,000 in 1.0.6 and 10,007 in 1.1.4 ([LangGraph: recursion limit](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)); a system that relied on the default changed behaviour on an upgrade. Hosted services move too: OpenAI's Evals platform goes read-only on 31/10/2026 and shuts down on 30/11/2026 ([OpenAI: evals](https://developers.openai.com/api/docs/guides/evals)).
- **Defaults that are not the system's.** Several frameworks run an agent with no bound unless one is passed, or send traces to a vendor unless told not to (the table below).
- **Lock-in to the framework's concepts.** State graphs, handoffs, sessions and middleware are the framework's vocabulary. Leaving it means rewriting the orchestration, not swapping an import.

## Per problem

| Problem | Recommended | Why | Wrong choice when |
|---|---|---|---|
| A single call or a fixed workflow (rungs 1 and 2) | No framework: the provider's SDK | Nothing to orchestrate beyond ordinary code; the prompt stays in view | The workflow must survive a process restart mid-run and resume, or pause for hours for a person: see durable execution below |
| One agent over the system's own tools, in-process, short-lived | No framework: a hand-written loop on the provider's SDK; on Claude, the SDK's tool runner is acceptable | The loop is short and the bound and stop are the team's code. The [tool runner](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner) runs the loop and ends at `max_iterations` when set, but is beta, and its page sends human approval, custom logging and conditional execution back to the manual loop | The agent needs file, shell and code-editing tools with permissions, or several agents with handoffs: the rows below |
| An agent that works in a workspace: reads and edits files, runs commands, searches | [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) | Ships the tools, agent loop and context management of Claude Code as a library, with hooks, permission modes, sessions, subagents and MCP ([capabilities](https://code.claude.com/docs/en/agent-sdk/overview#capabilities)) | The agent needs only a few tools of its own: the built-in set is a wider authority than the task, and removing it with `disallowed_tools` and a permission mode is work a hand-written loop never needed. Also wrong off Claude |
| A long-running or asynchronous agent in a sandbox, with little infrastructure of the team's own | [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview) | A pre-built agent harness on managed infrastructure, meant for long-running and asynchronous work, with sessions and environments the platform keeps | The data may not leave for a hosted harness: the page states it is not ZDR or HIPAA eligible except self-hosted for ZDR. It is beta, behind a header, and Claude-only |
| Several agents with handoffs, guardrails and session memory, on OpenAI models | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) | Few primitives (agents, handoffs, guardrails, sessions, tracing) over plain Python; handoffs are tools to the model ([handoffs](https://openai.github.io/openai-agents-python/handoffs/)) | One agent would do (rung 4 not justified), or the traces may not go to OpenAI: tracing is on by default and includes sensitive data by default ([tracing](https://openai.github.io/openai-agents-python/tracing/#sensitive-data)) |
| Durable execution: a run that is checkpointed, survives a restart, and pauses for a person for hours or days | [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) with a production checkpointer | A low-level runtime for long-running, stateful agents; checkpointers persist each thread's state, and `interrupt()` pauses until resumed with `Command(resume=...)` ([persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)) | The flow is a plain loop or chain that finishes in one request. LangGraph's own overview says to start from LangChain agents or Deep Agents unless explicit control over state and control flow is needed |
| One agent whose model provider must be swappable now, inside a LangChain codebase | [LangChain `create_agent`](https://docs.langchain.com/oss/python/langchain/agents) | A model calling tools in a loop, built on LangGraph, customised through middleware ([overview](https://docs.langchain.com/oss/python/langchain/overview)) | Portability is anticipated rather than needed: a second provider that is not in use today is not a reason (`choosing-the-shape.md`, the evidence rule) |
| An agent on AWS, with Bedrock models and AWS tooling | [Strands Agents](https://strandsagents.com/) | Amazon Bedrock is the default provider ([quickstart](https://strandsagents.com/docs/user-guide/sdk/quickstart/python/#run-your-first-agent)); `@tool` turns a function into a tool; traces go out over OpenTelemetry ([traces](https://strandsagents.com/docs/user-guide/sdk/observability-evaluation/traces/#opentelemetry-integration)); multi-agent patterns start from agents as tools ([patterns](https://strandsagents.com/docs/user-guide/sdk/multi-agent/multi-agent-patterns/)) | The system is not on AWS, or the team needs a documented way to stub the model in tests: the documentation has no testing page, so a test double means implementing the abstract model class ([`Model`](https://strandsagents.com/docs/api/python/strands.models.model/)) |

## The loop bound each framework starts with

An agent's bound is the design's to set (`choosing-the-shape.md`, rung 3). What happens when it is left out differs:

| Stack | Bound | Default |
|---|---|---|
| Claude API tool runner | `max_iterations` | none set: runs until no tool use ([tool runner](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner#iterating-over-the-tool-runner)) |
| Claude Agent SDK | `max_turns`, `max_budget_usd` | no limit on either; the page calls a budget "a good default for production agents" ([turns and budget](https://code.claude.com/docs/en/agent-sdk/agent-loop#turns-and-budget)) |
| OpenAI Agents SDK | `max_turns`, raising `MaxTurnsExceeded` | 10 ([result reference](https://openai.github.io/openai-agents-python/ref/result/), [agent loop](https://openai.github.io/openai-agents-python/running_agents/#the-agent-loop)) |
| LangGraph and LangChain agents | `recursion_limit`, raising `GraphRecursionError` | 10,007 super-steps since 1.1.4 ([recursion limit](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)) |
| Strands Agents | `limits` on turns and tokens | none: "No limit applies unless you pass one" ([invocation limits](https://strandsagents.com/docs/user-guide/sdk/agents/agent-loop/#invocation-limits)) |

None of these defaults is a bound a design chose, so the design states its own in every case.

## What the design records

When the answer is no framework, one line: "provider SDK, no framework", and the provider. When it is a framework, three things: the need from the table above that holds **today**, with the evidence; the framework and its version; and the costs from "What a framework costs" that apply, each accepted in writing. A need that cannot be stated takes the default.

## Where this stops

This page chooses whether and which framework. It does not choose the shape ([`choosing-the-shape.md`](choosing-the-shape.md)), the model, or the cloud; a model's capabilities and price are on its provider's model pages, and a cloud's managed AI services are the cloud plugin's. It does not teach any framework's API; the linked pages do.

Frameworks not listed here (Rivet and Vellum are named in Anthropic's article, and there are many more) are not rejected by omission. A design that proposes one argues it against the same four costs and the same evidence rule.
