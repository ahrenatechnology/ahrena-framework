# Rust panics and safety

Opened by step 2 of `SKILL.md` when the change touches an `as` cast, arithmetic or a fallible call whose result is dropped. Each condition gives the state, how it is detected, what exempts it, and the correction.

A panic on a path that can fail and an `unsafe` block are not here: they are `rules/panics.md` and `rules/unsafe-code.md`, cited by their conditions. RS-1, RS-2 and RS-3 were retired into those rules and their identifiers are not reused.

### RS-4 An `as` cast that truncates, wraps or loses sign

- **State:** `as` between numeric types that can lose data — `i64 as i32`, `usize as u32`, `u64 as f64`, `f64 as i32` (which saturates), a cast on a length or an id.
- **Detect:** each `as` on a value whose range can exceed the target. `as` never errors; it silently truncates or wraps.
- **Exempt:** a cast the code proves is in range, with a comment; a deliberate bit-level truncation.
- **Correct:** `TryFrom`/`try_into` and handle the error; `u32::try_from(x)?`; a widening `From` when it cannot lose data.

### RS-5 Arithmetic that can overflow silently

- **State:** `+`, `-`, `*` on integers that can overflow with real input, where release builds wrap (no panic) — a sum of sizes, a multiply for an allocation, a subtraction that can go below zero on an unsigned type.
- **Detect:** read the operands' ranges. Debug panics, release wraps, so tests pass and production corrupts.
- **Exempt:** values provably bounded, or a type chosen wide enough with a comment.
- **Correct:** `checked_add`/`checked_mul` and handle `None`; `saturating_*` or `wrapping_*` when that is the intent, named so.

### RS-6 A `Result` or must-use value ignored

- **State:** a `Result` dropped with `let _ =` where the error matters, a `#[must_use]` value discarded, or `.ok()` used to throw away an error that should be handled or logged.
- **Detect:** each fallible call whose outcome is dropped. The compiler warns on a bare unused `Result`, so the suppressed ones (`let _ =`) are where the reader looks.
- **Exempt:** a genuinely best-effort call whose failure is meant to be ignored, with `let _ =` making it visible and a comment.
- **Correct:** propagate with `?`, handle with `match`, or log; reserve `let _ =` for the deliberate, commented case.
