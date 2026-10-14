---
name: querying-the-code-graph
description: Use at edit time and at planning time to orient in a codebase you did not write — to locate yourself and find which component owns a path, to find what a file depends on and what depends on it, to trace a path between two symbols, or to read the macro overview of the whole system. Keeps an always-fresh, two-tier graph (a light per-language index and a Graphify macro tier) and degrades gracefully when a tier's tool is absent.
type: skill
clade: engineering
subclade: architecture
references:
  - docs/code-graph.md
  - docs/component-map.md
  - skills/provisioning-the-code-graph/SKILL.md
---

# Querying the code graph

This is the procedure a build agent runs to orient itself in a codebase: to
locate itself, follow dependency paths, and read the shape of the whole before
it changes one corner. [`docs/code-graph.md`](../../docs/code-graph.md) defines
the graph this queries — the gitignored cache, the two tiers, and how it stays
fresh — and this names the interface over it. Run it whenever a question about
*where*, *what depends on what*, or *the shape of the whole* comes up, not once
per session.

The graph is a cache, so step 1 is always to make it fresh. The script is
self-healing: it regenerates a stale cache and leaves a current one alone, and
it degrades to whatever tiers the machine can build. The full command surface,
output shapes and exit codes are in [`references/commands.md`](references/commands.md);
the generator and query implementation is [`scripts/graph.py`](scripts/graph.py).

## 1. Ensure the cache is fresh

Before any query, bring the cache up to the commit and working tree in front of
you. The generator computes the freshness key and regenerates only when it is
stale, so this is cheap on a current cache and correct on a stale one.

```sh
python3 scripts/graph.py refresh
```

To know the state without paying for a rebuild — whether the cache is current,
and which tiers are available on this machine — run `--check` instead:

```sh
python3 scripts/graph.py --check
```

`--check` reports freshness and tier availability and regenerates nothing. It is
the step for deciding whether a rebuild is worth its cost before you ask for one.

## 2. Locate yourself with `locate`

To answer *where am I* and *which component owns this path*, pass a file or a
symbol. `locate` returns the module, the symbols it declares, and — when the
project's component map is present — the component whose declared paths contain
it.

```sh
python3 scripts/graph.py locate <path-or-symbol>
```

When the component the map claims differs from where the graph shows the path's
dependencies going, that is drift; [`docs/code-graph.md`](../../docs/code-graph.md)
and [`docs/component-map.md`](../../docs/component-map.md) say how the two
reconcile. Surface the gap rather than resolving it on your own authority.

## 3. Find dependencies with `deps`

To answer *what do I depend on* and *what depends on me*, pass a file or module.
`deps` returns the internal modules it imports and, in reverse, the modules that
import it — the blast radius of a change before you make it.

```sh
python3 scripts/graph.py deps <path-or-module>
```

The light tier answers this from the import index, so it is cheap enough to run
on every edit. Reach for it before changing a shared module, not after.

## 4. Trace a path with `path`

To find how two files or symbols are connected, pass both. `path` returns the
shortest dependency chain between them through the import graph, or reports that
none exists.

```sh
python3 scripts/graph.py path <from> <to>
```

An empty result is information: two things with no path between them are
decoupled, which is what you want to confirm before asserting they are.

## 5. Read the overview with `explain`

To read the macro shape — god nodes, communities, and a plain-language account
of a node — use `explain`, which draws on the Graphify macro tier. Because that
tier is optional, ensure it first through the doctor
([`skills/provisioning-the-code-graph`](../provisioning-the-code-graph/SKILL.md)),
which builds it when Graphify is present and reports exactly what it needs when
it is not.

```sh
python3 scripts/graph.py explain <node>
```

This is the planning-time question, paid once and amortised across a plan. When
the macro tier is unavailable, `explain` does not fail — it names the doctor and
`/graph-doctor` as the way to provision it, and the guaranteed light floor keeps
answering `locate`/`deps`/`path` meanwhile; `references/commands.md` gives the
exact output in that case and when to fall back to reading the component map.

## When this skill does not apply

**A greenfield repository with no code yet.** There is nothing to index, so the
graph has nothing to say. Orientation in an empty tree comes from the project's
intended structure, which is the component map's business and
[`skills/reading-the-component-map`](../reading-the-component-map/SKILL.md), not
this skill's.

**A language the light indexer does not cover.** The reference indexer is
Python; another language with no indexer is recorded as present but unindexed,
and `locate`/`deps`/`path` cannot answer over it. Degrade to the Graphify macro
tier, which is language-agnostic, or to reading the component map for the
declared structure.

**Deciding whether the declared structure is right.** This skill makes drift
between the map and the code visible. Whether the map is wrong or the code is
wrong is a judgment about the project, made in the project's vocabulary, and it
belongs to the architecture rules and the owner, not to a graph query.

**Changing the component map.** Reconciling drift by editing the map is a change
to the project the owner consents to, not a side effect of a query. This skill
reads; it does not rewrite the project's own declared structure.

<!--
Directory layout:

skills/querying-the-code-graph/
├── SKILL.md
├── references/    the command surface, outputs and exit codes a step opens
└── scripts/       the generator and query implementation a step runs

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
