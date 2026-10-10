# Rust panics and safety

Opened by step 2 of `SKILL.md` when the change touches `unwrap`, `expect`, `panic!`, `unsafe`, an `as` cast, an index or arithmetic. Each condition gives the state, how it is detected, what exempts it, and the correction.

### RS-1 `unwrap` or `expect` on a fallible path

- **State:** `.unwrap()`, `.expect()`, `.unwrap_err()` or indexing (`v[i]`) on a `Result`/`Option`/slice that can be `Err`/`None`/out of bounds from real input — a parse, a lookup, an environment read, a user-supplied index.
- **Detect:** read what the receiver can return. In a library, every `unwrap` reachable from a public function is a panic the caller cannot catch cleanly.
- **Exempt:** a value a prior line provably establishes (a regex literal compiled once, a constant index into a known-length array), ideally with `expect` carrying the invariant as its message; a binary's top level where a panic is the chosen failure.
- **Correct:** propagate with `?`; handle with `match`/`if let`; `.get(i)` for a checked index; `unwrap_or`/`ok_or` for a default or a converted error.

### RS-2 `panic!`, `assert!` or `unreachable!` on reachable input

- **State:** `panic!`, `todo!`, `unimplemented!`, `assert!` or `unreachable!` on a condition ordinary input can trigger, in library code.
- **Detect:** read what reaches it. `unreachable!` on a case that is in fact reachable is the trap.
- **Exempt:** a genuine invariant that only a programming error violates; `assert!` guarding an internal precondition; a binary's fatal path.
- **Correct:** return a `Result` with a real error; reserve these macros for impossible states, and say why in the message.

### RS-3 An `unsafe` block that does not justify itself

- **State:** an `unsafe` block or `unsafe fn` with no `// SAFETY:` comment stating the invariants that make it sound; a raw-pointer deref, a `transmute`, a `get_unchecked`, a `from_utf8_unchecked`, an FFI call whose preconditions are not argued.
- **Detect:** every `unsafe` the change adds. The compiler stops checking inside it; the comment is the only remaining record of why it is correct.
- **Exempt:** none from the comment. The `unsafe` itself is exempt when it is genuinely necessary and the safety argument holds.
- **Correct:** add the `// SAFETY:` comment proving each invariant; or replace with the safe API (`get`, `from_utf8`, a checked conversion) when the unsafe buys nothing measured.

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
