---
id: unit-tests
type: rule
clade: engineering
subclade: rust
title: A unit's tests sit in its own file
statement: Every Rust source file that defines a function carries its unit tests in its own `#[cfg(test)] mod tests`; integration tests live in `tests/`.
enforcement: judgment
references:
  - docs/testing.md
  - docs/toolchain.md
---

# A unit's tests sit in its own file

A reader who opens a unit finds its tests beside it, and a change to the unit shows its tests in the same diff. In Rust the unit is the function or method, grouped by concern into a module, and a module is a file. This rule puts the tests of a file's functions in that file. [`docs/testing.md`](../docs/testing.md) says how such a test is written.

**What the specification says.** The Reference defines `cfg(test)` as enabled when compiling the test harness ([Conditional compilation, `test`](https://doc.rust-lang.org/reference/conditional-compilation.html#test)) and `#[test]` as marking a function to be run as a test ([The `test` attribute](https://doc.rust-lang.org/reference/attributes/testing.html#the-test-attribute)). Neither says where a test lives. The community does: the Rust book's convention is to "create a module named `tests` in each file" ([Test Organization](https://doc.rust-lang.org/book/ch11-03-test-organization.html#the-tests-module-and-cfgtest)), and Cargo treats files under `tests/` as integration tests ([Cargo Targets](https://doc.rust-lang.org/cargo/reference/cargo-targets.html#integration-tests)). This rule follows both.

**The form chosen, and why.** The owner's directive on #285, item 9, asked for one of two forms: the in-file `#[cfg(test)] mod tests`, or a sibling `tests.rs` declared from the unit's module. This rule takes the in-file module. It is the language's own convention, so a Rust reader looks there first. It sees the module's private items without a `pub(crate)` widened for the test. And a file whose tests have grown too long for it is a file doing too much: the remedy is to split the unit, which the single-responsibility limits already ask for, not to move its tests away. The sibling file stays allowed for one case, a module whose test data is large and textual, declared `#[cfg(test)] mod tests;` beside it.

## Conditions

1. **A source file under a crate's `src/` that defines a function with a body, other than `main`, carries at least one test attribute.** Decided by `hooks/check-rust.py`. Any attribute whose last segment is `test` counts — `#[test]`, `#[tokio::test]`, `#[sqlx::test]` — so an async test satisfies it. A file of declarations alone (`mod`, `use`, types, trait signatures) owes no test, and neither does a `main.rs` whose only function is `main`. Files under `src/bin/` are other crates and are read as their own roots. A file named `tests.rs` is the sibling form and is not itself read.

2. **The tests of a file are in that file's `#[cfg(test)] mod tests`, or in a sibling `tests.rs` declared from it with `#[cfg(test)] mod tests;`, never in another module's tests.** Decided by a reviewer. A function tested only from another file's test module is a function whose test a reader of its file cannot find.

3. **Tests that exercise more than one unit through the public API live in `tests/`.** Decided by a reviewer. They see only what a caller sees, which is the point of them, and Cargo builds each file there as its own crate.

## Where this stops

**Presence, not sufficiency.** Condition 1 reports a file with no test at all. Whether its tests cover each function, and whether they test behaviour rather than structure, is [`docs/testing.md`](../docs/testing.md) and the reviewer's; coverage tools say how much ran.

**A doc test does not satisfy condition 1.** It is documentation that compiles and runs, read by a caller, and belongs to the public API; a unit test pins a module's own behaviour, private items included. A file can and often should have both.

**Measured over a local Cargo registry**, 328 crate directories, condition 1 reported 4,421 files in 292 crates. Much of the ecosystem tests through `tests/`, doc tests and a separate test crate. Those are legitimate choices for a published library, and they are not the form this framework asks of the code it writes, which is why the condition is new code's and not a description of the ecosystem's.

**Generated code is excluded by path.** A file written by `build.rs`, `bindgen` or a protocol compiler is tested through what uses it; leave it out of the paths the hook is given and say why.
