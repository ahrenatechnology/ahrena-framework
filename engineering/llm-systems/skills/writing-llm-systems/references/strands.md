# Strands Agents

For an agent on AWS with Bedrock models (`docs/frameworks.md`). Facts read on 2026-11-15; open the linked page before relying on one.

**Install and pin.** Python `strands-agents`, TypeScript `@strands-agents/sdk` ([Strands](https://strandsagents.com/)). Amazon Bedrock is the default provider, with a default model and region ([quickstart](https://strandsagents.com/docs/user-guide/sdk/quickstart/python/#run-your-first-agent)); set the model explicitly so an SDK upgrade does not change it.

**Tools.** `@tool` turns a function into a tool; its docstring and type hints tell the model when and how to call it ([add tools](https://strandsagents.com/docs/user-guide/sdk/quickstart/python/#add-tools-to-your-agent)). Write the docstring as the tool's description (`docs/tools.md`) and validate the arguments again in the body.

**Bound.** The loop invokes the model, runs a tool if asked, and invokes again ([agent loop](https://strandsagents.com/docs/user-guide/sdk/agents/agent-loop/#how-the-loop-works)). Pass `limits` on turns and tokens; no limit applies unless one is passed, and a reached limit ends with a stop reason such as `limit_turns` ([invocation limits](https://strandsagents.com/docs/user-guide/sdk/agents/agent-loop/#invocation-limits)). A truncated response raises `MaxTokensReachedException` ([exceptions](https://strandsagents.com/docs/user-guide/sdk/agents/agent-loop/#maxtokensreachedexception)). Map each to an outcome.

**Several agents.** The patterns page starts from agents as tools, then swarm, graph and workflow ([multi-agent patterns](https://strandsagents.com/docs/user-guide/sdk/multi-agent/multi-agent-patterns/)); take agents as tools unless the design argues otherwise.

**Stub.** The documentation has no testing page. Implement the abstract model class (`stream`, `update_config`, `get_config`, `structured_output`) as a scripted test double and pass it to the agent ([`Model`](https://strandsagents.com/docs/api/python/strands.models.model/)); this use is not documented by Strands, so keep the double small and covered by the evaluation.

**Evaluation.** Strands Evals (`strands-agents-evals`) provides cases, experiments and output and trajectory evaluators ([evals SDK](https://strandsagents.com/docs/user-guide/evals-sdk/)); keep the cases in the repository.

**Tracing.** OpenTelemetry with an OTLP or console exporter (`strands-agents[otel]`) ([traces](https://strandsagents.com/docs/user-guide/sdk/observability-evaluation/traces/#opentelemetry-integration)).
