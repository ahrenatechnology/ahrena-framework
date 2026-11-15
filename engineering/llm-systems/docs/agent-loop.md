---
id: agent-loop
type: doc
clade: engineering
subclade: llm-systems
title: The Agent Loop and How It Ends
summary: What an agent loop is in each stack, the two ways it may end - the model is done, or a bound is reached - the stop reasons that are neither, and how a bound is chosen and handled; the companion of the loop-bounds rule.
references:
  - rules/loop-bounds.md
  - docs/frameworks.md
---

# The Agent Loop and How It Ends

This is the rationale behind [`rules/loop-bounds.md`](../rules/loop-bounds.md). An agent is a model calling tools in a loop until it decides it is done. That one sentence describes every stack in [`frameworks.md`](frameworks.md); what differs is who writes the loop and what stops it when the model does not.

## The loop in each stack

- **Claude API, by hand.** Call the model; if `stop_reason` is `tool_use`, run each `tool_use` block and send the `tool_result`s back; otherwise stop ([how tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview#how-tool-use-works)).
- **OpenAI Responses API, by hand.** The same, with `function_call` items answered by `function_call_output` ([function calling](https://developers.openai.com/api/docs/guides/function-calling)).
- **Claude Agent SDK.** One turn is model output followed by any tool calls; the loop ends at output with no tool call ([turns and messages](https://code.claude.com/docs/en/agent-sdk/agent-loop#turns-and-messages)).
- **OpenAI Agents SDK.** Call the model; a final output ends, a handoff switches agent and continues, tool calls run and continue; past `max_turns` it raises `MaxTurnsExceeded` ([the agent loop](https://openai.github.io/openai-agents-python/running_agents/#the-agent-loop)).
- **LangChain and LangGraph.** An agent is a model calling tools in a loop until the task is complete ([agents](https://docs.langchain.com/oss/python/langchain/agents)), run as graph super-steps under a `recursion_limit` ([recursion limit](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)).
- **Strands Agents.** Invoke the model, run a tool if it asks for one, invoke again ([how the loop works](https://strandsagents.com/docs/user-guide/sdk/agents/agent-loop/#how-the-loop-works)).

## Two good endings and several bad ones

A loop ends well in one of two ways: the model finishes, or a bound the system set is reached and the system says so. Everything else is a failure with a name, and treating it as an answer is the defect.

On the Claude API the stop reasons are listed together ([handling stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)): `end_turn` is the model finishing; `tool_use` continues the loop; `max_tokens` means the output was cut; `refusal` means the model declined; `model_context_window_exceeded` means the context filled and the output is truncated; `pause_turn` means a server-side loop paused and the content must be sent back to continue. Only the first is success. A loop that returns the last text whenever it is not `tool_use` reports a truncated or refused answer as a finished one.

## Why a bound, and why the system sets it

Anthropic's guidance for agents is to include stopping conditions such as a maximum number of iterations ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents#building-blocks-workflows-and-agents)). Without one, a model that keeps finding another tool to call spends without limit, and a loop stuck between two tools never returns. The frameworks disagree on the default: none on the Claude Agent SDK and Strands, ten turns on the OpenAI Agents SDK, about ten thousand super-steps on LangGraph ([`frameworks.md`](frameworks.md), "The loop bound each framework starts with"). A bound inherited from a default was chosen by a framework's maintainers for nobody's task, and it changes on upgrade. So the system states its own.

A bound can be on turns, on tokens, on money or on time. Turns are the simplest to reason about; money is what the business feels. The Claude Agent SDK takes both `max_turns` and `max_budget_usd` and calls a budget a good default for production ([turns and budget](https://code.claude.com/docs/en/agent-sdk/agent-loop#turns-and-budget)).

## Choosing the size

No number fits every task, and this plugin sets none. The evaluation set chooses it: run the cases, look at how many turns the passing ones took, and set the bound with room above the longest. A bound the evaluation never approaches is too loose to catch a runaway; a bound the evaluation keeps hitting is a design problem (a missing tool, a vague description, the wrong rung), not a reason to raise it.

## When the bound is reached

The caller has to be able to tell. Return a typed failure, or a partial result marked as partial, or hand the run to a person, which OpenAI's guide names as the response to exceeded failure thresholds ([practical guide, p. 31](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)). The OpenAI Agents SDK lets an error handler for `max_turns` return a controlled output instead of raising ([error handlers](https://openai.github.io/openai-agents-python/running_agents/#error-handlers)).

## Testing the ending

Each ending gets a deterministic test with the model stubbed: a stub that answers at once (success), one that always asks for a tool (the bound), one that returns each bad stop reason. These run with no network. LangChain documents fake chat models for this ([unit testing](https://docs.langchain.com/oss/python/langchain/test/unit-testing#mock-chat-model)) and the OpenAI Agents SDK a scripted model ([testing](https://openai.github.io/openai-agents-python/testing/)); where a stack documents none, the stub implements the stack's model interface, or the hand-written loop takes the client as a parameter.

## Where this stops

This document covers one loop. What fills its context as it runs is [`context-and-memory.md`](context-and-memory.md); loops that hand work to one another are [`multi-agent.md`](multi-agent.md); what the loop costs is [`cost-and-latency.md`](cost-and-latency.md).
