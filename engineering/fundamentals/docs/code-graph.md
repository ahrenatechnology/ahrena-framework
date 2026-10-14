---
id: code-graph
type: doc
clade: engineering
subclade: architecture
title: The code graph
summary: The always-fresh, two-tier graph a build agent consults to locate itself, follow paths and find dependencies — a gitignored cache keyed by commit, a heavy Graphify macro tier and a light per-language index, how a session refreshes it, how it degrades when a tier's tool is absent, and how it reconciles with the component map.
references:
  - docs/component-map.md
---

# The code graph

This defines the code graph: the structure an agent reads to answer *where am
I*, *what depends on what*, and *what is the shape of the whole* before it
changes one corner of a codebase it did not write. It is the reference behind
the procedure in [`skills/querying-the-code-graph`](../skills/querying-the-code-graph/SKILL.md),
which names the agent's interface and the script that maintains it. Where the
[`docs/component-map.md`](component-map.md) is the structure a project
*declares*, this graph is the structure that *is*, and the gap between them is
drift an agent can see.

The graph is a **cache, not a committed artifact.** `ADR-016` records why: a
committed derivation of the code drifts against the code the moment the next
commit lands, and `ARCHITECTURE.md` forbids a derived tree that is "generated,
committed or kept in sync." So the graph is regenerated at the point of use and
never versioned.

## The cache layout

The graph lives under one gitignored root, keyed by the commit it describes.

```
.ahrena/
  graph/
    <sha>/          one directory per commit the graph was built for
      key           the freshness key the build was keyed to
      index.json    the light per-language index
      graphify/     the macro tier's output, when it was built
```

`.ahrena/` is in the repository's root `.gitignore`, so nothing here reaches
version control and nothing here can drift against the source. The directory is
named for the commit's forty-character `HEAD` sha. The `key` file holds the full
freshness key, which is the sha on a clean tree and the sha with a short digest
of the dirty working tree appended when there are uncommitted changes — a build
of a dirty tree is still usable, and the appended digest is what lets a session
tell a stale build from a current one.

## The two tiers

The graph answers two questions whose costs are opposites, so it is built in two
tiers rather than one.

**The macro tier is a Graphify build.** It carries god nodes, community
detection and the `query`, `path` and `explain` tools over the whole corpus. It
is the comprehension of the system an agent reaches for at planning and routing
time, where the cost of building it is paid once and amortised across a plan. It
is consulted rarely, because building and reading it is expensive, and that is
the right trade for a question asked a few times per change.

**The light tier is a per-language import and symbol index.** It records, for
each source file, the module it is, the symbols it declares, and the modules it
imports — enough to answer `locate` and `deps` in the time it takes to read a
line. It is consulted constantly, at edit time, because it is cheap. It is
tree-sitter or a language server where one is available, and a standard-library
scan where one is not.

Collapsing the two into one tier makes the cheap, constant question pay the
expensive, rare question's price on every call, which is the cost profile a
build agent can least afford.

The two tiers carry different guarantees, and the split is deliberate. The light
tier is the **always-available floor**: it is standard-library only, needs zero
install, and `locate`, `deps` and `path` answer over Python on any bare
checkout — nothing has to be provisioned for it to work. The macro tier is
**optional enrichment**: Graphify is the owner's personal skill rather than a
dependency this framework installs, so the macro tier is provisioned at work
time by the doctor (`scripts/graph.py doctor`, run through
[`skills/provisioning-the-code-graph`](../skills/provisioning-the-code-graph/SKILL.md)
or `/graph-doctor`), which readies it where Graphify is present and otherwise
reports exactly how to enable it while the floor keeps answering. `ADR-015`
holds the architecture decision behind this; the doctor only provisions within
its shape.

## How a session refreshes the graph

Freshness is self-healing: the capability maintains it, rather than a gate
deciding it. `ADR-016` explains why there is no CI check — a gate over a
gitignored cache reads nothing and reports it absent forever.

A session refreshes by comparing the world in front of it to the cache's key.
It computes the current freshness key from `HEAD` and a marker of the dirty
working tree, and reads the `key` file in `.ahrena/graph/<sha>/`. When the two
match, the cache is current and is used as-is. When they differ, or the
directory is absent, the cache is stale and is regenerated before it is queried.
The regeneration is incremental where it can be: the light index re-scans the
files the change touched rather than the whole tree, and the macro tier rebuilds
through Graphify's own update path. The generator's `--check` mode reports this
staleness without rebuilding, for a step that wants to know the state before it
decides to pay for a rebuild.

## Graceful degradation

No tier is required for the graph to answer. The capability runs on a bare
checkout, which is the only state a consumer is guaranteed to have.

**When Graphify is absent**, the generator builds and answers from the light
index alone, and reports the macro tier unavailable. `locate` and `deps` still
work; `explain` says the overview cannot be built here rather than failing.

**When tree-sitter is absent**, the light tier falls back to a standard-library
scan of imports and symbols. For Python this is a full, working indexer built on
the `ast` module; for other languages it is an extension point, and a file in a
language no indexer covers is recorded as present but unindexed rather than
dropped. An agent working in an uncovered language degrades to the macro tier or
to reading the component map, as the querying skill's boundary section says.

## Reconciling with the component map

The graph and the [`docs/component-map.md`](component-map.md) describe the same
system from two directions, and the discipline is to read them together. The map
is what a project *declares*: which component owns which paths, in the project's
own vocabulary. The graph is what the code *does*: which module actually imports
which. The two agree in a healthy codebase and diverge in a drifting one.

The divergence worth naming is a component that the map claims owns a set of
paths, where the graph shows those paths depending on a component the map places
elsewhere. That is drift — the declared structure and the real one have parted —
and surfacing it is one of the things the graph is for. The graph does not
resolve the drift, because which side is wrong is a judgment about the project
that belongs to the project; it makes the drift visible so a person or an agent
can decide.

## Where this stops

**It is a cache, not a source of truth.** The graph describes the code at a
commit; the code is the truth. A query answered from a stale cache is answered
about a commit that is no longer checked out, which is why freshness is checked
before a query and not assumed.

**It does not decide who consults it.** This document defines the graph and how
it stays fresh. Which agent reads it, at which step of which build, is the
subject of the wiring layer (#183) and the skills it touches, not of this
schema.

**It does not adjudicate drift.** The graph makes a divergence between the
declared and the actual structure visible. Whether the map is wrong or the code
is wrong is a decision about the project, made by a person or a build agent in
the project's vocabulary, and the graph holds no opinion on it.

**It governs the graph, not the languages in it.** The reference indexer is
Python. The shape of an indexer for another language, and what counts as a
symbol or an import there, is the business of whoever extends the light tier,
and this document fixes only the index's contract, not its per-language
contents.
