# Symptoms and their usual causes

Read by step 4 of `debugging-llm-systems`. Each row goes from what the trace shows to the cause to check first, then the fix and its source. Check the cause against the reproduction before applying the fix.

| Symptom in the trace | Check first | Usual fix | Source |
|---|---|---|---|
| The answer ignores a fact that was in the context | Context size near the window; the fact buried among stale tool results | Fetch the fact when needed; clear old tool results; shorten the history | `docs/context-and-memory.md`; [context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) |
| The answer states something not in any source | Whether retrieval returned the source at all; opaque ids in tool results | Fix retrieval; return names, not ids, from tools | [Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| The output stops mid-sentence and is returned as an answer | `stop_reason` is `max_tokens` or `model_context_window_exceeded`, treated as success | Handle each stop reason as its own outcome; raise `max_tokens` or shorten the input | `rules/loop-bounds.md` condition 5; [stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons) |
| An empty or declining answer | `stop_reason` is `refusal`; the prompt or the input | Handle refusal as an outcome; check whether the input is one the system should refuse | [stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons#refusal) |
| The wrong tool is called, or two tools alternate | Overlapping tool descriptions; similar names | Sharpen descriptions, namespace, merge overlapping tools | `docs/tools.md` |
| Invalid arguments, repeated | The description and parameter names; strict mode off | `strict: true`; unambiguous parameter names; an error result that says what to send | `rules/tool-definitions.md`; [Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| The run ends with an exception from a tool | A handler that raises on bad input | Return an error result the model can act on | `rules/tool-definitions.md` condition 3 |
| The loop reaches its bound on tasks it should finish | Redundant calls; pagination; a missing tool | Bound tool output, add the missing tool; do not raise the bound first | `docs/agent-loop.md`, "Choosing the size" |
| The loop never ends, or cost explodes | No bound set; a bound of `None`; a framework default | Set the bound in code | `rules/loop-bounds.md`; `hooks/check-loop-bounds.py` |
| Cost or latency rose with no code change | Cache hit rate fell (a changing prefix); a model or tokenizer change | Stable content first in the prompt; recount tokens per model | `docs/cost-and-latency.md`; [token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) |
| Results changed after an upgrade | The model identifier or the framework version moved; a changed default | Pin the model and the framework; set defaults in code; rerun the set | `rules/framework-adoption.md`; [model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions) |
| A sub-agent's work is lost or contradicted by the manager | The hand-off message omits what the sub-agent found | Write the hand-off as a contract; pass a reference to stored output | `docs/multi-agent.md` |
| Passes alone, fails sometimes | Sampling variance; pass@k mistaken for pass^k | Measure over several trials; fix for consistency | [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
