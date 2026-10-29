# ADR-018: A process's orchestration is declared data a runtime binds

- **Status:** accepted
- **Date:** 2026-10-19
- **Issue:** #213

## Context

The framework's reason to exist is control of orchestration state that holds the same across platforms. ADR-017 settled this for the agency's manager/worker shape: the spec is portable and each platform binds it. The code-review flow then forced the question one level down. That flow is a state machine — route the change, fan out the lenses the route selects, compose one verdict, hand blocking findings to a separate fixer and re-review under a bounded loop, then a merge gate — and it is realized two ways at once: as the skills a session follows in a framework-only run, and, when the runtime is turned on, as a graph the LangGraph runtime executes.

The tension is where that state machine lives. A runtime that holds the topology in its own code — the nodes, the edges, the loop bound, the escalation threshold — is faster to write and is the obvious shape for a graph library. But a process encoded in one runtime's code is a process that exists only on the platform that runtime serves, and the next platform's binding reimplements it from a reading of the code rather than from a shared source. Two bindings that each hold their own copy of the control flow drift the moment one is edited, and the drift is invisible until a change behaves differently on Codex than it did on Claude. The constraint the framework will not give up is behavioural compatibility across Claude, Codex, Cursor and DeepSeek; a hard-coded control flow forfeits it. This is not a review-only question — delivery routes and builds and lands, and future processes will carry their own state machines — so the decision has to be the base one, made once for any process.

## Decision

A process's orchestration is declared data the framework owns: its nodes, the edges between them, its loop bounds and its escalation thresholds are stated as content, beside the route table and the findings-and-verdict contract they already sit with. A runtime is a binding that executes the declared graph. It contributes platform mechanics only — how a model is called, how a service such as the Clef gate is reached, how state is persisted between passes — and never the topology and never the substance. The LangGraph runtime is one such binding; a session following the orchestration skills is another; both read the same declared machine, so neither can diverge from it.

Nothing a process decides is hard-coded in a runtime or a platform. What varies per platform is binding mechanics; what varies per project is installed plugins — a client's domain joins as a route fragment, a lens and a persona, merged into the declared graph rather than forking it. Code review is the first process expressed this way; delivery and every process after it take the same form, which is why this record is the base decision and not a review one. It extends ADR-017 from the agency's shape to the orchestration of any process.

The edge still open is the declaration format itself — the schema a graph is written in, and how a binding loads it — which the runtime work settles when it is no longer deferred. That the graph is declared data and the runtime only binds it is decided here; the shape of the declaration is the next record's context.

## Consequences

Portability stops being something each binding has to be trusted to preserve and becomes a property of construction: one declared machine, several bindings that execute it, behaviour that matches across platforms because there is a single source for it. The LangGraph runtime shrinks to a thin executor — less code, a smaller surface to get wrong — and a session-driven run and a runtime-driven run become the same process rather than two implementations that happen to agree today.

The cost is paid in the framework, and it is real. Control flow expressed as data is harder to write than control flow written as code in the runtime that runs it: a graph needs a schema, the schema has to be expressive enough for loops and thresholds and conditional fan-out, and a binding cannot take the shortcut of simply writing the `if`. The framework carries that weight so the platforms do not, and a binding tempted to hard-code one edge "just here" is the drift this record exists to forbid.

It forecloses per-runtime orchestration. A platform that wants a flow the declared graph does not express changes the declared graph, where every binding sees it, rather than its own copy. That is slower than a local edit, and that is the point: the slower path is the one that keeps the four platforms in step.

## Alternatives considered

- **The runtime hard-codes the coarse state machine, and only the substance — prompts, route table, contract — is injected.** Rejected: the coarse machine is still the process, and a process held in one runtime's code is reimplemented by the next platform's binding and drifts from it. It was the framing this record was opened to correct.
- **Each platform implements its own orchestration against a shared prose spec.** Rejected: a prose spec is read, not executed, and two readings of it are two processes, with no stage that catches the divergence until behaviour differs in production.
- **Keep the orchestration only as the skills a session follows, and let each runtime translate them.** Rejected: a translation is a second copy with no check that it still matches, and the skills are prose for a reader, not a machine a runtime executes directly. The declaration has to be data both a session and a runtime read.
- **Defer the question until the runtime is built.** Rejected: the runtime is where the hard-coding would happen, so the decision has to precede it; building first is how the control flow ends up in the runtime's code by default.
