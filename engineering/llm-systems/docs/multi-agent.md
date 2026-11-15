---
id: multi-agent
type: doc
clade: engineering
subclade: llm-systems
title: Several Agents and the Handoff Between Them
summary: When a second agent earns its cost, the two ways agents divide work (a manager calling agents as tools, or peers handing off), what crosses a handoff and what is lost in it, and how a multi-agent system is bounded and evaluated.
references:
  - docs/choosing-the-shape.md
  - rules/simplest-shape.md
---

# Several Agents and the Handoff Between Them

Rung 4 of [`choosing-the-shape.md`](choosing-the-shape.md), and condition 4 of [`rules/simplest-shape.md`](../rules/simplest-shape.md): a second agent exists only where one agent with the same tools has been tried and its failure recorded. This document says what that failure usually looks like, and how the second agent is built when it is justified.

## What it costs

Anthropic measured its research system: agents use about four times the tokens of a chat, and multi-agent systems about fifteen times ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)). The same system beat a single agent by a wide margin on its internal research evaluation, and token usage alone explained most of the variance in performance. The two facts go together: a multi-agent system mostly buys the ability to spend more tokens in parallel, and it pays off when the task is valuable enough to fund that.

## When it fits

From the same post: tasks with heavy parallelisation, information that exceeds one context window, and many complex tools. It is a poor fit where all agents need the same context, or where the parts depend on one another; Anthropic notes that most coding tasks have fewer truly parallel parts than research ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)). OpenAI's guide gives the same order: maximise a single agent first, and split when the logic grows too branched or the tools overlap too much for one prompt ([practical guide, p. 16](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)).

## Two ways to divide the work

- **A manager calls agents as tools.** One agent keeps the conversation and calls specialists the way it calls a tool, receiving their result. The OpenAI Agents SDK provides `Agent.as_tool` for this ([handoffs](https://openai.github.io/openai-agents-python/handoffs/)); Strands' patterns page tells the reader to start here ([multi-agent patterns](https://strandsagents.com/docs/user-guide/sdk/multi-agent/multi-agent-patterns/)); the Claude Agent SDK's subagents work this way ([subagents](https://code.claude.com/docs/en/agent-sdk/subagents)). It keeps one owner of the outcome and is the default.
- **Peers hand off.** One agent transfers the conversation to another and stops. In the OpenAI Agents SDK a handoff is a tool the model sees, such as `transfer_to_refund_agent` ([handoffs](https://openai.github.io/openai-agents-python/handoffs/)); OpenAI's guide calls it a one-way transfer ([practical guide, pp. 17-23](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)). It fits a triage that routes once to a specialist who then owns the conversation. It is also a routing workflow (rung 2) whenever the code could make the routing decision, and that is checked first.

## What crosses the handoff

Each agent sees only its own context, so the handoff is a message, and whatever is not in it is lost. Write it as a contract: the task, the constraints, what is already known, and the shape of the answer expected back. A sub-agent's summary is short by design ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)); where detail must survive, sub-agents write it to a store and pass a reference back, as Anthropic's research system does ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).

## Bounds and authority

Every agent's loop is bounded ([`agent-loop.md`](agent-loop.md)), and so is the whole: the number of sub-agents a manager may start, and a budget across them. Each agent gets the tools its part needs and no more; splitting authority between agents is one of the few good reasons for rung 4, and wasting it by giving every agent every tool removes the reason.

## Evaluating it

Evaluate the system on the outcome, not turn by turn; Anthropic found end-state evaluation the workable approach for stateful agents ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)). Run the same set against the single-agent version: the comparison is the evidence condition 4 of the rule asks for, and it is cheap to keep running.

## Where this stops

This document covers agents inside one system. Agents in different systems talking over a protocol (A2A, a remote agent endpoint) are an integration between services and are designed as one.
