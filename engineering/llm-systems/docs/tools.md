---
id: tools
type: doc
clade: engineering
subclade: llm-systems
title: Designing Tools a Model Calls
summary: How a tool is designed for a model as its caller - its name, description and schema, what it returns, how it fails, and how much it may do - and why each choice changes what the model does; the companion of the tool-definitions rule.
references:
  - rules/tool-definitions.md
---

# Designing Tools a Model Calls

This is the rationale behind [`rules/tool-definitions.md`](../rules/tool-definitions.md). A tool is an interface whose only reader is a model, at run time, with nothing but its definition. Anthropic calls this the agent-computer interface and asks for as much care in it as in a human-computer one ([Building effective agents, appendix 2](https://www.anthropic.com/engineering/building-effective-agents#appendix-2-prompt-engineering-your-tools)). Most of what goes wrong in an agent goes wrong at a tool: the model picks the wrong one, sends the wrong arguments, or drowns in what one returned.

## The definition is a prompt

On the Claude API a tool is a `name`, a `description` and an `input_schema` in JSON Schema ([how tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview#how-tool-use-works)); on the OpenAI Responses API it is a `name`, a `description`, `parameters` and `strict` ([function calling](https://developers.openai.com/api/docs/guides/function-calling)). The model reads all of it to decide whether and how to call.

- **Describe it as to a new hire.** Anthropic's guide asks for the description you would give a new colleague: what the tool does, when to use it, the implicit context made explicit, and parameter names that cannot be misread (`user_id`, not `user`) ([Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)). A good definition includes example usage, edge cases and input format requirements ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents#appendix-2-prompt-engineering-your-tools)).
- **Make mistakes hard to make.** "Poka-yoke your tools": change the arguments so the wrong call is harder to express, as Anthropic did by requiring absolute file paths ([appendix 2](https://www.anthropic.com/engineering/building-effective-agents#appendix-2-prompt-engineering-your-tools)).
- **Namespace when there are many.** Prefixes by service or resource (`asana_search`, `asana_projects_search`) help the model tell similar tools apart ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)).
- **Fewer tools is usually better.** Anthropic names bloated tool sets as one of the most common failure modes ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)); OpenAI's guide observes that overload depends on how much tools overlap, not on their count ([A practical guide to building agents, p. 16](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)). A tool that overlaps another is merged or removed before a second agent is considered.

## The schema constrains; the code still decides

`strict: true` on a Claude tool guarantees the input follows the schema and the tool name is valid ([strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use)); OpenAI's strict mode requires `additionalProperties: false` on every object and every property in `required` ([function calling](https://developers.openai.com/api/docs/guides/function-calling)). That removes malformed calls. It does not make the values safe: a schema cannot say that an order id belongs to the caller, or that a path stays under a root. The memory tool's documentation shows the case: the handler must validate every path against traversal such as `/memories/../../secrets.env` ([memory tool: path traversal](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool#path-traversal-protection)). So the tool's code validates again, at its own edge, as it would any untrusted input.

## What a tool returns

- **Signal, not identifiers.** Return the fields the model can reason with and resolve opaque ids to names; Anthropic reports that this reduces hallucination ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)).
- **Bounded.** Paginate, filter, select a range or truncate with sensible defaults; Claude Code caps a tool response at 25,000 tokens by default ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)). When a result is cut, say so and say how to get the rest.
- **A choice of detail.** A `response_format` parameter with `concise` and `detailed` lets the model ask for less; the guide's example went from 206 tokens to 72 ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)).

## How a tool fails

An error goes back to the model as a tool result, so it is written for the model: what was wrong and what to do instead. The guide's phrase is to prompt-engineer error responses rather than return opaque codes or tracebacks ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)). A raised exception that escapes the tool ends the loop and teaches the model nothing; a traceback in the result spends tokens and may leak what the security plugin's exposure rule keeps in.

## How much a tool may do

A tool runs on a model's decision, and the model's input can carry an attacker's text. So a tool holds the least authority the task needs: it acts as the person or tenant the run is for, not as a service account that can reach everyone's data, and an action that changes, sends, deletes or spends is either confirmed by a person or limited by code. OpenAI's guide rates tools by risk and calls for human intervention on high-risk actions ([practical guide, pp. 26-27, 31](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)). What an attacker can make a model do through a tool is the subject of the security plugin's [`reviewing-model-use`](../../security/skills/reviewing-model-use/SKILL.md), and a tool review runs it.

## Tools are tested twice

A unit test calls the tool with valid, invalid and hostile inputs, with no model involved. An evaluation then runs the agent on real tasks and reads its transcripts for wrong tool choices, redundant calls and invalid parameters; many redundant calls point at pagination or limits, many invalid parameters at the description ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)). Keep a held-out set so the descriptions are not tuned to the evaluation itself.

## Where this stops

This document designs the tool. When a model should be given tools at all is [`choosing-the-shape.md`](choosing-the-shape.md); the loop that calls them is [`agent-loop.md`](agent-loop.md); server tools a provider runs for you are configured, not designed here.
