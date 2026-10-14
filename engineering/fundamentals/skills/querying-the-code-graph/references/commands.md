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

- **Graphify absent.** `locate`, `deps` and `path` answer from the light index.
  `explain` reports the macro tier unavailable and suggests reading the component
  map for the declared structure.
- **tree-sitter absent.** The light tier uses the standard-library scan. Python
  is fully indexed through the `ast` module. A file in a language no indexer
  covers is recorded as present but unindexed, and a query over it returns the
  unindexed note rather than a wrong answer.
- **Outside a git checkout.** The script keys the cache to the working tree
  rather than a commit and still builds the light index, so the queries work; the
  freshness key cannot name a commit and says so.
