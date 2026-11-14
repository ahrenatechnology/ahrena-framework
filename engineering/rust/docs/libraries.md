---
id: libraries
type: doc
clade: engineering
subclade: rust
title: The crate to reach for, per problem
summary: For each kind of problem a Rust service, library or tool meets, the one crate this framework recommends, why, and the case where it is the wrong choice; with the evidence behind each choice and the crates deliberately not recommended.
references:
  - docs/error-handling.md
  - docs/async-and-concurrency.md
  - docs/testing.md
  - docs/performance.md
---

# The crate to reach for, per problem

An agent writing Rust meets the same dozen problems in every project, and the ecosystem offers three or four crates for each. Picking one per problem, with the reason, saves the search and makes two services written by two agents look alike. Each entry below names one crate, the reason it is the default, and the case where it is the wrong default, because a recommendation that cannot say when it does not apply is a habit.

**How the choices were made.** A crate is recommended when it is maintained (a release or a commit in the last year), widely used, and either the ecosystem's de facto standard or the one the other recommended crates are built around, so that choosing it does not fork the dependency tree. Download counts are crates.io's figures for the 90 days to 14 November 2026, read from its API on that date, and are given only where they decide between two candidates. Versions are deliberately not pinned here; the project's lock file pins them.

The predecessor's `codex-rust-burntsushi-ecosystem` mapped Andrew Gallant's crates to their uses. Its entries for text search, bytes, CSV and dates are carried into the sections below; its entries for internals (`regex-automata`, `regex-syntax`) and for `fst` move to [`performance.md`](performance.md), where they are a choice about speed rather than a default.

## Runtime and network

### Async runtime: `tokio`

**Why.** It is the runtime the rest of this page assumes: `axum`, `reqwest`, `sqlx`, `tonic` and `tracing` are built for it or by its organisation, so any other choice forks the stack. 309 million downloads in the period; `async-std`, its long-time alternative, was marked unmaintained by RustSec advisory RUSTSEC-2025-0052 in August 2025.

**Wrong when** the program does not wait on I/O. A CLI that reads files and computes needs no runtime at all, and a CPU-bound batch job wants threads (`rayon`, below). An embedded target without an operating system wants `embassy`.

### HTTP server: `axum`

**Why.** Built by the Tokio organisation on `hyper` and `tower`, so a middleware written for any `tower` service — timeouts, tracing, compression, rate limits from `tower-http` — works on it unchanged. Handlers are ordinary async functions with typed extractors; there is no macro language to learn. 165 million downloads against `actix-web`'s 13.5 million.

**Wrong when** the service is gRPC (`tonic`, also on `tower`), or when the team already runs `actix-web` in production: both are sound, and the cost of switching is higher than the difference.

### HTTP client: `reqwest`

**Why.** The default high-level client on `hyper`, with connection pooling, redirects, timeouts, TLS and JSON through `serde`. It shares the runtime and the `tower` world with `axum`.

**Wrong when** the program is synchronous and does not otherwise need Tokio: `ureq` is a blocking client with no runtime, and pulling Tokio into a small CLI for one request is the larger dependency. Never `reqwest::blocking` inside async code; [`rules/async-blocking.md`](../rules/async-blocking.md) condition 1 decides it.

### Retries: `backon`

**Why.** Exponential, constant and Fibonacci back-off with jitter, for sync and async calls, as a combinator on the call (`call.retry(ExponentialBuilder::default())`). Last released in October 2025, with 44 million downloads in the period. `backoff`, the crate older code reaches for, was marked unmaintained by RUSTSEC-2025-0012.

**Wrong when** the retry belongs to a layer that already has one — `tower`'s retry middleware on an `axum` or `tonic` stack, or the database pool's own reconnect. Two retry layers multiply each other's attempts.

## Data

### Serialization: `serde`, with `serde_json` for JSON

**Why.** It is the format-independent standard: almost every crate that reads or writes data implements its traits, so one `#[derive(Serialize, Deserialize)]` serves JSON, TOML, YAML, CSV and MessagePack. 432 million downloads; there is no second candidate.

**Wrong when** the format has a schema compiler of its own and other languages read it — Protocol Buffers through `prost`, Cap'n Proto — where the schema, not the Rust struct, is the source of truth. And `serde`'s derive is not validation: a field that parses is not a field that is valid (below).

### Validation: a newtype with `TryFrom`, no crate

**Why.** "Parse, don't validate": a `struct Email(String)` whose only constructor checks the value carries the check in its type, and `#[serde(try_from = "String")]` makes deserialisation run it. Every function that takes an `Email` knows it was checked, which no annotation-driven validator can say.

