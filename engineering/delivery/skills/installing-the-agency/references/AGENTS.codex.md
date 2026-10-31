# The Codex binding — AGENTS.md directive and subagent note

A reference for the `installing-the-agency` skill. It holds the entry directive
text the skill writes into a Codex repository's `AGENTS.md`, and a short note on
how the portable personas map onto Codex custom subagents and how the caps apply.
This is a template to adapt, not a file to copy wholesale.

On Codex the script is the skill's own `scripts/install.py`, run with
`--platform codex`. That run writes only `AGENTS.md`: the plugin set in
`.claude/settings.json` is Claude Code's, and Codex does not read it.

## The entry directive

The skill writes this between its markers into `AGENTS.md`. Everything outside the
markers is the repository's own and is never touched.

```markdown
<!-- ahrena:agency:start -->
## Build work enters through the agency

Build work enters through the `athena` agent. She plans the issue, routes the
concern, and delegates each layer to `iris` (frontend), `apollo` (backend) or
`clio` (data), running the develop→Argos loop (at most three rounds) before each
stacked pull request. Do not implement build work directly — delegate to the
agency. Athena orchestrates; she does not write production code, pass a review
verdict, or apply a fix.
<!-- ahrena:agency:end -->
```

The directive is the whole always-loaded cost of the binding: one short block
that reaches every request before an agent is chosen. It names the agents and the
loop so the reader routes correctly, and nothing else — the rationale lives in the
delivery docs, not in the always-loaded file.

## Mapping a persona to a Codex custom agent

A Codex custom agent is a TOML file, personal under `~/.codex/agents/` or
per-project under `.codex/agents/`. A framework persona maps onto one directly:

- the persona's `name` and `role` become the agent's identity,
- the persona's `description` becomes the agent's selection text,
- the persona's body becomes the agent's system prompt.

Athena is the manager agent — the one that plans, delegates and integrates and
never writes code. Iris, Apollo and Clio are the worker agents she spawns. The
portable markdown persona is the source of truth; the TOML is the binding Codex
reads, regenerated from the persona rather than hand-edited.

```toml
# .codex/agents/athena.toml  (illustrative)
name = "athena"
description = "Tech-lead: plans an issue, routes each concern, delegates layers, runs the Argos loop, stacks PRs. Never implements."
# system prompt is the body of engineering/delivery/agents/athena.md
```

## The caps, and the depth gotcha

Codex bounds its subagents with two settings in its own configuration:

- `agents.max_threads` — concurrent subagents, default 6.
- `agents.max_depth` — recursion depth, default 1.

The depth cap is the one to design around. Athena spawning a build agent is
already depth 1. A build agent that spawned its own stage subagent would be depth
2 and exceed the default, so the binding **flattens**: Athena spawns the build
agents directly, and the build agents do their layer's work in their own thread
rather than sub-spawning. That runs on a stock Codex install with no config
change.

A project that wants build agents to fan out into their own stage subagents
raises the cap to `max_depth = 2`. That is the owner's deliberate opt-in, named
here so it is a choice and not a silent dependency; the skill reports the cap but
does not edit Codex's config.
