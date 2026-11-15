# Design: <component name in the project's vocabulary>

Issue: <#n> · Date: <yyyy-mm-dd> · Author: <agent or person>

## Job

- In: <what the system receives>
- Out: <what it returns, to whom>
- Success criteria: <specific, measurable, one per line>
- Latency budget: <p50 / p95, or "not stated">
- Cost budget per request: <amount, or "not stated">
- Data: <personal / regulated / none; where it may be sent>
- Side effects: <what the system may change, send, delete or pay for, or "none">

## Evaluation cases (first set)

| # | Input (summary) | Pass when | Source (real / issue example) |
|---|---|---|---|

## Shape

- Rung: <1 single call | 2 workflow: pattern | 3 agent | 4 several agents: manager or hand-off>
- Evidence for each rung below: <run date, cases failed, why the shape and not the prompt; or "rung 1, no climb">
- What would make it climb: <the result that would justify the next rung>

## Framework

- Choice: <provider SDK, no framework | framework@version>
- Need that holds today: <row of docs/frameworks.md and evidence, or "none">
- Costs accepted: <abstraction / upgrade churn / defaults / lock-in, each with a line, or "not applicable">
- Defaults set explicitly: <loop bound, trace destination, ...>

## Tools

| Tool | Description (as the model reads it) | Input schema | Validation in code | Acts as | Effect gated by | Output bound |
|---|---|---|---|---|---|---|

reviewing-model-use: <findings, or "not run: plugin not installed">

## Loop

- Bound: <turns / tokens / budget / time, and how the size was chosen>
- Success stop reason: <e.g. end_turn>
- Other endings and what the caller receives: <bound reached, max_tokens, refusal, context full, error>

## Context and memory

- Loaded up front: <...>
- Fetched when needed: <...>
- Clearing or compaction: <what and why, or "none needed">
- Memory across runs: <what, scoped to whom, kept how long, or "none">
- Hand-off contract (rung 4): <task, constraints, known facts, answer shape>

## Evaluation and tests

- Set lives at: <path>
- Command: <one line>
- Threshold: <...>
- Graders: <criterion: code | model (not the evaluated one) | person>
- Deterministic tests: <what is stubbed, with which stub>

## Tracing

- Spans: <model call, tool call, agent>
- Convention: <OpenTelemetry GenAI, version followed>
- Content: <not recorded | stored at ..., readable by ..., kept for ...>

## Cost

- Per request: <calls × tokens in/out × price read on <date> from <pricing page>, or "not computed" with the inputs>
- Levers applied: <...>

## Open questions

- <question, and who answers it>