**Wrong when** a form has dozens of fields with independent constraints and the errors must be reported together, field by field. Then `garde` or `validator` collect them; neither replaces the newtype for a value that travels through the domain.

### Database access: `sqlx`

**Why.** Plain SQL with queries checked against the real schema at compile time (`query!` and `query_as!`), async on Tokio, with migrations built in (`sqlx::migrate!`). The SQL is the SQL the database runs, which keeps the query a reviewer reads and the one in production the same. Compile-time checking needs a database or the offline data `cargo sqlx prepare` writes, and CI carries one or the other.

**Wrong when** the application is synchronous (`diesel`, whose query builder also type-checks against the schema), or when queries are built dynamically from many optional filters, where a query builder — `diesel`'s or `sea-query` — is clearer than string assembly.

### Database migrations: `sqlx`'s own

**Why.** One tool for queries and migrations, and the migrations are plain SQL files run in order by `sqlx migrate run` or embedded with `sqlx::migrate!`. A second migration tool next to `sqlx` is a second record of which migrations ran.

**Wrong when** the project does not use `sqlx`: `diesel` ships its own, and `refinery` serves a project on another driver.

### Dates and times: `jiff`

**Why.** Time-zone-aware arithmetic that follows the IANA database and the design of JavaScript's Temporal proposal, by Andrew Gallant; it makes the ambiguous cases (a day that is 23 hours long, a time that does not exist) explicit rather than silent. Its documentation compares it with `chrono` and `time` point by point.

**Wrong when** a dependency's API already speaks `chrono` (many database drivers and older crates do) or `time`: converting at every boundary costs more than the better arithmetic gives. `jiff` is also still before 1.0, and a library that exposes date types on its surface takes that version into its own.

### CSV: `csv`

**Why.** Andrew Gallant's, fast, `serde`-integrated, with a `csv-core` underneath that needs no allocation. There is no serious alternative.

**Wrong when** the data is too large for row-by-row processing and wants a columnar engine — `polars` or Arrow — which is a different problem.

## Errors

### Error types for a library: `thiserror`

**Why.** A derive that writes the `Display`, `Error` and `From` implementations [`rules/error-types.md`](../rules/error-types.md) asks for, and nothing else: the generated code is what a person would write, and `thiserror` does not appear in the library's public API. 530 million downloads, the most of any crate on this page. [`error-handling.md`](error-handling.md) shows the shape.

**Wrong when** the library wants context attached at each call site rather than a variant per source, where `snafu`'s context selectors do more of the work. Both satisfy the rule; `thiserror` is the default because it adds less.

### Error handling in an application: `anyhow`

**Why.** One error type for everything a binary can fail with, `.context("reading config")` to say what it was doing, and a chain of causes printed at the top. It is the right tool exactly where `thiserror` is not: at the last caller, where nobody matches on the error.

**Wrong when** the code is a library, by [`rules/error-types.md`](../rules/error-types.md). `eyre` is the same design with pluggable reports; `color-eyre` makes them pretty for a CLI. `anyhow` is the default because it is the one most code already uses.

## Tools and operations

### Command-line parsing: `clap`, with the derive API

**Why.** A struct with `#[derive(Parser)]` is the interface, and help, completion, validation and error messages come from it. It is the standard, at 290 million downloads.

**Wrong when** binary size or compile time is the constraint — a tool shipped to constrained devices — where `lexopt` or `pico-args` parse by hand in a few kilobytes. The trade is writing the help text yourself.

### Logging and tracing: `tracing`, with `tracing-subscriber`

**Why.** Structured events and spans rather than lines of text, so a request's logs carry its fields and nest under it, and the same instrumentation exports to OpenTelemetry through `tracing-opentelemetry`. It is the Tokio organisation's, and `axum`, `tower-http`, `reqwest` and `sqlx` emit to it.

**Wrong when** the code is a small library with no async and no spans to speak of, where the `log` facade is lighter and every application can still collect it (`tracing-subscriber` reads `log` records). A library chooses a facade and never installs a subscriber; that is the application's decision.

### Data parallelism: `rayon`

**Why.** Turning `iter()` into `par_iter()` spreads CPU-bound work across a work-stealing pool with no locks in sight; ripgrep's directory walking and many parsers run on it.

**Wrong when** the work waits on I/O — that is the async runtime's — or when the parallel part is so small that the pool's start-up dominates. Inside async code, a `rayon` job is started from `spawn_blocking` or sends its result back over a channel, never awaited by blocking the worker.

