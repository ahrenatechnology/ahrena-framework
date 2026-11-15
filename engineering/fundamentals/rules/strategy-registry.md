---
id: strategy-registry
type: rule
clade: engineering
subclade: architecture
title: One strategy per problem, kept
statement: A project keeps a registry of the strategy chosen for each recurring problem; a change adds no second way, and swaps a strategy only by a superseding decision.
enforcement: judgment
---

# One strategy per problem, kept

Three conditions. A codebase that solves the same problem two ways, with two `Result` types or two HTTP clients, makes every reader learn both and every change pick one. The cure is to choose once, write the choice down where a detector can read it, and make the only way out a recorded decision. The registry is a project file; this rule names its shape and where it lives, and never what a project chooses.

## Conditions

1. **CON-1. The project keeps a strategy registry.** The file is `.ahrena/strategies.json` at the repository root: an array of entries, each with `problem`, `strategy`, `decision` (the path of the ADR that chose it), `canonical` (the path of the implementation every caller uses), `status` (`active`, `migrating` or `superseded`) and, when superseded, `supersededBy` (an object holding the `problem` and `strategy` of the successor). The problems a project registers are those it has, such as: result format, error format, HTTP client, event envelope, persistence mode, validation library, test library and date library. Threshold: the file exists, every entry has every field, and each `decision` and `canonical` path resolves. Detector: a script validating the file against that shape.

2. **CON-2. A change adds no second way to a registered problem.** The state is a pull request that introduces an import, a type or a dependency which solves a registered problem differently from the entry with `status: active`. Threshold: 0 competing introductions in the diff. Detector: a search of the added lines for imports and type declarations that name a competing strategy, run against the registry; the TypeScript detector is owned by the structure detectors issue of #323.

3. **CON-3. A strategy changes only by a superseding decision.** The state is a diff of the registry that edits or replaces an `active` entry without adding a new ADR that supersedes the old one and a migration plan the ADR names. While an entry is `migrating`, the detector knows both strategies and accepts the new one in new code only. Threshold: 0 registry changes without a superseding ADR. Detector: a diff of the registry against its base, checked for the ADR.

## Where this stops

**It does not choose.** Which library or format a project registers is the project's decision, recorded in its ADR, and the rule is satisfied by any choice that is written down. [`pattern-selection.md`](pattern-selection.md) is where a choice between patterns is argued.

**It does not reach a problem nobody registered.** An unregistered problem has no second way to compete with. A reviewer who sees the same problem solved twice asks for an entry; the first entry is what turns the second solution into a finding.

**It does not reach code that existed before the entry.** CON-2 reads the lines a change adds. The old callers of a `migrating` entry are the migration plan's work, not findings.

**CON-3 does not reach a correction that keeps the strategy.** Editing `canonical` because the file moved, or `decision` because the ADR was renumbered, changes no strategy and needs no superseding ADR; the detector compares `problem` and `strategy`, not the paths.

**CON-2 sees names, not intent.** A wrapper that hides a second HTTP client behind a new function passes a search of imports at the call sites and fails it in the wrapper, which is where the finding should land; a client written by hand on raw sockets passes both, and that is left to review.

**This rule declares judgment because no detector ships yet.** A hook is declared in the change that lands the script, as [`layer-map.md`](layer-map.md) does.
