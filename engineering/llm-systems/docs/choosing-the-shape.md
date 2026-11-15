---
id: choosing-the-shape
type: doc
clade: engineering
subclade: llm-systems
title: Choosing the Shape of an LLM System
summary: The four shapes an LLM system can take, from one model call to several agents, the order they are tried in, the condition that justifies each step up, and the evidence that shows the step below has failed.
---

# Choosing the Shape of an LLM System

An LLM system is any software that sends a model a prompt and acts on what comes back. Its shape is how many model calls it makes and who decides their order: the code, or the model. This document is the ladder the design climbs, one rung at a time, and the evidence each rung needs before the next is taken. It rests on Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), whose advice is to find the simplest solution possible and increase complexity only when needed.

The ladder is about the shape, not the vendor. Whether a framework is used to build the chosen shape is a separate decision, argued in [`frameworks.md`](frameworks.md).

## Why the order matters

Each rung trades something for something. A step up buys flexibility in what the system can do and pays for it in latency, cost, and the ability to predict and test what it will do. Anthropic's article draws the central line between **workflows**, where the model and its tools are orchestrated through predefined code paths, and **agents**, where the model directs its own process and tool use. A workflow can be read, tested path by path, and bounded in cost; an agent's path is decided at run time, so its tests are statistical and its cost has to be capped rather than computed.

The most expensive mistake in this area is a shape the problem did not need: an agent where a fixed sequence of calls would do, or several agents where one with more tools would. It is expensive because nothing fails. The system works, slower and dearer than it had to be, and harder to change, and nobody can point at the line that made it so.

## Rung 1: a single call

One request to the model, with what it needs in the prompt: instructions, the input, and, when one call alone gets it wrong, retrieved context or worked examples. Most classification, extraction, summarisation, rewriting and drafting tasks are this rung.

**It is enough when** one well-written prompt, evaluated against a set of real inputs, meets the quality bar. Retrieval and examples are part of this rung, not a step up: they change what is in the prompt, not how many calls are made.

**It has failed when** the evaluation shows a quality ceiling that prompt work, retrieval and examples have not moved, and the failures trace to the task having distinct parts that interfere in one prompt, or to needing an outside result (a lookup, a computation) the model cannot produce. "It might need more later" is not evidence.

## Rung 2: a fixed workflow in code

Several model calls whose order the code decides. Anthropic's article names five patterns, and a design names the one it uses:

| Pattern | What the code does | Fits when |
|---|---|---|
| Prompt chaining | Runs a sequence of calls, each on the last one's output, with checks between them | The task splits cleanly into fixed subtasks, and accuracy is worth the extra latency |
| Routing | Classifies the input and sends it to a specialised prompt, model or tool | Inputs fall into distinct categories that are better handled apart |
| Parallelisation | Runs calls at once and merges them: independent subtasks (sectioning), or the same task several times (voting) | Subtasks are independent, or several attempts give more confidence than one |
| Orchestrator-workers | One call breaks the task into subtasks it chooses, workers run them, and the results are combined | The subtasks cannot be listed in advance, but the overall flow can |
| Evaluator-optimiser | One call produces, another evaluates against stated criteria, in a bounded loop | Clear evaluation criteria exist, and iterating measurably improves the result |

A workflow can use tools, including tools the model calls within one step. What makes it a workflow is that the code, not the model, decides which step comes next.

**It is enough when** the steps can be written down before the run. Most systems that look like they need an agent are a routing step in front of a few chains.

**It has failed when** the cases that fail need a step order the code cannot know in advance: the number of steps, or which tool comes next, depends on what earlier tool results revealed, and enumerating those paths in code would mean writing the planner by hand.

## Rung 3: one autonomous agent

The model runs in a loop, chooses which tool to call with what input, reads the result, and decides whether to call another or stop. The code supplies the tools, the stop conditions and the bounds; the model supplies the path.

**It fits when** the problem is open-ended, the number of steps cannot be predicted, and the environment gives the model feedback it can act on at each step: a test result, a search result, an error. Coding against a test suite is the canonical case.

**It costs** more tokens and latency per task, compounding errors across steps, and a path that differs between runs. So it ships with what rungs 1 and 2 do not need as urgently: a bound on turns or tokens, a defined stop, tools whose effects are limited to what the task needs, and an evaluation set run as a statistic rather than a single pass. A design at this rung states each of the four.

**It has failed when** one agent, given the tools it needs, cannot do the task, and the failure traces to the work itself rather than to a missing tool, a vague tool description or a weak prompt. The usual remedies are better tools and a better prompt, and they come first.

## Rung 4: several agents

More than one agent, each with its own prompt, tools and context, handing work to one another or coordinated by one of them.

**It fits when** one agent's context cannot hold what the task needs at once, or parts of the work need tools or permissions that must not share one context, or independent parts gain from running in parallel with separate contexts. A multi-agent system is a distributed system: it adds handoff, the state that crosses it, and failures in the seams between agents.

**It has failed to be justified when** the reason given is the organisation of the code ("one agent per responsibility") rather than a limit one agent has actually hit. Splitting a prompt into several agents does not make each part better; it adds a handoff each part can lose information in. One agent with more tools is ruled out first, with the evidence.

## What a design writes down

A design names the rung it chose. For every rung above the first, it names the rung below and the evidence that it fails: the evaluation result, the failing cases, and why they trace to the shape rather than to the prompt or the tools. A design that cannot cite that evidence takes the lower rung and records what would make it climb.

A step up later is cheap when the step down was honest. A single call that grows into a chain keeps its prompt and its evaluation set; a chain that becomes an agent keeps its tools. A system built at rung 3 from the start has no lower-rung baseline to compare against when somebody asks whether the agent earns its cost.

## Where this stops

This document chooses the shape. It does not choose a framework ([`frameworks.md`](frameworks.md)), and it does not say how to define a tool, bound a loop, keep memory or evaluate a run. Prompt injection, and what a tool may be allowed to do on a model's say-so, are the security discipline in [`reviewing-model-use`](../../security/skills/reviewing-model-use/SKILL.md).

It does not apply to a product that only puts a vendor's finished assistant in front of users with no prompt or tool of its own; there is no shape to choose. And a ladder is a default order, not a quota: a problem whose first evaluation already shows it needs rung 3 records that evidence and starts there.
