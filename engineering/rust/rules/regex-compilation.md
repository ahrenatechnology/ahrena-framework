---
id: regex-compilation
type: rule
clade: engineering
subclade: rust
title: A pattern is compiled once
statement: Rust compiles a regex or a multi-pattern matcher once, in a `static` `LazyLock` or at construction, never in a loop or per request.
enforcement: judgment
references:
  - docs/performance.md
  - docs/toolchain.md
---

# A pattern is compiled once

Compiling a regular expression parses it, builds an automaton and allocates; searching with the compiled one is cheap. A program that compiles inside a loop or on every request pays the expensive half every time and the cheap half once. The `regex` crate's own documentation calls compiling the same pattern in a loop an anti-pattern and recommends `std::sync::LazyLock`. [`docs/performance.md`](../docs/performance.md) puts this beside the other costs that a search pays up front.

Inherited from the predecessor's `lex-rust-no-regex-compilation-in-loops`, drawn from Andrew Gallant's [Regex engine internals as a library](https://burntsushi.net/regex-internals/). The source recommended `once_cell` and `lazy_static`; the standard library has had `OnceLock` since Rust 1.70 and `LazyLock` since 1.80, and neither crate is needed for this any longer.

## Conditions

1. **No regex is compiled from a literal pattern inside a loop.** Decided by Clippy's `clippy::regex_creation_in_loops`, in the default `perf` group, denied.

2. **A literal pattern is compiled in a `static` initialised by `LazyLock` or `OnceLock`, or once in the constructor of a value that lives as long as its uses.** Decided by a reviewer. Condition 1's lint sees a loop in the same function; it does not see a request handler, a function called from a loop elsewhere, or an iterator closure called per item. A compile in any of those is the same defect, and the reviewer follows the function to its callers to find it.

3. **A pattern built from input is compiled once per distinct input, not once per use.** Decided by a reviewer. A search term the user typed is compiled when it arrives and reused for every line it is searched against. A server that compiles one pattern per request from a small set of inputs caches the compiled ones. The same holds for `aho_corasick::AhoCorasick` and `regex_automata`'s engines.

4. **A literal pattern is valid.** Decided by Clippy's `clippy::invalid_regex`, in the `correctness` group, which Clippy denies by default; the condition is that nothing allows it. It is what makes the `expect` in `LazyLock::new(|| Regex::new(r"…").expect("…"))` the invariant [`panics.md`](panics.md) condition 2 asks for, rather than a panic waiting for a typo.

## Where this stops

**A program that runs once may compile in `main`.** A command-line tool that compiles its patterns at start-up and exits pays the cost once by construction. The rule is about the second compile, not the first.

**Thread contention is not addressed here.** A `Regex` is `Send + Sync` and is shared by reference across threads. The `regex` crate keeps a pool of scratch space per regex, and under very high contention from many threads a clone per thread can be faster; that is a measurement, and `docs/performance.md` says how to take one.

**Other compiled things follow the same reasoning and are not listed.** A compiled template, a parsed schema, a TLS configuration: each is expensive to build and cheap to use, and a reviewer reading condition 2 applies it to them. The rule names regexes because the predecessor did and because Clippy decides the commonest case.
