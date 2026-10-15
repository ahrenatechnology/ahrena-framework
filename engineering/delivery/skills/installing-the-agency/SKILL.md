---
name: installing-the-agency
description: Make the agency the default path for build work on this platform. Use when setting up a repository so build work enters through Athena — ensuring the agency plugins are available, then writing or refreshing the entry directive into the platform's always-loaded instruction file (CLAUDE.md for Claude Code, AGENTS.md for Codex), idempotently and without clobbering. Ensure-or-report, never overwrite; a --check mode reports whether the directive is present and current.
type: skill
clade: engineering
subclade: delivery
references:
  - docs/platform-bindings.md
  - skills/orchestrating-delivery/SKILL.md
---

# Installing the agency

This is the procedure that makes the agency *always used* on a platform, or
reports exactly what is missing — the install layer for the orchestration spec a
person runs through `/install-agency`. The agency is portable and already shipped;
this skill binds it to the platform in front of it and routes build work through
it. It follows the graph doctor's shape: ensure-or-report, idempotent, standard
library, a `--check` that writes nothing. [`docs/platform-bindings.md`](../../docs/platform-bindings.md)
defines the per-platform bindings this skill applies, and the orchestration it
installs is [`skills/orchestrating-delivery/SKILL.md`](../orchestrating-delivery/SKILL.md).

## 1. Detect the platform and confirm the plugins are available

Decide which platform this repository runs on, by the always-loaded file present:
`CLAUDE.md` is Claude Code, `AGENTS.md` is Codex; when neither is present the
install defaults to creating `CLAUDE.md`, and `--platform codex` steers a Codex
repository that has not yet written its `AGENTS.md`. Confirm the agency plugins —
delivery and the build clades it delegates to — are installed and discoverable;
without them the directive would point at agents that do not exist. When a plugin
is missing, report it rather than installing it, the way the graph doctor reports
Graphify rather than installing a personal skill.

## 2. Check the directive before writing it

Run the install script in `--check` mode. It reports whether the entry directive
is present and current between its markers, and writes nothing:

```sh
python3 engineering/delivery/skills/installing-the-agency/scripts/install.py --check
```

Read the result: present-and-current means there is nothing to do; absent or
stale means step 3 writes it. `--platform` overrides the auto-detection when the
repository carries both files.

## 3. Write or refresh the entry directive, idempotently

Write the directive with the same `scripts/install.py`, without `--check`. It
writes the directive between clear markers (`<!-- ahrena:agency:start -->` …
`<!-- ahrena:agency:end -->`) into the detected file, replacing only what sits
between them and never touching the surrounding content:

```sh
python3 engineering/delivery/skills/installing-the-agency/scripts/install.py
```

The directive states that build work enters through the `athena` agent, who plans
the issue, routes the concern, and delegates each layer to iris, apollo or clio
while running the develop→Argos loop before each stacked pull request — and that
build work is not implemented directly. Running it twice changes nothing the
second time, which is what makes it safe to re-run on every setup.

## 4. For Codex, apply the subagent binding and report max_depth

On Codex, the persona maps to a custom agent and the directive goes into
`AGENTS.md`. Use the [`references/AGENTS.codex.md`](references/AGENTS.codex.md)
template for the directive text and the note on where the TOML agents live and how
the caps apply. Report the `agents.max_depth` cap rather than editing Codex's
config: the default is 1, the binding flattens so Athena spawns build agents
directly and they do not sub-spawn, and a deeper tree is the owner's opt-in to
`max_depth=2`. The script surfaces this guidance under `--platform codex`.

On Claude Code, the optional Workflow binding encodes Athena's loop as a
deterministic fan-out; [`references/athena.workflow.js`](references/athena.workflow.js)
is the illustrative script to adapt when a project wants the loop run that way.

## 5. Hand back what was ensured or what is missing

Return which platform was detected, whether the directive was already current or
was written, any plugin the agency needs that is not installed, and — on Codex —
the `max_depth` guidance. A missing plugin or a config the owner must set is
carried back as a report, not worked around, exactly as the graph doctor carries
its `to enable` lines.

## When this skill does not apply

**The directive is already present and current.** When `--check` reports it in
place, there is nothing to ensure; re-writing an unchanged directive is churn, and
the idempotent write already makes a re-run harmless.

**Running the orchestration.** This skill installs the agency and routes build
work to it; turning an issue into a landed stack is
[`skills/orchestrating-delivery/SKILL.md`](../orchestrating-delivery/SKILL.md),
which Athena runs once the agency is installed.

**Changing the binding or the spec.** How a platform binds the spec is
[`docs/platform-bindings.md`](../../docs/platform-bindings.md), and the spec
itself is the orchestration artifacts. This skill applies a binding; it does not
author one or re-specify Athena's loop.

**Setting Codex's config or wiring a runtime.** Changing `agents.max_depth`,
building the LangGraph runtime, or enabling a local-model path are the owner's
acts and the `ahrena-agents` repository's code. This skill reports them; it does
not perform them.

<!--
Directory layout:

skills/installing-the-agency/
├── SKILL.md
├── references/
│   ├── athena.workflow.js   the Claude Code Workflow binding, illustrative
│   └── AGENTS.codex.md      the Codex directive template and subagent note
└── scripts/
    └── install.py           ensure-or-report the directive, --check, stdlib

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
