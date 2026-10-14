---
name: provisioning-the-code-graph
description: Use before any macro-tier work on the code graph, and whenever /graph-doctor runs, to provision the optional Graphify tier or report exactly how to enable it — always leaving the guaranteed light floor answering. Runs the doctor, reads the two-tier status, (re)builds the macro tier when Graphify is present, installs tree-sitter grammars when pip is, and never tries to install Graphify, which is a personal skill and not a package.
type: skill
clade: engineering
subclade: architecture
references:
  - docs/code-graph.md
  - skills/querying-the-code-graph/SKILL.md
---

# Provisioning the code graph

This is the procedure that makes the code graph's optional macro tier ready, or
reports precisely what it needs, before an agent leans on it — and that a person
runs through `/graph-doctor` to diagnose the graph on a machine.
[`docs/code-graph.md`](../../docs/code-graph.md) defines the two tiers and the
guarantee split this honours: the **light tier** is the always-available floor
(Python via the standard library, zero install, `locate`/`deps`/`path` always
answer), and the **macro tier** (Graphify) is optional enrichment. This skill
ensures the macro tier *or reports how*; it never blocks on it, because the floor
already answers. The doctor is the `doctor` subcommand of the one script that
[`skills/querying-the-code-graph`](../querying-the-code-graph/SKILL.md) runs; its
surface is in that skill's [`references/commands.md`](../querying-the-code-graph/references/commands.md).

## 1. Run the doctor

From the repository root, run the doctor with no flags. It only inspects and
reports — it changes nothing — and it exits 0 even when the macro tier is absent.

```sh
python3 engineering/fundamentals/skills/querying-the-code-graph/scripts/graph.py doctor
```

## 2. Read the two-tier status

The report prints the **light tier** first (always ready; tree-sitter grammar
availability per language it finds) and then the **macro tier** (whether
`graphify` is on PATH *and* whether a build exists). Read which of the two
outcomes you are in:

- **Both ready.** The macro tier's `status` is `ready`. Proceed; a macro-tier
  `explain` will answer from the overview.
- **Macro tier unavailable.** Proceed on the guaranteed light floor, and carry
  the doctor's `to enable` lines back verbatim as the actionable report — they
  name exactly what the tier needs. Do not stop work: the floor answers *where*,
  *what depends on what* and *the path between two symbols* without it.

## 3. Ensure-or-report the macro tier

Act only on what is safe, and only when asked to provision rather than inspect.

When `graphify` is on PATH but no build exists, build it — this re-extracts the
code into `graphify-out/` and needs no network:

```sh
python3 engineering/fundamentals/skills/querying-the-code-graph/scripts/graph.py doctor --build
```

When `graphify` is **not** on PATH, do not try to install it. Graphify is the
owner's personal skill (`~/.claude/skills/graphify/`), not a published package;
report the doctor's `to enable` lines and move on. Installing it is the owner's
act of consent, never this skill's side effect.

## 4. Install tree-sitter grammars when asked

The light floor needs no grammar for Python. When the tree holds other languages
whose grammar is absent, and you are provisioning rather than only inspecting,
install the published grammars — this degrades to a precise `pip install` line to
run elsewhere when pip is absent here:

```sh
python3 engineering/fundamentals/skills/querying-the-code-graph/scripts/graph.py doctor --install-grammars
```

## When this skill does not apply

**The light floor already answers the question.** `locate`, `deps` and `path`
over Python are the guaranteed tier and never need provisioning. A *where* or
*what-depends-on-what* question is [`skills/querying-the-code-graph`](../querying-the-code-graph/SKILL.md)'s
job directly; reach here only when the macro-tier overview is what is wanted.

**A sandbox with no network, where provisioning can only report.** When neither
Graphify nor pip can reach what they would install, the doctor still runs and
still reports exactly what each tier needs — but it cannot provision, and that
report *is* the outcome. Carry it back; do not treat the inability to install as
a failure of the graph, which is still answering on its floor.

**Deciding whether the macro tier is worth building.** This skill makes the tier
ready or names its cost. Whether a given plan needs the overview at all is a
judgment the planning step makes, not a step this skill takes on its behalf.

**Changing what the graph is.** The tiers, the cache and the guarantee split are
fixed by [`docs/code-graph.md`](../../docs/code-graph.md) and `ADR-015`. This
skill provisions within that shape; it does not amend it.

<!--
Directory layout:

skills/provisioning-the-code-graph/
└── SKILL.md    the whole procedure; it reuses querying-the-code-graph's script
                and command reference rather than carrying its own.

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
