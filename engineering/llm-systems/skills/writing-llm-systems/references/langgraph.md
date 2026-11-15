# LangChain and LangGraph

For durable execution, a run that pauses for a person, or a LangChain codebase (`docs/frameworks.md`). Facts read on 2026-11-15; open the linked page before relying on one.

**Which one.** LangChain's `create_agent` is a model calling tools in a loop, built on LangGraph and customised with middleware ([agents](https://docs.langchain.com/oss/python/langchain/agents)). LangGraph is the low-level runtime; its overview says to start from LangChain agents or Deep Agents unless explicit control over state and control flow is needed ([LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)). Take the lowest one that serves. Pin the versions of every LangChain package.

**Tools.** Define tools with explicit schemas and descriptions; the model's tool schema is what the model reads (`docs/tools.md`). Validate again in the tool's body.

**Bound.** `recursion_limit`, a top-level key of the run's config, bounds super-steps and raises `GraphRecursionError`; the default is 10,007 since 1.1.4 and changed in earlier minor versions ([recursion limit](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)). Set it explicitly on every invoke, and catch the error into an outcome.

**Durability and people.** A checkpointer persists each thread's state by `thread_id`: `InMemorySaver` in tests, `PostgresSaver` in production ([persistence](https://docs.langchain.com/oss/python/langgraph/persistence)). `interrupt()` pauses a run until it is resumed with `Command(resume=...)` on the same thread ([interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)): this is the gate for a tool's irreversible effect. Long-term memory goes in a store, by namespace ([memory](https://docs.langchain.com/oss/python/concepts/memory#long-term-memory)).

**Stub.** `GenericFakeChatModel` and `FakeListChatModel` script the model's replies; for `create_agent` with tools, subclass `GenericFakeChatModel` and make `bind_tools` return `self`; use `InMemorySaver` for multi-turn tests ([unit testing](https://docs.langchain.com/oss/python/langchain/test/unit-testing#mock-chat-model)).

**Evaluation.** Keep the set in the repository; LangSmith can run it as an experiment with code, LLM-as-judge or human evaluators ([LangSmith evaluation](https://docs.langchain.com/langsmith/evaluation)).

**Tracing.** LangSmith tracing is turned on by environment variables and sends the run's inputs and outputs to LangSmith ([observability](https://docs.langchain.com/oss/python/langchain/observability)); confirm the design allows that destination before enabling it.
