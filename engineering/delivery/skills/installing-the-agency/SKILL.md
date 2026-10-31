---
name: installing-the-agency
description: Install the agency in a repository. Use when setting it up so build work enters through Athena — enables the agency plugins in .claude/settings.json and writes the entry directive into CLAUDE.md or AGENTS.md, idempotently and without clobbering; --check reports what is missing.
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

## 1. Detect the platform

Decide which platform this repository runs on, by the always-loaded file present:
`CLAUDE.md` is Claude Code, `AGENTS.md` is Codex; when neither is present the
install defaults to creating `CLAUDE.md`, and `--platform codex` steers a Codex
repository that has not yet written its `AGENTS.md`. Whether the agency plugins
are available is not left to the model: the script reports each one, in step 2.

The script, `scripts/install.py`, is resolved from the plugin's own root, never
from a path that exists only in the framework's checkout. On Claude Code that is
`${CLAUDE_PLUGIN_ROOT}`; on Codex it is the skill's own `scripts/` directory.

## 2. Check what is in place

Run the script in `--check` mode. It writes nothing. It reports the directive's
state in each instruction file and each agency plugin as enabled, missing or
disabled, counting the project's `.claude/settings.json` and
`.claude/settings.local.json` and the user's `settings.json`:

```sh
# Claude Code
python3 "${CLAUDE_PLUGIN_ROOT}/skills/installing-the-agency/scripts/install.py" --check
# Codex, from the skill's own directory
python3 scripts/install.py --check --platform codex
```

Exit 0 means everything is in place and there is nothing to do; exit 1 means
step 3 has work. `--platform` overrides the detection when the repository
carries both files.

## 3. Install, idempotently

Run the same script without `--check`. It does two things:

- **Merges the agency into `.claude/settings.json`.** The set is declared in
  [`references/agency.json`](references/agency.json): the `ahrena` marketplace
  and the eight core plugins, plus the language plugin for each marker file at
  the repository root (`pyproject.toml`, `tsconfig.json`, `go.mod`,
  `Cargo.toml`), or the ones `--language python|typescript|go|rust` names. The
  merge only adds. It keeps every other key and its order, never flips a plugin
  the user disabled, and never overwrites an `ahrena` marketplace entry that
  exists; it reports a disabled plugin and a marketplace that differs. It is not
  `claude plugin marketplace add`, which rewrites an entry the user already has.
- **Writes the directive** between `<!-- ahrena:agency:start -->` and
  `<!-- ahrena:agency:end -->` in the instruction file, replacing only what sits
  between them. `--platform codex` skips settings.json, which Codex does not read.

```sh
# Claude Code
python3 "${CLAUDE_PLUGIN_ROOT}/skills/installing-the-agency/scripts/install.py"
# Codex, from the skill's own directory
python3 scripts/install.py --platform codex
```

The directive states that build work enters through the `athena` agent, who plans
the issue, routes the concern, and delegates each layer to iris, apollo or clio
while running the develop→Argos loop before each stacked pull request — and that
build work is not implemented directly. A malformed settings file is an error,
exit 2, and the file is left as it was. Running the script twice changes nothing
the second time and says so, which is what makes it safe to re-run on every setup.

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

Return which platform was detected, which plugins were enabled and which were
already, any plugin the owner disabled, a marketplace entry that differs from the
declared one, whether the directive was already current or was written, and — on
Codex — the `max_depth` guidance. A disabled plugin or a config the owner must set
is carried back as a report, not worked around, exactly as the graph doctor
carries its `to enable` lines. The script's own tests are
[`scripts/test-install.py`](scripts/test-install.py).

## When this skill does not apply

**Everything is already in place.** When `--check` exits 0, there is nothing to
ensure; re-running is harmless, and it changes nothing.

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
│   ├── agency.json          the declared set: marketplace, plugins, language map
│   ├── athena.workflow.js   the Claude Code Workflow binding, illustrative
│   └── AGENTS.codex.md      the Codex directive template and subagent note
└── scripts/
    ├── install.py           merge settings.json, write the directive, --check, stdlib
    └── test-install.py      its tests

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
