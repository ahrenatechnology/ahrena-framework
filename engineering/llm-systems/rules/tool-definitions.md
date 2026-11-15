---
id: tool-definitions
type: rule
clade: engineering
subclade: llm-systems
title: A Tool Validates What the Model Sends and Can Do Only What the Task Needs
statement: Every tool a model calls has a strict input schema, validates its input again before acting, returns errors the model can act on, and holds least authority.
enforcement: hook
enforced-by: hooks/check-tool-definitions.py
references:
  - docs/tools.md
---

# A Tool Validates What the Model Sends and Can Do Only What the Task Needs

A tool is an interface whose caller is a model. Its arguments are generated text, so they are untrusted input; its effects happen on the model's say-so. How to design one for the model to use well is in [`docs/tools.md`](../docs/tools.md). What an attacker can make a model do with a tool is the security discipline in [`reviewing-model-use`](../../security/skills/reviewing-model-use/SKILL.md), which a review of a tool runs as well.

## Conditions

1. **Every tool has a description that says what it does, when to use it and what each parameter means, and a JSON Schema for its input with every object closed (`additionalProperties: false`).** That a description exists and that every object in a literal schema is closed is decided in Python by `hooks/check-tool-definitions.py`; what the description says, a generated schema, and other languages, by review.
2. **Where the provider offers schema-constrained tool input, it is on: `strict: true` on the Claude API and on OpenAI function tools.** On a tool defined as a literal in Python, decided by `hooks/check-tool-definitions.py`; the Responses API turns strict on when it is omitted, so there only an explicit `False` fails. Otherwise by review.
3. **The tool's code validates its input against the same contract before it acts, and rejects what fails with an error result rather than an exception that ends the loop.** A schema shapes what the model sends; the code still decides what it accepts, including values the schema cannot express (an identifier that must belong to the caller, a path that must stay inside a root). Decided by review, and by a unit test that calls the tool with an invalid input.
4. **An error result says what was wrong and what the model can do next, in words the model can act on, and carries no stack trace, credential or upstream error body.** Decided by review.
5. **A tool acts with the authority of the person or tenant the run is for, never with a broader service identity, and a tool that changes or deletes data, sends a message or spends money is gated: confirmed by a person, or limited by the code to what the task needs.** Decided by review, with `reviewing-model-use`.
6. **A tool's output is bounded: it paginates, truncates or summarises, and says so, instead of returning whatever the source holds.** Decided by review.

## Where this stops

**Server tools a provider runs** (web search, code execution on the provider's side) are configured, not written; conditions 1 to 4 do not reach them, and condition 5 reaches the decision to enable one.

**The model's choice of tool** is the design's and the evaluation's, not this rule's.
