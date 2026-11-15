# Provider SDK, no framework

The default stack (`docs/frameworks.md`). The loop is the project's own code, so every part of it is visible and testable. Facts read on 2026-11-15; open the linked page before relying on one.

## Claude API

**Tool.** A dict with `name`, `description`, `input_schema` (JSON Schema) and `strict: True`, which guarantees the input follows the schema ([strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use)); close every object with `"additionalProperties": False` ([structured outputs, JSON Schema limitations](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations)).

**Loop.** Call `client.messages.create`; while `stop_reason == "tool_use"`, run each `tool_use` block and send a `tool_result` with the same `tool_use_id` ([how tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview#how-tool-use-works)). Write it as a `for` over a bound, never `while True`:

```python
for _ in range(MAX_TURNS):
    response = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, tools=TOOLS, messages=messages)
    if response.stop_reason != "tool_use":
        return outcome_for(response)  # end_turn is success; every other reason its own outcome
    messages += [{"role": "assistant", "content": response.content}, {"role": "user", "content": run_tools(response)}]
raise TurnLimitReached(messages)
```

The stop reasons and what each means are on [handling stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons). The SDK's tool runner runs the same loop for you; it is beta and needs `max_iterations` set ([tool runner](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner)).

**Stub.** No official fake client is documented for the Anthropic SDK. Take the client as a parameter of the function that holds the loop, and pass a test double whose `messages.create` returns scripted responses with the `stop_reason` and `content` the test needs.

## OpenAI Responses API

**Tool.** `{"type": "function", "name", "description", "parameters", "strict": True}`; strict needs `additionalProperties: false` on every object and every property in `required`, with optional fields typed as nullable. Set `strict` explicitly: when it is omitted the Responses API only attempts strict mode ([function calling](https://developers.openai.com/api/docs/guides/function-calling)).

**Loop.** `client.responses.create`; for each `function_call` item, run it and send a `function_call_output` with the same `call_id`, until a response carries no function call ([function calling](https://developers.openai.com/api/docs/guides/function-calling)). Success is a response with `status: "completed"` and no function call; `status: "incomplete"` (the reason in `incomplete_details.reason`) and a `refusal` content item are each their own outcome ([Responses object](https://developers.openai.com/api/reference/resources/responses/methods/create)). Same bounded `for`. Passing `previous_response_id` keeps state on the server but still bills every earlier input token ([conversation state](https://developers.openai.com/api/docs/guides/conversation-state)).

**Stub.** As for Claude: inject the client, script its `responses.create`.

## Both

**Evaluation.** A script in the repository that runs each case through the real component and grades it, printing the pass rate against the threshold; nothing in either SDK is required for it. Where a model grades, call a different model with a grading prompt kept in the set.

**Tracing.** Emit spans with the OpenTelemetry SDK around each model and tool call, named and attributed per the GenAI conventions ([inference spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-inference.md), [execute tool](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/execute-tool.md)). In tests, the OpenTelemetry Python SDK's `InMemorySpanExporter` (`opentelemetry.sdk.trace.export.in_memory_span_exporter`), which its source describes as meant for testing, keeps finished spans for `get_finished_spans()` ([source](https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/export/in_memory_span_exporter.py)).
