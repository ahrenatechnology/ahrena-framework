---
id: performance
type: doc
clade: engineering
subclade: rust
title: Performance in Rust, measured first
summary: When to optimise and how to measure, the costs a Rust program pays without noticing — allocation, compiling a pattern, decoding text — and how ripgrep's search is layered to avoid them, with the crates that provide each layer.
references:
  - rules/regex-compilation.md
  - rules/utf8-io.md
  - docs/libraries.md
---

# Performance in Rust, measured first

This is the companion to [`rules/regex-compilation.md`](../rules/regex-compilation.md) and [`rules/utf8-io.md`](../rules/utf8-io.md). It ports the predecessor's `codex-rust-performance-and-search`, built on Andrew Gallant's articles on [ripgrep](https://burntsushi.net/ripgrep/), [regex internals](https://burntsushi.net/regex-internals/), [`fst`](https://burntsushi.net/transducers/) and [`bstr`](https://burntsushi.net/bstr/). The source stated ripgrep's design decisions as rules for every program — "never use memory maps", "never use `str::contains` in a hot path" — and they are not. They are what one search tool measured for its workload, and they are kept here as that.

## Measure, then change

Rust is fast by default, and most code is not on the path that decides how fast the program is. An optimisation starts from a measurement that says where the time goes, and ends with a measurement that says it went down.

- **A profile of the real program on real input** finds the hot path: `perf` on Linux, `samply` on Linux and macOS, `cargo flamegraph` to draw either. Build with `--release` and `debug = true` in the release profile so the profile has symbols.
- **A micro-benchmark** with `criterion` pins one function's speed and reports, on each run, whether it changed beyond noise. It is how a fix is kept from regressing, not how a hot path is found.
- **A count of allocations** with `dhat` or a counting global allocator shows the cost a profile spreads thinly across `malloc` and `free`.

An optimisation without the first and last measurement is a guess with a commit message.

## Costs a program pays without noticing

**Allocation in a loop.** A `String` built per line, a `Vec` collected only to be iterated once, a `format!` whose result is written straight out. The fix is to reuse: a buffer cleared and refilled each iteration, an iterator chain that never collects, `write!` into the output. APIs that take a `&mut` buffer exist for this ([`api-design.md`](api-design.md)).

**Compiling something twice.** A regex, a template, a parsed schema: the expensive half is building it. [`rules/regex-compilation.md`](../rules/regex-compilation.md) holds the regex case; the reasoning is the same for the others.

**Decoding text that did not need decoding.** Validating UTF-8 is a pass over every byte. A program that searches, splits or counts lines can do all three on `&[u8]` with `bstr` and decode only the lines it prints, which is the same choice that makes it correct on invalid input ([`rules/utf8-io.md`](../rules/utf8-io.md)).

**Line-by-line reading.** `BufRead::lines` allocates a `String` per line and validates each one. For a search that matches few lines, reading a large buffer, searching it whole, and finding line boundaries only around a match is far cheaper. ripgrep does this with a 64 KiB default buffer (`DEFAULT_BUFFER_CAPACITY` in `grep-searcher`'s `line_buffer.rs`), growing it only when a single line does not fit.

**Contention.** An `Arc<Mutex<T>>` touched by every thread serialises them. A thread-local accumulator merged at the end, or `rayon`'s `fold` and `reduce`, removes the lock from the hot path.

## How ripgrep layers a search

The predecessor's best material, and still accurate, is how ripgrep avoids running a regex engine on most of its input.

1. **Read incrementally into a fixed buffer.** Memory maps are used for a single large file and avoided when searching a directory tree, because, in Andrew Gallant's measurements, creating and tearing down a map per file costs more than reading thousands of small files into a buffer.
2. **Prefilter on literals.** Most patterns contain a literal that every match must contain. `regex` extracts it and searches for it first with `memchr` (one byte or one substring, vectorised) or `aho-corasick` (several literals, with the Teddy algorithm on vector instructions). The full engine runs only around a candidate.
3. **Confirm with the cheapest engine that answers the question.** `regex-automata` holds several: a lazy DFA that builds its states as it goes, which answers "is there a match and where" fastest; a PikeVM, slower, that also reports capture groups; a bounded backtracker for small inputs. `regex` picks among them per search, and every one keeps the `O(m * n)` worst case.
4. **Buffer output per thread.** Parallel workers write into their own buffers and the output is serialised per file, so matches from two files never interleave.

Using `regex` gets the first three without writing them. `regex-automata` is for the program that needs an engine directly — a serialised DFA, a stream search — and `regex-syntax` for one that inspects patterns without searching.

**`fst` for very large sets of strings.** A finite state transducer stores a sorted set or map of strings compressed, searchable by prefix, range, regex or edit distance. Andrew Gallant's article indexes 1.6 billion keys with it. It needs its keys inserted in sorted order, and it is the right tool only when the set is large enough that a `HashSet` does not fit or a sorted `Vec` is too slow; below that, the standard collections win on simplicity.

## Where this stops

**These are a search tool's numbers.** The 64 KiB buffer, the decision against memory maps and the layered engines were measured by ripgrep for searching source trees. A program with another workload measures its own, which is the first section's point.

**`str::contains` is not forbidden.** The predecessor said to replace it with `memchr::memmem` in every hot path, on the ground that the standard library did not vectorise substring search; the source itself hedged that this held for older versions. Whether `memmem` wins for a given needle and haystack is a benchmark's question. It has a clear advantage when the same needle is searched many times, because `memmem::Finder` builds its searcher once.

**Compile-time performance, binary size and `unsafe` optimisations are out of scope.** The first two are build engineering; the third is [`rules/unsafe-code.md`](../rules/unsafe-code.md), which asks that an unchecked operation earn its place with a measurement.
