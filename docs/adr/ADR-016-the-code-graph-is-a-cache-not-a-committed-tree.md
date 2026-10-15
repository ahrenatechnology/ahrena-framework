# ADR-016: The code graph is a cache, not a committed tree

- **Status:** accepted
- **Date:** 2026-10-14
- **Issue:** #182

## Context

The build agents — Iris, Apollo, Clio and Athena — keep asking the same three
questions of a codebase they did not write. Where am I, and which component owns
this path? What does this file depend on, and what depends on it? What is the
shape of the whole thing before I touch one corner of it? Today each agent
answers by reading files until it has seen enough, which is slow at edit time
and incomplete at planning time, and the two failures want opposite remedies.
The edit-time question is cheap and constant: it wants a lookup. The
planning-time question is expensive and rare: it wants comprehension.

A graph answers both, and the obvious thing to do with a graph is to build it
once and commit it. `ARCHITECTURE.md` forbids exactly that: "No derived tree is
generated, committed or kept in sync." A graph of the code is a derivation of
the code, and a committed derivation drifts the moment the next commit lands —
whoever forgot to regenerate it has shipped a map of a territory that no longer
exists, and an agent that trusts the map is worse off than one that reads the
files. The prohibition is the whole reason this is a decision and not a script.

The graph also has to survive a consumer who has none of the heavy tooling
installed. Graphify is the owner's own skill and tree-sitter is a dependency a
framework may not assume, so a capability that only works when both are present
works almost nowhere.

## Decision

The code graph is a cache regenerated at the point of use, in two tiers, and it
is consulted by a skill rather than enforced by a gate.

**Cached, not committed.** The graph lives in `.ahrena/graph/<sha>/`, keyed by
the commit it describes, and `.ahrena/` is gitignored. Nothing derived enters
version control, so nothing derived can drift against the source; the cache is
rebuilt when the source it was keyed to is no longer the source in front of the
agent. This is the no-derived-tree principle honoured rather than worked around:
the tree exists, but as a cache a session owns, not as a committed artifact a
reviewer has to keep in sync.

**Two tiers, because the two questions are not one question.** The macro tier is
a Graphify build — god nodes, community detection, and the `query`, `path` and
`explain` tools over the whole corpus — consulted rarely, at planning and
routing time, where the cost of building a comprehension of the system is paid
once and amortised across a plan. The light tier is a per-language import and
symbol index, tree-sitter where it is available and a standard-library scan
where it is not, consulted constantly, at edit time, where `locate` and `deps`
have to return in the time it takes to read a line. Collapsing them into one
tier makes the cheap question pay the expensive question's price on every call.

**Consultation is a skill step, not a rule, and freshness is self-healing.**
Whether an agent consults the graph is not a rule, because consulting it or not
yields *different* work rather than *defective* work — it fails the test in
`foundation/docs/artifact-model.md` that a rule's violation leaves the result
defective. So a skill names the consultation as a step, and the capability keeps
itself fresh: the generator computes the cache key from `HEAD` and a dirty-tree
marker and regenerates when the key it finds does not match, and a `--check`
mode reports staleness without rebuilding. There is deliberately no
`check-graph-freshness` CI gate. The cache is gitignored, so a gate over the
tree would never see it and would report it absent on every run — a rule that
nothing checks is a claim, and a gate that always passes by seeing nothing is
the worst kind of claim, the one that looks like coverage. Freshness is a
property the generator maintains, not a condition CI decides.

## Consequences

The generator never requires its heavy tiers. With Graphify absent it builds and
answers from the light index alone and reports the macro tier unavailable; with
tree-sitter absent it falls back to a standard-library import and symbol scan.
Python ships as the working reference indexer because the repository is
Python-heavy, and the other languages are extension points rather than
omissions. The capability therefore runs on a bare checkout, which is the only
state a consumer is guaranteed to have.

Issue #182's acceptance criterion AC-4 names a `check-graph-freshness` hook with
`enforced-in: tree`. This record reconciles it: the hook is not shipped, because
over a gitignored cache it is vacuous, and freshness is delivered instead as
self-healing logic in the generator plus the `--check` mode a session runs. The
AC is satisfied by the behaviour it wanted, not by the mechanism it named.

The graph reconciles with the component map rather than replacing it. The map in
`engineering/fundamentals/docs/component-map.md` is the structure a project
*declares*; the graph is the structure that *is*. Where a component claims paths
that the graph shows depending elsewhere, that gap is drift the agent can see,
and seeing it is one of the things the graph is for.

The wiring of this capability into the build and routing skills is a separate
layer (#183). This record decides what the graph is; it does not decide who
reads it.

## Alternatives considered

- **Commit the graph.** Rejected by `ARCHITECTURE.md`'s no-derived-tree
  principle. A committed derivation drifts against its source and misleads the
  agent that trusts it, which is worse than having no graph at all.
- **One tier.** Rejected. A single index rich enough for planning is too
  expensive to consult on every edit, and one cheap enough for every edit cannot
  answer the planning question. The two needs have opposite cost profiles, so
  they get two tiers.
- **Ship the `check-graph-freshness` gate the AC names.** Rejected. The cache is
  gitignored, so the gate reads nothing and reports it absent forever — a gate
  that cannot fail is not a guardrail, it is decoration that reads as coverage.
  Freshness belongs in the generator, which can see the cache, not in CI, which
  cannot.
- **Require Graphify and tree-sitter.** Rejected. A capability that works only
  with both installed works almost nowhere a consumer runs. Graceful degradation
  to the standard-library tier is what makes it a framework capability rather
  than a local convenience.
