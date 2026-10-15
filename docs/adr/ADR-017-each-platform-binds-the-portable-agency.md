# ADR-017: Each platform binds the portable agency spec

- **Status:** accepted
- **Date:** 2026-10-15
- **Issue:** #192

## Context

The agency's orchestration is already shipped and it is runtime-agnostic. Athena
is the tech-lead that plans an issue, routes each concern, delegates each layer
to Iris, Apollo or Clio, runs the develop→Argos loop at most three rounds before
each stacked pull request, and never implements. That is a manager/worker shape,
and it is written as portable artifacts — one agent and two skills — that say
nothing about which runtime executes them.

A spec that no platform runs is a document. Two gaps stand between the spec and a
platform actually using it. The first is mechanical: each platform discovers and
spawns agents its own way, so the one manager/worker shape needs a per-platform
binding. The second is behavioural, and it is the harder one: a platform that
*can* run Athena will not do so unless something makes build work enter through
her. An agent sitting in a plugin is available, not used. Left to default, a
request to build a feature is answered by whatever agent the prompt happened to
address, and the orchestration is bypassed on exactly the changes it exists for.

Codex adds a specific constraint the binding has to survive. Its custom agents
cap recursion with `agents.max_depth`, default 1. Athena spawning a build agent
is already depth 1, so a build agent that spawned its own stage subagent would be
depth 2 and exceed the default — a binding that assumed arbitrary nesting would
fail on a stock Codex install.

## Decision

The manager/worker shape is the portable spec, and each platform binds it. The
binding is mechanical; the lever that makes the platform *always* use it is a
single entry directive written into the platform's always-loaded instruction
file.

**The spec is portable; the binding is per-platform.** `ARCHITECTURE.md` already
says a plugin adapts to a platform through a manifest, not a migration, and the
same holds for orchestration. The spec stays one agent and two skills. Each
platform gets a thin binding that maps that shape onto its own agent mechanism,
documented in `engineering/delivery/docs/platform-bindings.md`.

- **Claude Code** binds it as the Athena agent, plus an optional Workflow script
  that encodes her loop as a deterministic fan-out. The Workflow is opt-in and
  spawns subagents; the agent alone is the default binding.
- **Codex** binds it as custom subagents (GA ~March 2026): a manager agent that
  plans, delegates and integrates — Athena — and worker agents it spawns. Custom
  agents are TOML under `~/.codex/agents/` or `.codex/agents/`, spawned explicitly
  or triggered from `AGENTS.md`, capped by `agents.max_threads` (default 6) and
  `agents.max_depth` (default 1). The binding keeps the manager one level above
  the workers — Athena spawns the build agents directly and the build agents do
  not sub-spawn — so it runs inside `max_depth=1` with no config change. A project
  that wants build agents to fan out further raises `agents.max_depth` to 2; the
  binding names that as the one setting to change rather than assuming it.
- **LangGraph** (LangChain) maps the same shape to a supervisor with cycles and a
  human-in-the-loop, but it is the runtime (`ahrena-agents`), not a framework
  artifact. It is documented as the out-of-scope runtime binding and no LangGraph
  code is shipped here.

**The "always uses it" lever is the entry directive.** `ARCHITECTURE.md` already
routes a judgment-call rule into the platform's always-loaded file as one line
plus a link. The directive uses that same channel for one behavioural instruction:
build work enters through the `athena` agent, who plans, routes and delegates to
the agency, and is not implemented directly. It goes into `CLAUDE.md` for Claude
Code and `AGENTS.md` for Codex. Being always-loaded is the whole point — it is the
one place that reaches every request before an agent is chosen.

**The install procedure is ensure-or-report, mirroring the graph doctor.** A
skill (`installing-the-agency`) and its command (`install-agency`) ensure the
directive is present or report precisely what is missing, writing it between
clear markers so it never clobbers surrounding content, with a `--check` mode that
reports without writing. The default binding is the local harness with API
inference; a local-model path (Ollama or vLLM) is a one-line documented extension
point, not implemented here.

## Consequences

The spec earns a second and third consumer without changing, which is the test an
abstraction has to pass: Athena and her skills are written once and bound three
ways. A fourth platform costs a binding section and an install branch, not a
rewrite of the orchestration.

The directive makes the agency the default path for build work on both shipped
platforms, and it costs one always-loaded line, consistent with the footprint
`ARCHITECTURE.md` bounds. A request to build a feature now enters through Athena
unless a person deliberately steps around her.

The Codex depth cap is handled by flattening rather than by requiring a config
change, so the binding works on a stock install. The cost is that a Codex build
agent does its layer's work in its own thread instead of spawning stage
subagents; a project that wants the deeper tree opts into `max_depth=2`.

The Workflow binding is a reference, not CI-run code. It illustrates Athena's loop
in the Workflow API and is there to be read and adapted, so it carries no test and
gates nothing.

## Alternatives considered

- **One binding, ported per platform.** Rejected. Collapsing the spec into each
  platform's native form would fork the orchestration three ways and drift the
  moment one platform changed. Keeping the spec portable and the binding thin is
  what lets a fix to the loop land once.
- **A hook that forces routing through Athena.** Rejected. Whether a request is
  build work that should enter the agency is a judgment, not a decidable
  condition, and `ARCHITECTURE.md` sends judgment-call rules to the instruction
  file, not to a hook. A hook here would either fire on everything or need the
  judgment it cannot make.
- **Ship the LangGraph binding.** Rejected as out of scope. LangGraph is the
  runtime, and this layer is framework artifacts only. It is documented so the
  mapping is on record, but the code lives in `ahrena-agents`.
- **Require `agents.max_depth=2` on Codex.** Rejected as the default. A binding
  that needs a non-default config to run at all is a binding that fails on a fresh
  install. Flattening to one level runs everywhere, and the deeper tree is the
  opt-in, not the baseline.