### Directory traversal: `ignore`, or `walkdir` when `.gitignore` does not matter

**Why.** `ignore` is ripgrep's walker: parallel, and it honours `.gitignore`, `.ignore` and hidden files the way a developer expects. `walkdir` is the simple, sequential, rule-free one, by the same author.

**Wrong when** the walk must see every file regardless of ignore rules — a backup tool, an archiver — which is `walkdir`'s case and why both are listed.

### Text search: `regex`, `aho-corasick` and `memchr`

**Why.** `regex` guarantees worst-case `O(m * n)` search, so a pattern from a user cannot make it take exponential time, which a backtracking engine cannot promise. For a set of literal strings `aho-corasick` is faster than an alternation in a regex; for one byte or one substring `memchr` is faster still. All three are what `regex` itself uses inside. [`rules/regex-compilation.md`](../rules/regex-compilation.md) says how to hold a compiled pattern.

**Wrong when** the pattern needs look-around or back-references, which `regex` does not support by design; `fancy-regex` adds them over a backtracking engine and gives up the time bound to do it.

### Bytes that may not be UTF-8: `bstr`

**Why.** String operations — find, split, lines, trim — on `&[u8]`, so a program can treat file contents as text without first proving they are UTF-8. It is what [`rules/utf8-io.md`](../rules/utf8-io.md) condition 1 points to.

**Wrong when** the input's encoding is guaranteed; then `str` is simpler and the standard library is enough.

## Testing and measurement

### Test runner: `cargo-nextest`

**Why.** Runs each test in its own process, in parallel, with retries for flaky tests and per-test timeouts, and reports the slow ones. A test that leaks global state into the next is caught by the process boundary instead of becoming an order-dependent failure.

**Wrong when** the suite is doc tests, which `cargo-nextest` does not run; keep `cargo test --doc` beside it. For a small crate, `cargo test` is enough and needs nothing installed.

### Property-based tests: `proptest`

**Why.** Strategies that generate structured input and, on a failure, shrink it to the smallest case that still fails, with failing seeds saved and replayed. Its strategies compose more freely than `quickcheck`'s single `Arbitrary` per type. [`testing.md`](testing.md) says what a property is.

**Wrong when** the goal is finding crashes in a parser from raw bytes, which is fuzzing: `cargo-fuzz` with the `arbitrary` crate explores far more inputs, guided by coverage.

### Snapshot tests: `insta`

**Why.** For output too large to assert by hand — a rendered page, a formatted error, a serialised structure — `insta` stores the expected output beside the test and `cargo insta review` shows each change as a diff to accept or reject.

**Wrong when** the output has one field that matters; an `assert_eq!` on that field says what the test is about, and a snapshot says only that something changed.

### Test doubles: a trait the code owns, implemented by hand; `mockall` when that is not enough

**Why.** A port the domain defines as a trait, with an in-memory implementation in the test module, is a fake that runs real logic and needs no macro. It also keeps the test from asserting on call sequences, which is what makes mock-heavy suites break on every refactoring.

**Wrong when** the trait is wide, the interactions are the behaviour under test (a call must happen exactly once), or the trait belongs to another crate. Then `mockall`'s `#[automock]` writes the double.

### Benchmarks: `criterion`

**Why.** Statistical benchmarking that reports confidence intervals and compares against the previous run, on stable Rust. Maintained, with releases through 2026.

**Wrong when** the measurement is of a whole program's behaviour under load, which is a profiler's (`perf`, `samply`) and a load generator's, not a micro-benchmark's. `divan` has a lighter API and has not released since April 2025; it is the alternative if `criterion` stops being maintained, not today's default. [`performance.md`](performance.md) says when to measure at all.

## Where this stops

**These are defaults, not mandates.** A project with a reason to choose otherwise — an existing dependency, a platform constraint, a team's experience — writes the reason down and keeps its choice. No rule in this plugin names a crate except where a condition does not exist without one, and those are named in the rules themselves.

**The list ages.** A crate's maintenance changes, and two of the alternatives above (`async-std`, `backoff`) were defaults a few years ago. The evidence for each entry is dated, and an entry whose crate has had no release in a year is the first to recheck.

**No version is given, and none should be.** A version here would be wrong at the next release and would compete with the project's lock file.

**Security review of a dependency is not this page's.** Whether a crate is safe to depend on — its `unsafe`, its maintainers, its advisories — is `cargo deny check` in [`toolchain.md`](toolchain.md) and `ahrena-engineering-security`'s supply-chain review.
