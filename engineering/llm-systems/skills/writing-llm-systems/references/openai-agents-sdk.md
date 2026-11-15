# OpenAI Agents SDK

For several agents with handoffs, guardrails and sessions on OpenAI models (`docs/frameworks.md`). Facts read on 2026-11-15; open the linked page before relying on one.

**Install and pin.** `pip install openai-agents` ([overview](https://openai.github.io/openai-agents-python/)). Pin the version.

**Tools and handoffs.** A function becomes a tool; a handoff is presented to the model as a tool such as `transfer_to_refund_agent`, and `Agent.as_tool` nests a specialist without handing the conversation over ([handoffs](https://openai.github.io/openai-agents-python/handoffs/)). Prefer `as_tool` (`docs/multi-agent.md`). Input, output and tool guardrails raise tripwire exceptions such as `InputGuardrailTripwireTriggered` ([tripwires](https://openai.github.io/openai-agents-python/guardrails/#tripwires)); map each to an outcome.

**Bound.** `Runner.run`, `run_sync` and `run_streamed` take `max_turns`; past it the SDK raises `MaxTurnsExceeded`, and `None` disables the limit ([agent loop](https://openai.github.io/openai-agents-python/running_agents/#the-agent-loop)). The default is 10 ([result reference](https://openai.github.io/openai-agents-python/ref/result/)); set it explicitly anyway (`rules/loop-bounds.md` condition 3). `error_handlers={"max_turns": ...}` returns a controlled output instead of raising ([error handlers](https://openai.github.io/openai-agents-python/running_agents/#error-handlers)).

**Stub.** `agents.testing` provides `ScriptedModel`, `ModelStep`, `function_call()` and `assistant_message()`, which run in memory with no model request; pass it as `Agent(model=...)`, run with `RunConfig(tracing_disabled=True)`, then call `model.assert_complete()` ([testing](https://openai.github.io/openai-agents-python/testing/)).

**Sessions.** `SQLiteSession`, `RedisSession`, `SQLAlchemySession` and others keep memory across runs ([sessions](https://openai.github.io/openai-agents-python/sessions/)); scope a session to its owner.

**Evaluation.** A script that runs each case through `Runner.run` and grades the outcome. Do not build on OpenAI's hosted Evals platform: it shuts down on 2026-11-30 ([evals](https://developers.openai.com/api/docs/guides/evals)).

**Tracing.** On by default, to OpenAI; `trace_include_sensitive_data` defaults to `True`. Set it to `False` unless the design places content, or disable tracing with `RunConfig.tracing_disabled` and emit your own spans ([tracing](https://openai.github.io/openai-agents-python/tracing/), [sensitive data](https://openai.github.io/openai-agents-python/tracing/#sensitive-data)).

**Other models.** Through `Model` / `ModelProvider` and the LiteLLM adapter ([models](https://openai.github.io/openai-agents-python/models/)).
