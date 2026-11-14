---
id: testing
type: doc
clade: engineering
subclade: rust
title: Testing Rust
summary: Where unit, integration and doc tests live and what each can see, how a test reaches behaviour rather than structure, what property, snapshot and fuzz tests add and when, and how async and I/O code is tested without a flaky suite.
references:
  - rules/unit-tests.md
  - rules/utf8-io.md
  - rules/panics.md
  - docs/libraries.md
---

# Testing Rust

Cargo builds three kinds of test into the language's own tooling, and the choice between them is a choice about what the test can see. This page ports the predecessor's `codex-rust-testing-docs`, built on the Rust book's chapters on testing and documentation, and adds what that edition of the book predates: property tests, snapshot tests, fuzzing and the async test harness. What to test and in which order is `ahrena-engineering-backend`'s `driving-with-tdd`; this page is how those tests are written in Rust.

**What the specification says.** The Reference defines the `test` configuration and the `#[test]` attribute ([Conditional compilation, `test`](https://doc.rust-lang.org/reference/conditional-compilation.html#test); [The `test` attribute](https://doc.rust-lang.org/reference/attributes/testing.html#the-test-attribute)); Cargo defines `tests/` as the home of integration tests ([Cargo Targets](https://doc.rust-lang.org/cargo/reference/cargo-targets.html#integration-tests)) and runs doc tests from the documentation of a library. Where a unit test lives is left to convention, and the convention this page follows is the Rust book's, which [`rules/unit-tests.md`](../rules/unit-tests.md) makes a condition.

## The three kinds

**Unit tests** live in the file they test, in a `#[cfg(test)] mod tests` at the bottom, and see everything in that module including private items. They are compiled only for `cargo test`. They are where a domain rule is pinned: a function, a type's invariants, a parser's edge cases. Every file that defines a function carries them, and [`rules/unit-tests.md`](../rules/unit-tests.md) gives the reason for the in-file module over a sibling file: it is where a Rust reader looks, it reaches private items without widening their visibility, and a file whose tests no longer fit beside it is a file to split.

**Integration tests** live in `tests/` at the crate root. Each file is compiled as a separate crate that depends on the library, so it sees exactly the public API and nothing else. They are where the crate is used as a caller would use it. Helpers shared between them go in `tests/common/mod.rs` (a directory, so Cargo does not compile the helper as a test of its own). A binary crate has no library for `tests/` to import, which is the strongest argument for putting a binary's logic in `src/lib.rs` and keeping `main.rs` to argument parsing and wiring.

**Doc tests** are the code blocks in `///` comments, compiled and run by `cargo test` as if they were integration tests. They keep examples from rotting: a renamed method breaks the build of the example that uses it. Lines starting with `# ` are compiled and hidden from the rendered docs, which keeps setup out of the reader's way. `cargo-nextest` does not run them, so a project using it keeps `cargo test --doc` in CI.

## Testing behaviour, not structure

A test that calls a private helper pins the helper; a test that calls the public function pins what the function promises. Unit tests may reach private items, and the temptation is to test every one. The test that survives a refactoring is the one written against the smallest surface that exhibits the behaviour — usually the public function, sometimes a private one with an invariant worth pinning on its own.

Each test asserts one behaviour and is named for it: `rejects_a_key_without_a_value`, not `test_parse_3`. `assert_eq!(actual, expected)` prints both on failure, `assert!(matches!(err, Error::Syntax { line: 3 }))` checks a variant without needing `PartialEq` on the error type.

**An error path is a behaviour.** A function returning `Result` has a test for each variant its callers branch on. Testing that it panics, with `#[should_panic(expected = "…")]`, is right only for the panics [`rules/panics.md`](../rules/panics.md) allows — a broken precondition — and the `expected` string keeps the test from passing on the wrong panic.

**Bytes that are not UTF-8 are an input.** A function that reads from outside the program has a test that feeds it invalid UTF-8; [`rules/utf8-io.md`](../rules/utf8-io.md) condition 3 asks for it, because without one the claim that the function handles such input was never run.

**`unwrap` in a test is fine.** A test's failure is the report, and a panic with a line number is a good one. A test may also return `Result<(), Box<dyn Error>>` and use `?`, which reads better when there are many fallible steps.

## Beyond examples

**Property tests** state something true for all inputs — a round trip (`parse(print(x)) == x`), an invariant (a sorted output is sorted and has the same elements), an equivalence with a simpler implementation — and `proptest` generates inputs and shrinks a failure to its smallest case. One property often replaces a dozen examples and finds the one nobody thought of. They belong on parsers, serialisers, data structures and any function with an algebraic law.

**Snapshot tests** with `insta` pin a large output — a formatted report, an error message, a generated file — and show each change as a diff to accept. They are for output that a person judges by reading, and they are the wrong tool when one field is what the test is about.

**Fuzzing** with `cargo-fuzz` feeds a function coverage-guided random bytes for minutes or hours and keeps any input that crashes it. It is how a parser of untrusted input is shown not to panic or loop, and it needs a nightly toolchain. It runs outside the regular suite, with the crashing inputs it finds turned into ordinary regression tests.

[`libraries.md`](libraries.md) gives the reasons for each of these crates over the alternatives.

## Async and I/O

`#[tokio::test]` runs an async test on a current-thread runtime; `#[tokio::test(flavor = "multi_thread")]` when the code under test needs real parallelism. Time-dependent code is tested with `tokio::time::pause()`, from Tokio's `test-util` feature, after which `sleep` and timeouts advance instantly and deterministically — a test that really sleeps is slow, and one that races a real clock is flaky.

A test that touches the file system writes under a directory from `tempfile`, never under a fixed path, so parallel tests do not collide. A test against a database runs against a real one, started for the test run, with migrations applied; `sqlx::test` creates a fresh database per test. Code that talks to a third-party service is tested against a fake of the port the code defines, as [`libraries.md`](libraries.md) describes under test doubles, with the real service exercised by a smaller set of contract or end-to-end tests.

## Where this stops

**Coverage figures are not set here.** `cargo llvm-cov` measures line and branch coverage; what figure a project holds itself to is a decision `ahrena-engineering-quality` and the project make, and a figure without a measurement behind it is not one this plugin invents.

**Benchmarks are not tests.** [`performance.md`](performance.md) covers them.

**Test organisation for a large workspace** — a separate crate for shared fixtures, feature-gated test utilities exported from a library — is a layout decision the project makes; the three kinds above work the same in each crate.
