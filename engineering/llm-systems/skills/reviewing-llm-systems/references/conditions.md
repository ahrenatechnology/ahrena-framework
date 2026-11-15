# LLM-system review conditions

The conditions `reviewing-llm-systems` applies, grouped by the rule each comes from. Every condition gives the state, how it is detected, what exempts it (or "none"), the correction, and its source. An exemption here is one the source rule's own conditions or `Where this stops` section grants; nothing else exempts. Severity follows the review that ran this skill: a condition on a line the change adds is reported at the severity that review gives a broken rule. A condition marked as a question is reported as one, naming who answers it.

## Shape (`rules/simplest-shape.md`)

### SHP-1 A rung above 1 without its evidence

- **State:** the change builds a workflow, an agent or several agents, and neither the design nor the pull request cites an evaluation run at the rung below; or it cites one without the failing cases and why they trace to the shape rather than to the prompt, the retrieval or the tools.
- **Detect:** the design and the pull-request text; the evaluation results in the repository.
- **Exempt:** a prototype made to learn whether the task is possible, marked as one and not wired to production (the rule's `Where this stops`).
- **Correct:** name the lower rung, ask for the run against the evaluation set at that rung with the failing cases and their cause, and keep the lower rung until it fails.
- **Source:** rule condition 2.

### SHP-2 An agent whose path is fixed

- **State:** a loop in which the model chooses the next tool, while every evaluation case or test fixture shows the same tools in the same order, or the agent has a single tool it always calls once.
- **Detect:** the evaluation's traces or the test fixtures; the tool list.
- **Exempt:** none.
- **Correct:** replace the loop with a fixed workflow (rung 2): the calls in that order in code, naming the pattern (prompt chaining, routing). One tool called once is a single call with the tool's result fetched by code before it.
- **Source:** rule condition 3; `docs/choosing-the-shape.md`, rung 2.

### SHP-3 A router written as an agent

- **State:** an agent, or a triage agent that hands off, whose only decision is which of several fixed paths takes the input.
- **Detect:** the agent's prompt and its tools or hand-offs; whether anything follows the choice besides the chosen path.
- **Exempt:** none.
- **Correct:** a routing workflow: one classification call, then the path in code.
- **Source:** rule condition 3; `docs/multi-agent.md`, "Two ways to divide the work".

### SHP-4 A second agent with no single-agent run

- **State:** two or more agents with separate prompts and contexts, and no recorded run of one agent with the same tools against the evaluation set.
- **Detect:** the design; the evaluation results.
- **Exempt:** none.
- **Correct:** one agent with the union of the tools, evaluated; a second agent only for the limit the run shows.
- **Source:** rule condition 4; `docs/multi-agent.md`.

### SHP-5 A model call for what code can do

- **State:** a model call whose output is a lookup, a format conversion, arithmetic or a rule that the code could compute exactly.
- **Detect:** the prompt and how its output is used.
- **Exempt:** none.
- **Correct:** reported as a question to the component's owner: whether the code that computes it can replace the call.
- **Source:** `docs/cost-and-latency.md`, "Levers, from structural to tactical", lever 1.

### SHP-6 A model call whose rung is not named

- **State:** the change adds a model call, and neither its design nor the pull request names the rung of the component it belongs to.
- **Detect:** the design and the pull-request text.
- **Exempt:** a vendor's finished assistant used as is, with no prompt or tool of the system's own (the rule's `Where this stops`).
- **Correct:** name the rung in the design or the pull request; the review then applies SHP-1 to it.
- **Source:** rule condition 1.

## Framework (`rules/framework-adoption.md`)

### FWK-1 A framework with no recorded need

- **State:** a manifest or lockfile adds an agent framework (the Claude Agent SDK, the OpenAI Agents SDK, LangChain, LangGraph, Strands Agents, or another library that runs the model loop) and no design or decision record names the need from `docs/frameworks.md` that holds today.
- **Detect:** the manifest diff; the design or record the pull request links.
- **Exempt:** the provider's own client SDK (`anthropic`, `openai`); its loop helpers, such as the Claude SDK's tool runner, are read under FWK-4 and LOOP-3 (the rule's `Where this stops`).
- **Correct:** the provider's SDK with the loop in code, or a written need with its evidence.
- **Source:** rule condition 1.

### FWK-2 A framework wrapping what the SDK does

- **State:** the framework is used for a single call or a fixed workflow (rung 1 or 2) and none of its features in the "Per problem" table of `docs/frameworks.md` is used.
- **Detect:** the imports and calls into the framework.
- **Exempt:** none.
- **Correct:** remove the framework and call the provider's SDK directly; name the calls that replace it.
- **Source:** rule condition 1; `docs/frameworks.md`, first row.

### FWK-3 Costs not accepted, or version not pinned

- **State:** the decision does not name the costs that apply, or the framework's version floats in the manifest with no lockfile.
- **Detect:** the decision text; the manifest and lockfile.
- **Exempt:** none.
- **Correct:** name the costs in the decision; pin the version.
- **Source:** rule conditions 2 and 3.

### FWK-4 A behaviour-changing default inherited

- **State:** the loop bound or the trace destination is the framework's default rather than set in code.
- **Detect:** the run or options call; the tracing configuration.
- **Exempt:** none.
- **Correct:** set it, naming the value.
- **Source:** rule condition 4.

## Tools (`rules/tool-definitions.md`)

Exempt from TOOL-1 to TOOL-4: a server tool the provider runs (web search, code execution on the provider's side), which is configured, not written; TOOL-5 still reads the decision to enable it, and TOOL-6 still applies (the rule's `Where this stops`).

### TOOL-1 Description or schema too thin

- **State:** a tool with no description of when to use it, an ambiguous parameter name, or an object in its schema that is not closed.
- **Detect:** `hooks/check-tool-definitions.py` on Python literals, for a missing description and an open object; reading, for what the description says and for any other form.
- **Exempt:** a provider-run server tool.
- **Correct:** the description and schema `docs/tools.md` asks for.
- **Source:** rule condition 1.

### TOOL-2 Strict mode off where offered

- **State:** a Claude tool, a Responses API function tool or a Chat Completions function defined without `strict: true`.
- **Detect:** `hooks/check-tool-definitions.py` on Python literals; reading elsewhere.
- **Exempt:** a provider-run server tool.
- **Correct:** `strict: true`.
- **Source:** rule condition 2.

### TOOL-3 The handler trusts the model's arguments

- **State:** the handler acts on its input with no validation of its own, or an invalid input raises an exception that ends the loop.
- **Detect:** reading the handler; a unit test that calls it with an invalid input, if one exists.
- **Exempt:** a provider-run server tool.
- **Correct:** validate at the handler's edge and return an error result.
- **Source:** rule condition 3.

### TOOL-4 An error the model cannot act on

- **State:** an error result that is a code, a stack trace, an upstream body, or a credential.
- **Detect:** reading the handler's error paths.
- **Exempt:** a provider-run server tool.
- **Correct:** a sentence saying what was wrong and what to do instead.
- **Source:** rule condition 4.

### TOOL-5 Authority wider than the task, or an ungated effect

- **State:** a tool that acts as a service identity broader than the run's user or tenant, or that changes, sends, deletes or spends with neither a person's confirmation nor a limit in code; or a provider-run server tool enabled with no reason in the design.
- **Detect:** the credentials the handler uses; its side effects; the design.
- **Exempt:** none.
- **Correct:** the run's identity; a confirmation step or a limit.
- **Source:** rule condition 5; with `reviewing-model-use`.

### TOOL-6 Unbounded output

- **State:** a tool that returns everything its source holds.
- **Detect:** reading the handler's return path.
- **Exempt:** none.
- **Correct:** pagination, filtering or truncation that says so.
- **Source:** rule condition 6.

## Loop (`rules/loop-bounds.md`)

Exempt from LOOP-1 to LOOP-5: a single call and a fixed workflow, whose step count is the code's; an evaluator-optimiser loop is a loop and is not exempt (the rule's `Where this stops`).

### LOOP-1 A hand-written loop with no bound

- **State:** a `while True` loop that calls a model.
- **Detect:** `hooks/check-loop-bounds.py` in Python; reading in any other language.
- **Exempt:** a single call or a fixed workflow.
- **Correct:** a `for` over a bound, and the bound-reached outcome of LOOP-4.
- **Source:** rule condition 1.

### LOOP-2 Claude Agent SDK with no bound

- **State:** `ClaudeAgentOptions` (or `maxTurns` / `maxBudgetUsd` in TypeScript) with neither bound set, or set to `None`.
- **Detect:** `hooks/check-loop-bounds.py` in Python; reading in TypeScript.
- **Exempt:** a single call or a fixed workflow.
- **Correct:** set `max_turns` or `max_budget_usd`.
- **Source:** rule condition 2.

### LOOP-3 A framework bound left to its default or removed

- **State:** the tool runner with no `max_iterations`, the OpenAI runner with no `max_turns`, a Strands agent with no `limits`, a LangGraph or LangChain run with no `recursion_limit`, or any of them set to `None`.
- **Detect:** `hooks/check-loop-bounds.py` for the first two in Python; reading for the rest.
- **Exempt:** a single call or a fixed workflow.
- **Correct:** set the bound in code, naming the value.
- **Source:** rule condition 3.

### LOOP-4 The bound reached is not an outcome

- **State:** reaching the bound returns the last message as if it were the answer, or raises an exception the caller does not handle.
- **Detect:** reading the code after the loop; a test with a stub that always calls a tool, if one exists.
- **Exempt:** a single call or a fixed workflow.
- **Correct:** a typed failure, a partial result marked partial, or a hand-off to a person.
- **Source:** rule condition 4.

### LOOP-5 A bad stop reason treated as success

- **State:** the loop returns on anything that is not a tool call, so `max_tokens`, `refusal` or a full context window comes back as an answer.
- **Detect:** reading the loop's exit condition.
- **Exempt:** a single call or a fixed workflow.
- **Correct:** success on the finishing stop reason only; each other reason its own outcome.
- **Source:** rule condition 5; `docs/agent-loop.md`.

## Evaluation (`rules/evaluation.md`)

### EVAL-1 to EVAL-6

- **State:** the rule's conditions: no evaluation set for a component that calls a model (1); no success criteria stated before the run, no threshold or no command (2); a prompt, model, tool or shape change with no rerun shown (3); a production failure fixed with no case added (4); a model grader whose grading prompt is not versioned with the set, that is the evaluated model, or that was never compared with a person (5); code around the model with no deterministic test (6).
- **Detect:** the repository's evaluation directory; the pull-request text; the tests.
- **Exempt:** online evaluation of production traffic does not replace the offline set and does not exempt it (the rule's `Where this stops`); otherwise none.
- **Correct:** what the rule's condition asks, named for this component.
- **Source:** rule conditions 1 to 6.

## Tracing (`rules/tracing.md`)

### TRC-1 to TRC-5

- **State:** the rule's conditions: a model or tool call with no span (1); a model span missing the model, tokens or stop reason (2); no record of how the run ended (3); content recorded without the design placing it, including the OpenAI Agents SDK's `trace_include_sensitive_data` left at its default (4); prompt version or model not recoverable (5).
- **Detect:** the instrumentation and the framework's tracing configuration.
- **Exempt:** none; dashboards, alerts and the export destination are outside the rule (its `Where this stops`), not exemptions from it.
- **Correct:** what the rule's condition asks.
- **Source:** rule conditions 1 to 5.
