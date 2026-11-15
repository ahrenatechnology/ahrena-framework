---
id: context-and-memory
type: doc
clade: engineering
subclade: llm-systems
title: Context and Memory
summary: Why an LLM system treats its context window as a budget, what each technique for keeping it small costs (retrieval just in time, tool-result clearing, compaction, notes outside the window), and how memory that outlives a run is stored and scoped.
references:
  - docs/agent-loop.md
---

# Context and Memory

Everything a model sees on a request is its context: the system prompt, the tool definitions, the messages, the tool results, and on the Claude API the output and its thinking too ([context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)). An agent's context grows with every turn. This document is about keeping it small enough to work, and about what survives when a run or a session ends.

## Context is a budget, not a container

A bigger window is not free room. Claude's documentation names context rot: as the context grows, accuracy and recall degrade ([context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)). Anthropic's engineering post asks that context be treated as a finite resource with diminishing returns, and the goal stated as the smallest set of high-signal tokens that gets the outcome ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). LangChain's memory guide makes the same point from cost: long histories distract the model with stale content and make responses slower and dearer ([managing short-term memory](https://docs.langchain.com/oss/python/concepts/memory#manage-short-term-memory)). Cached tokens count too; caching changes what they cost, not whether they occupy the window ([context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)).

## Keeping it small, cheapest first

1. **Load what is needed when it is needed.** Keep identifiers (paths, queries, links) in context and fetch the content with a tool at the step that needs it, instead of loading everything up front ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). Retrieval for a single call (rung 1) is the same idea, decided before the call.
2. **Return less from tools.** A paginated, truncated tool result never needs clearing ([`tools.md`](tools.md)).
3. **Clear old tool results.** Anthropic calls tool-result clearing one of the safest, lightest forms of compaction ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). On the Claude API, context editing's `clear_tool_uses_20250919` strategy replaces old results with a placeholder once a trigger is crossed, keeping the most recent few; it is beta, and clearing invalidates the cached prefix, so it is tuned to clear enough at once to be worth the cache write ([context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)).
4. **Compact.** Summarise the conversation near the limit and continue from the summary ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). The Claude API offers it server-side, in beta, on demand or at a token threshold; the summary is a separate sampling call billed on its own line ([compaction](https://platform.claude.com/docs/en/build-with-claude/compaction), [threshold mode](https://platform.claude.com/docs/en/build-with-claude/compaction-threshold#understanding-usage)). A summary loses detail by design, so what must not be lost is written down first (the next section).
5. **Give a subtask its own context.** A sub-agent can spend tens of thousands of tokens and hand back a summary of one or two thousand ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). This is a step to rung 4 and is argued as one ([`multi-agent.md`](multi-agent.md)).

## Memory that outlives the context

Two kinds, and a design says which it needs:

- **Within a run or a thread** (short-term). The conversation so far. In LangGraph it is thread-scoped state that a checkpointer persists so the thread can resume ([short-term memory](https://docs.langchain.com/oss/python/concepts/memory#short-term-memory)); in the Claude Agent SDK a session id resumes a session ([sessions](https://code.claude.com/docs/en/agent-sdk/agent-loop#sessions-and-continuity)); in the OpenAI Agents SDK a session object stores it ([sessions](https://openai.github.io/openai-agents-python/sessions/)).
- **Across runs** (long-term). Facts, preferences and progress that a later run reads. LangGraph keeps them as JSON documents in a store, scoped by namespace ([long-term memory](https://docs.langchain.com/oss/python/concepts/memory#long-term-memory)). Claude's memory tool has the model ask for file operations under `/memories` that the application runs against storage it controls ([memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)); the documented multi-session pattern is a progress log and a checklist read first and updated last.

Long-term memory is data the system stores about people, written by a model whose input may carry an attacker's text. So it is scoped to its owner (the tenant, the user), validated on write as a tool's input is, given a retention period, and kept out of reach of other owners. The memory tool's documentation asks for path validation, size caps, expiry and stripping sensitive data ([path traversal protection](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool#path-traversal-protection)). Where a model can read one owner's memory into another's run is the security plugin's [`reviewing-model-use`](../../security/skills/reviewing-model-use/SKILL.md).

## When this does not apply

A single call with a fixed prompt has no context to manage beyond its prompt and no memory. A short agent whose evaluation cases all finish far inside the window needs none of steps 3 to 5; adding compaction to it adds a sampling call and a loss of detail for nothing.

## Where this stops

Retrieval as a data system (indexing, chunking, embedding stores) is a design of its own, made with the data plugin and the cloud plugin; this document covers what reaches the model's context, not how the corpus is built.
