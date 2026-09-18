# Architecture

## The two models

The framework separates what it *is* from how it *travels*.

**The content model is the five artifact types**, inherited from the predecessor framework and unchanged. Each type has one job, and an authority hierarchy governs which may reference which.

| Type | Job | Authority |
|---|---|---|
| **rule** | An unbreakable guardrail. No exceptions. | Highest. Nothing may contradict a rule. |
| **doc** | A reference manual. Informs decisions. | Consulted by skills and agents. |
| **skill** | A repeatable procedure. Applies rules, consults docs. | Invoked by commands and agents. |
| **agent** | A specialist that orchestrates skills. | Invoked by commands and by people. |
| **command** | An entry point. | Invokes a skill or an agent — never a rule, never a doc. |

**The distribution model is the plugin.** A plugin is a directory of this repository, listed in `.claude-plugin/marketplace.json`, installed by name.

The two are independent on purpose. The content model is ours and it outlives any vendor. The distribution model is the platforms' and it changes when they change.

## Why plugins

Claude, Codex, Cursor and the rest each read a different layout. A plugin is the one packaging all of them already understand, so adapting to a new platform costs a manifest rather than a migration.

It also makes composition free. A consumer installs `ahrena-engineering-python` without inheriting .NET, mobile and SRE. There is no profile system to build — the marketplace is the catalog.

## Repository layout

```
ahrena-framework/
├── .claude-plugin/
│   └── marketplace.json          the catalogue: every plugin, by name
│
└── <plugin>/
    ├── .codex-plugin/plugin.json   manifest, points at the same content
    ├── .cursor-plugin/plugin.json  manifest, points at the same content
    ├── rules/                      *.md
    ├── docs/                       *.md
    ├── skills/<name>/              SKILL.md, references/, scripts/
    ├── agents/                     *.md
    ├── commands/                   *.md
    └── hooks/                      deterministic enforcement
```

**There is no transpilation.** Every platform reads the same `skills/` and `agents/` directories. Only the manifest differs, because the platforms already agree on the file format. No derived tree is generated, committed or kept in sync.

## The four platforms

Every plugin ships for all four at once. A plugin that supports three is incomplete.

| Platform | How it finds the plugin | What we ship |
|---|---|---|
| **Claude Code** | `.claude-plugin/marketplace.json` at the repository root; directories by convention inside the plugin | the marketplace entry |
| **Codex** | `.codex-plugin/plugin.json` inside the plugin | the manifest |
| **Cursor** | `.cursor-plugin/plugin.json` inside the plugin | the manifest |
| **DeepSeek** | directory discovery at `<projectRoot>/.agents/skills`, ranked by source; no manifest exists | the install-time mapping |

DeepSeek is the one that carries no manifest: its local provider discovers `<name>/SKILL.md` bundles and flat `<name>.md` files under `.agents/skills`, so the consumer's install step places or links the plugin's skills there.

Its documentation also states the constraint that settles our layout:

> Nested recursive `**/SKILL.md` discovery is not supported.

Skill directories are therefore flat under `skills/`, and skill names are kebab-case. That is not a preference — a nested layout is invisible to DeepSeek.

## Decisions

**The plugin boundary carries the taxonomy.** The predecessor addressed artifacts as `{clade}/{subclade}/{pilar}/{name}`. Platforms require `skills/`, `agents/` and `commands/` flat at the plugin root, so clade and subclade move to the plugin name and to artifact frontmatter. The authority hierarchy is unaffected: it is semantic, declared in `rules/pilars.md` and checked by a gate, never implied by directory depth.

**Granularity follows size.** A small clade is one plugin. A large one splits by subclade, because a consumer should not install eleven engineering subclades to get one. The split is decided when a clade is ported, not declared up front.

**Skills are named for the activity, in the gerund** — `creating-rules`, `executing-plans`. This matches the platform convention and reads correctly at the invocation site.

**Rules and docs are flat inside the plugin**, like everything else. No platform dictates their shape, and mixing flat and nested layouts inside one plugin buys nothing.

**Foundation is one plugin, not two.** The artifacts that create other artifacts consult the ones that define naming, paths and directives. Splitting them would create a cross-plugin dependency on the first day.

## Enforcement

A rule that nothing checks is a claim, not a guardrail. Where a rule is mechanically decidable it ships with a hook or a gate; where it is a judgment call it says so and does not pretend otherwise.

Artifacts reference each other through links that CI resolves. A reference to something that does not exist fails the build.

## How rules and docs reach the agent

No platform loads a `rules/` or `docs/` directory natively. They are ours, so we decide how they arrive — and they arrive differently, because they are different things.

**A doc is never injected.** It is a reference manual, consulted when a decision needs it. A skill or agent names its path and reads it at the moment of use. Injecting docs is how a framework arrives at tens of thousands of always-loaded tokens that are irrelevant to the task at hand.

**A rule arrives by one of two routes, decided by whether it is mechanically decidable.**

| The rule is | Route | Why |
|---|---|---|
| mechanically decidable | a hook in `hooks/` | A guardrail that runs beats a guardrail that is read. It costs no context and it cannot be overlooked. |
| a judgment call | the platform's instruction file, as one line plus a link | It needs a reader, so it needs to be in context — but only its statement, never its rationale. |

The install step writes the second route into whatever file the platform reads: `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex and DeepSeek, `.cursor/rules/*.mdc` for Cursor, whose `description`, `globs` and `alwaysApply` fields make the scoping native.

What it writes is an index, not the corpus: one line per rule, each linking its full text. A rule that cannot be stated in one line plus a link is carrying rationale that belongs in a doc.

This is the rule that keeps the injected set small, and it is measurable: the always-loaded footprint is one line per judgment-call rule, and every mechanical rule contributes zero.

## How the install reaches DeepSeek

DeepSeek discovers `<name>/SKILL.md` under `<projectRoot>/.agents/skills` and carries no manifest, so the install step places them.

**Symlink by default.** `.agents/skills/<name>` points at the plugin's own `skills/<name>`. It costs no bytes, it cannot drift, and DeepSeek's watcher follows additions and removals at that root.

**Copy on Windows**, where symlinks need `core.symlinks=true` and developer mode, neither of which a framework may assume. A copied tree can go stale, so the copy path records the source and a freshness gate fails when the two diverge. The symlink path needs no such gate, which is the reason it is the default rather than a preference.
