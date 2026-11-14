---
name: debugging-rust
description: Use when Rust misbehaves and the cause is not known - a panic, a wrong result, a hang or deadlock in async code, a crash or suspected undefined behaviour, a flaky test, a build or dependency error, a performance regression. Reproduces the symptom as a failing test, gathers the evidence the symptom calls for with Rust's own tools, names the cause, and hands a fix test-first to writing-rust.
type: skill
clade: engineering
subclade: rust
references:
  - rules/panics.md
  - rules/unsafe-code.md
  - rules/async-blocking.md
  - docs/async-and-concurrency.md
  - docs/testing.md
  - docs/performance.md
  - skills/writing-rust/SKILL.md
---

# Debugging Rust

A defect is fixed once it is understood, and it is understood once it can be made to happen on demand. This skill gets a Rust defect from a report to a failing test and a named cause, using the evidence each kind of symptom leaves, and then hands the fix to `skills/writing-rust/SKILL.md`. The procedures per symptom are in `references/symptoms.md`; the steps below say when to open it.

## 1. Classify the symptom

Put the report in one of these, because each leaves different evidence:

- **a panic** — a message, a location, maybe a backtrace;
- **a wrong result** — the program runs and says the wrong thing;
- **a hang** — an async service that stops answering, a test that never ends, a deadlock;
- **a crash or undefined behaviour** — a segfault, a corrupted value, a result that changes between builds or runs;
- **a flaky test** — passes and fails on the same code;
- **a build or dependency failure** — a compile error that appeared without a code change, a feature that is or is not enabled, a duplicate type from two versions of one crate;
- **a performance regression** — the same work, slower.

Output: the class, and the report's evidence verbatim.

## 2. Reproduce it as a failing test

Write the smallest test that shows the symptom, in the place `docs/testing.md` gives for its kind: a unit test when the cause is inside one module, an integration test when it is only visible through the public API. A hang is reproduced with a timeout around the test (`tokio::time::timeout` for async code) so the test fails rather than never ends; a performance regression with a `criterion` benchmark comparing the two revisions.

```sh
cargo test --all-features <test_name> -- --nocapture
```

If it does not reproduce, the difference between the report's environment and this one is the first lead: the feature set, the target, the release profile (overflow checks and `debug_assert!` are off in release), the data, the thread count. A defect that only reproduces in release is often an integer overflow that wrapped there and panicked in debug.

Output: the failing test, or the environment difference still being chased.

## 3. Gather the evidence the class calls for

Open `references/symptoms.md` at the class from step 1 and follow it. It names, per class, the tools that read Rust's evidence — `RUST_BACKTRACE`, `tokio-console`, Miri and the sanitizers, `cargo tree`, `cargo expand`, `git bisect` with a test, a profiler — what each one shows, and the rule whose violation is the commonest cause of that class:

- a panic on outside input is usually `rules/panics.md`;
- a stalled async service is usually `rules/async-blocking.md`, or two locks taken in opposite orders (`docs/async-and-concurrency.md`);
- undefined behaviour is, in safe-looking code, always an `unsafe` block, its own or a dependency's, and `rules/unsafe-code.md` condition 4 is where to look first.

Output: what each tool showed.

## 4. Name the cause, and prove it

State the cause as a claim the evidence supports: "`parse_header` slices at byte 4, inside `ç`, when the name is not ASCII". Then prove it: change the one thing the claim says is wrong, in a scratch edit, and watch the test from step 2 go green; revert the edit. A cause that cannot be proved this way is a hypothesis, and step 3 continues.

If the cause is in a dependency, reproduce it against the dependency alone, check its issue tracker and changelog for the version in the lock file, and decide between upgrading, working around it in this crate, and reporting it upstream.

Output: the cause, and the scratch edit that proved it.

## 5. Hand the fix to writing-rust

Run `skills/writing-rust/SKILL.md` from its step 5, with the test from step 2 as the red test. The fix is the smallest change that makes it green. When the cause was a rule violation, check whether the rule's detector would have caught it — a Clippy lint the project has not enabled, a condition of `hooks/check-rust.py` — and say so in the hand-back, because enabling the detector stops the next one.

Output: the test, the fix, the cause, and whether a detector would have caught it.

## When this skill does not apply

**A compile error in code being written.** The compiler's message is the diagnosis; that is part of `writing-rust`. This skill takes a build failure only when it appeared without the code changing.

**A known defect with a known fix.** A review finding or a reproduced bug with the cause named goes straight to `writing-rust`.

**A slow program with no earlier, faster revision.** That is optimisation, not a regression; `docs/performance.md` says how to measure where the time goes.

**Production incidents.** Reading a live service's logs, metrics and traces to find which request failed is operations work, and `ahrena-engineering-observability`'s disciplines say what the service should have emitted; this skill starts once the failure can be reproduced.
