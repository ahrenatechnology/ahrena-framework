# The code-graph command surface

The one script, `scripts/graph.py`, is both the generator that maintains the
cache and the query interface over it. It is standard-library only and requires
neither Graphify nor tree-sitter to run. [`docs/code-graph.md`](../../../docs/code-graph.md)
defines the cache and the tiers; this gives the exact commands, their output and
their exit codes.

Run every command from anywhere inside the repository. The script finds the
repository root with `git rev-parse --show-toplevel`, and falls back to the
current directory when it is run outside a git checkout.

## Freshness

| Command | What it does |
|---|---|
| `refresh` | Brings the cache up to the current commit and working tree. Regenerates only when the stored freshness key does not match; a current cache is left untouched. Prints whether it rebuilt and which tiers it built. |
| `--check` | Reports whether the cache is fresh and which tiers are available on this machine. Regenerates nothing. |

The freshness key is the forty-character `HEAD` sha on a clean tree, and the sha
with a short digest of the dirty working tree appended when there are
uncommitted changes. The cache directory is `.ahrena/graph/<sha>/`, and the
`key` file inside it holds the full key the build was keyed to.

`--check` exits 0 whether the cache is fresh or stale — it is a report, not a
gate. It prints one of `fresh` or `stale`, then a line per tier: the light
per-language index (always available, Python via the standard-library scan), the
tree-sitter grammars (present or absent), and the Graphify macro tier (present
or absent).

## Provisioning

The `doctor` command is the provisioning path for the optional macro tier. It
is driven by the `provisioning-the-code-graph` skill and by `/graph-doctor`, and
it **ensures-or-reports**: it readies the macro tier where it safely can, and
otherwise prints exactly how to enable it. It never installs Graphify, which is
a personal skill rather than a package, and it never hard-fails on an absent
tier.

| Command | What it does |
|---|---|
| `doctor` | Prints the two-tier status and changes nothing. The **light tier** is reported ready (stdlib floor), with tree-sitter grammar availability per language found in the tree; the **macro tier** reports whether `graphify` is on PATH *and* whether a build (`graphify-out/graph.json`, or the commit cache's `graphify/graph.json`) exists, plus `to enable` lines when it does not. |
| `doctor --build` | When `graphify` is on PATH, (re)builds the macro graph via `graphify update <root>` (no network, no LLM). When it is absent, reports how to enable Graphify and builds nothing. |
| `doctor --install-grammars` | Installs the tree-sitter grammar distributions the detected non-Python languages lack, via `python3 -m pip install`, when pip is importable. When pip is absent, degrades to printing the exact `pip install` line to run elsewhere. Python needs no grammar; a Python-only tree installs nothing. |

`doctor` exits 0 whether or not the macro tier is available — the absent tier is
a reported status, not a failure. A malformed invocation (an unknown flag) exits
2. The flags compose: `doctor --build --install-grammars` provisions both.

## Queries

Every query runs `refresh` implicitly first, so a query is always answered
against a current cache.

| Command | Answers | Output |
|---|---|---|
| `locate <path-or-symbol>` | Where am I, which component owns this path | The module, the symbols it declares, and the owning component when a component map is present. |
| `deps <path-or-module>` | What I depend on, what depends on me | The internal modules it imports, and in reverse the modules that import it. |
| `path <from> <to>` | How two files or symbols connect | The shortest dependency chain between them, or a line stating that none exists. |
| `explain <node>` | The macro shape of a node | Graphify's god nodes, communities and plain-language account. When the macro tier is unavailable, a line saying so and pointing at the component map. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | The command answered. An empty `path` result and an unavailable macro tier are answers, not failures. |
| `1` | A query names a target the index does not hold — an unknown file, module or symbol. |
| `2` | The command line is malformed — an unknown subcommand or a missing argument. |

## Degradation, per tier

- **Graphify absent, or present with no build yet.** `locate`, `deps` and `path`
  answer from the light index. `explain` reports the macro tier unavailable,
  points at `doctor` / `/graph-doctor` to provision it, and suggests reading the
  component map for the declared structure meanwhile.
- **tree-sitter absent.** The light tier uses the standard-library scan. Python
  is fully indexed through the `ast` module. A file in a language no indexer
  covers is recorded as present but unindexed, and a query over it returns the
  unindexed note rather than a wrong answer.
- **Outside a git checkout.** The script keys the cache to the working tree
  rather than a commit and still builds the light index, so the queries work; the
  freshness key cannot name a commit and says so.
