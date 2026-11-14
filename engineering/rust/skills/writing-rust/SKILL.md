---
name: writing-rust
description: Use when Rust code is being written or changed - a function, a type, a module, a crate - to implement a behaviour test-first against this plugin's Rust rules and docs. Reads the crate's shape and lint policy, picks dependencies from the recommended list, writes the test red, the code green, refactors, and runs fmt, Clippy, the tests and the Rust hook before handing back.
type: skill
clade: engineering
subclade: rust
references:
  - rules/panics.md
  - rules/unsafe-code.md
  - rules/ffi.md
  - rules/async-blocking.md
  - rules/error-types.md
  - rules/non-exhaustive.md
  - rules/utf8-io.md
  - rules/regex-compilation.md
  - rules/ownership.md
  - rules/strings.md
  - docs/toolchain.md
  - docs/libraries.md
  - docs/error-handling.md
  - docs/async-and-concurrency.md
  - docs/api-design.md
  - docs/testing.md
  - skills/reviewing-rust/SKILL.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
---

# Writing Rust

This skill writes Rust for one behaviour, test first, so that the code that comes out already holds to this plugin's rules rather than meeting them for the first time in review. The order of red, green and refactor is the one `ahrena-engineering-backend:driving-with-tdd` sets for any language; this skill adds what Rust changes about each step. A layer builder that is running that skill reads this one beside it.

## 1. Read the crate before writing in it

Run `ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md` for the component, for the project's words, its sanctioned folders and its test tools.

Then read the crate itself. Whether it is a library or a binary (`src/lib.rs`, `src/main.rs`, `[lib]` and `[[bin]]` in `Cargo.toml`) decides which rules bind it: a library is held to `rules/error-types.md` and `rules/non-exhaustive.md`, a binary is not. Read the `edition` and the `rust-version`: an API stabilised after the MSRV cannot be used, however convenient. Read `[lints]`, `[workspace.lints]` and `clippy.toml`, and compare them with the table in `docs/toolchain.md`. A lint the project has not enabled is still a condition of the rule that names it, so the code is written as though it were on.

Output: library or binary, edition, MSRV, the lints in force, the test runner.

## 2. Name the rules the behaviour will touch

Read the rules the change will meet before writing it, not after.

| The behaviour involves | Rules | Doc |
|---|---|---|
| anything that can fail | `rules/panics.md`, and `rules/error-types.md` in a library | `docs/error-handling.md` |
| `async`, a runtime, a lock or a channel | `rules/async-blocking.md` | `docs/async-and-concurrency.md` |
| a `pub` item of a library | `rules/non-exhaustive.md`, `rules/ownership.md`, `rules/strings.md` | `docs/api-design.md` |
| bytes from a file, stdin, a pipe or a socket | `rules/utf8-io.md` | `docs/performance.md` |
| a regex or a multi-pattern matcher | `rules/regex-compilation.md` | `docs/performance.md` |
| `unsafe`, or a call into C | `rules/unsafe-code.md`, `rules/ffi.md` | `docs/api-design.md` |

Output: the rules and docs this change is held to.

## 3. Choose dependencies from the list, not from memory

Before adding a crate, find the problem in `docs/libraries.md` and take the crate it names, or write down why not. Add it with `cargo add`, which respects the declared `rust-version`. A dependency the project already has for the same problem wins over the list: two HTTP clients in one tree is worse than either.

Output: the crates added, each with the problem it solves.

## 4. Write the test red

Put the test where `docs/testing.md` says it belongs: a unit test in the module's `#[cfg(test)] mod tests` for a domain rule, an integration test under `tests/` for behaviour through the public API, a doc test for an example a caller will read. Name it for the behaviour. Write a test for each error the callers will branch on, and, for code that reads outside data, the invalid-UTF-8 case `rules/utf8-io.md` condition 3 asks for.

```sh
cargo test --all-features <test_name>
```

Confirm it fails for the missing behaviour. In Rust the first red is often a compile error naming the function or variant that does not exist yet; that is a valid red when the error names the missing item and nothing else. A stub that compiles and returns a wrong value gives a clearer red, and a `todo!()` in it is gone before step 6 ends.

Output: the command and the failing test.

## 5. Write the smallest code that turns it green

Write the code against the rules from step 2. The ones a first draft breaks most often:

- An `unwrap` on a value from outside. Return the error with `?`, or use `expect` with the invariant if one exists (`rules/panics.md`).
- `anyhow` or a `String` as a library's error. Define the crate's error enum with `thiserror` (`rules/error-types.md`, `docs/error-handling.md`).
- A `std::fs` call or a `std::sync::Mutex` guard inside an `async fn`. Use the async API or `spawn_blocking`, and drop the guard before the `.await` (`rules/async-blocking.md`).
- A `String` or `&String` parameter that is only read. Take `&str` (`rules/ownership.md`).
- A `.clone()` added to quiet the borrow checker. Restructure the borrow first (`rules/ownership.md` condition 4).
- An `unsafe` block without `// SAFETY:` (`rules/unsafe-code.md`).

Run the test again, and the whole suite.

Output: the command and the passed and failed counts.

## 6. Refactor under green

With the tests green, improve names, split what grew, remove the duplication the change introduced, and run the suite after each step. A refactoring larger than the change follows `ahrena-engineering-quality:refactoring-safely`. Remove any `todo!()` left from step 4.

Output: the suite still green.

## 7. Run the gate

```sh
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
python3 <rust-plugin>/hooks/check-rust.py <crate-dir>
```

Clippy runs with the lints `docs/toolchain.md` lists added on the command line when the project has not configured them (`-W clippy::unwrap_used` and the rest), and every finding on a line this change touched is fixed, not allowed. `<rust-plugin>` is where this plugin is installed, `engineering/rust` in the framework repository. `check-rust.py` decides condition 1 of `rules/error-types.md` and of `rules/async-blocking.md`. A finding on a line the change did not touch is reported in the hand-back, not fixed here.

Output: each command and its result.

## 8. Read the diff as a reviewer will

Read the diff against the checklists of `skills/reviewing-rust/SKILL.md` steps 2 to 4, and correct what they find. This is not the review: it is the writer catching what the reviewer would, so the review spends its round on what only a second reader sees.

Output: the diff, still green, with what step 7 and this step found and what was fixed.

## When this skill does not apply

**Reviewing someone else's Rust.** That is `reviewing-rust`, which reads a diff and writes findings rather than code.

**Diagnosing a failure whose cause is unknown.** That is `debugging-rust`, which ends by handing a reproduced, explained defect to this skill to fix.

**Deciding what to build or in which layer.** The plan and the layer order are the orchestrator's — Apollo, Iris, Clio or Athena — and this skill writes one behaviour inside whatever layer it is given.

**A one-line change with an existing test.** Running the test before and after is enough; the full procedure is for a behaviour that does not exist yet.
