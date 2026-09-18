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

## Open

- Whether `rules/` and `docs/` reach the agent through a generated index or through a hook, per platform
- How the install step places a plugin's skills under `.agents/skills` for DeepSeek: copy, symlink, or a generated pointer
