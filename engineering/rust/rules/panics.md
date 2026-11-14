---
id: panics
type: rule
clade: engineering
subclade: rust
title: No panic on a path that can fail
statement: Rust outside tests takes no `unwrap`, `panic!`, `todo!` or `unimplemented!` on a failure input can cause; `expect` states the invariant it relies on.
enforcement: judgment
references:
  - docs/error-handling.md
  - docs/toolchain.md
---

# No panic on a path that can fail

A panic is how Rust reports a bug. A missing file, a malformed line, a refused connection and a user's typo are not bugs; they are the ordinary failures of a program that touches the world, and they are returned as `Result`. This rule holds the line between the two. [`docs/error-handling.md`](../docs/error-handling.md) argues where it falls and why `expect` survives where `unwrap` does not; [`docs/toolchain.md`](../docs/toolchain.md) says how the lints below are switched on.

The rule is inherited from the predecessor's `lex-rust-no-panic-in-production`, which took it from Andrew Gallant's [Using unwrap() in Rust is Okay](https://burntsushi.net/unwrap/): a panic is acceptable when it signals a violated invariant, and wrong when it signals a failure the caller could have handled.

## Conditions

1. **No `unwrap` or `unwrap_err` on a `Result` or `Option` outside test code.** Decided by Clippy's `clippy::unwrap_used`, from the `restriction` group, denied with `allow-unwrap-in-tests = true` in `clippy.toml`. The lint fires on every `unwrap`, including the ones on an invariant, and that is the point: the invariant case is `expect` (condition 2), so an `unwrap` that survives is one nobody justified.

2. **An `expect` names the invariant that makes it unreachable, and the invariant holds.** Decided by a reviewer. The message reads as a statement of what the code guarantees ("the pattern is a literal checked by a test"), not as a description of the failure ("failed to parse"). An `expect` on a value that comes from a file, the network, the environment, a user or another process is a condition 1 finding wearing a message. `clippy::expect_used` is not required, because it would forbid the case this condition allows.

3. **No `panic!`, `todo!` or `unimplemented!` outside test code.** Decided by `clippy::panic`, `clippy::todo` and `clippy::unimplemented`, all `restriction`, denied with `allow-panic-in-tests = true`. An `unreachable!` is allowed and read by a reviewer under condition 2: it carries the same claim as an `expect` and owes the same justification.

4. **A public function of a library that can still panic says when, under a `# Panics` heading in its documentation.** Decided by `clippy::missing_panics_doc`, from the `pedantic` group. The panics conditions 2 and 3 allow are bugs in the caller's use of the function — an index out of range, a precondition broken — and the caller can only avoid one it was told about.

## Where this stops

**Test code, examples and build scripts are out of scope.** In a test a panic is the failure report, and `#[should_panic]` exists for exactly that. The `allow-*-in-tests` settings carve the `#[cfg(test)]` code and `#[test]` functions out; a `build.rs` and an `examples/` target are separate targets, linted or not as the project chooses.

**`main` may end the process on an error, but by returning it.** `fn main() -> Result<(), E>` prints the error and exits non-zero, which is everything a panic would have done, without the backtrace that tells the user the program is broken. A binary's top level is the one place an opaque error belongs, and [`error-types.md`](error-types.md) says so for the error type.

**Indexing and arithmetic are not read here.** `v[i]` panics on an out-of-range index and `a + b` panics on overflow in a debug build and wraps in release. Both are real, and `clippy::indexing_slicing` and `clippy::arithmetic_side_effects` decide them, but denying either across a crate rewrites every loop over a slice for no finding, so this rule does not require them. `reviewing-rust` reads an index or a sum on a value input can reach.

**A panic inside a dependency is not this crate's.** The rule binds the code under review. A library that panics on input this crate passes it is a defect to report upstream, and a reason to validate the input first, not a reason to wrap every call in `catch_unwind`.

**`catch_unwind` is not a way to satisfy this rule.** It exists for a thread or FFI boundary that must not unwind ([`ffi.md`](ffi.md), condition 4), and catching a panic to turn it into an error reintroduces the failure this rule asked to be returned in the first place.
