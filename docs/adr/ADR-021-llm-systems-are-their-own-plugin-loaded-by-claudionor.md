# ADR-021: LLM-system engineering is its own plugin, loaded by Claudionor

- **Status:** accepted
- **Date:** 2026-11-15
- **Issue:** #350, #347

## Context

On 15/11/2026 the framework's owner decided that Claudionor, the artifact author
in `ahrena-foundation`, also becomes the specialist in AI agents and LLM systems,
rather than a new agent being added (#347). That work needs its own rules, docs
and skills: the shape ladder from a single model call to several agents, the
choice of framework, tool definitions, loop bounds, memory, evaluation, tracing
and cost. They have to live somewhere, and Claudionor has to load them.

Two facts constrain where.

**`ahrena-foundation` is installed by everyone and depends on nothing.** The
marketplace describes it as the plugin every other plugin depends on. On
15/11/2026 the gate's plugin graph (`foundation/rules/pilars.md` condition 8) had
no edge out of `ahrena-foundation` and two into it, from
`ahrena-engineering-quality` and `ahrena-engineering-code-review`. Each
judgment-call rule a plugin ships costs one always-loaded line in every project
that installs it (`ARCHITECTURE.md`, "How rules and docs reach the agent").

**The graph is acyclic, and the security plugin already sits downstream of
foundation.** `ahrena-engineering-security` references
`ahrena-engineering-quality`, which references `ahrena-foundation`. Janus's
`reviewing-model-use` is the discipline that already covers prompt injection and
tool authority, and the LLM-system work leans on it. Any declared reference from
foundation, or from anything foundation references, to the security plugin closes
a cycle the gate fails.

## Decision

**The rules, docs and skills for designing, building, reviewing and debugging LLM
systems live in a new plugin, `ahrena-engineering-llm-systems`, at
`engineering/llm-systems/`.** It has no agent of its own. Claudionor lists its
skills in `skills:` and its rules and docs in `references:`, as plugin-qualified
references (`ahrena-engineering-llm-systems:skills/<name>/SKILL.md`). This makes
`ahrena-foundation` depend on one plugin for the first time.

**The new plugin declares references only to itself and to
`ahrena-engineering-fundamentals`**, which references nothing. That keeps every
path out of it short of `ahrena-foundation`, so the new edge cannot close a cycle.

**Janus's `reviewing-model-use` is reached by name, not by reference.** A skill
in the new plugin, and Claudionor's body, name
`ahrena-engineering-security:reviewing-model-use` in prose and invoke it with the
Skill tool at the step that needs it, and a body link to its file is allowed,
since `pilars.md` does not count a body link as a reference. Neither lists it in
`references:` or `skills:`. A project without the security plugin installed gets
a step that says the skill is missing rather than a silent gap.

**The installer treats the new plugin as part of foundation's install.**
`installing-the-agency` lists `ahrena-engineering-llm-systems` among its core
plugins, beside `ahrena-foundation`, because Claudionor's `skills:` preload names
it.

## Consequences

A project that does not build LLM systems still installs the plugin with
foundation, but reads none of it: its skills load only when Claudionor runs, and
its docs only when a skill names them. The always-loaded cost is the plugin's
judgment-call rules, one line each.

`ahrena-foundation` is no longer a leaf. The marketplace and README stop saying it
depends on nothing; the sentence that every other plugin depends on it stays
true. Whoever next wants foundation to load another plugin's content now has a
precedent, and this record is where the constraint on it is written: the target
must not reach foundation.

The LLM-system content cannot declare a reference to the quality or security
plugins, so a rule there cannot cite `reviewing-prompts` or `reviewing-model-use`
as a load edge. It names them in prose and links them in the body, as rules
already do when they cite another rule.

A consumer who installs `ahrena-foundation` alone, outside the installer, has a
Claudionor whose LLM skills do not resolve. The gate validates the marketplace,
not an installation (`pilars.md`, "Where this stops"), so nothing here detects
that.

## Alternatives considered

- **Put the content inside `ahrena-foundation`.** Rejected. It keeps foundation a
  leaf, but every project that installs the framework, which is every project,
  carries the LLM-system rules' always-loaded lines, and foundation stops being
  the plugin about artifacts. It does not avoid the cycle either: foundation still
  could not reference the security plugin.
- **A new plugin with its own specialist agent.** Rejected by the owner's decision
  of 15/11/2026 recorded in #347: Claudionor is the specialist, because writing
  the instructions an agent runs on and building the agent are the same craft.
- **Move Claudionor out of foundation into the new plugin.** Rejected. Claudionor
  is the agent that creates foundation's own artifacts; moving it out would make
  foundation depend on an engineering plugin for its own authoring, a heavier edge
  than this one.
- **Let the new plugin reference the security plugin, and break the cycle by
  removing `ahrena-engineering-quality`'s reference to foundation.** Rejected.
  That reference is the review skills reaching the artifact rules they apply; it
  is older and has more reasons to exist than the convenience of a declared edge
  where a named invocation already works.
