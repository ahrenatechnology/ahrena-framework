---
id: unsafe-code
type: rule
clade: engineering
subclade: rust
title: Unsafe code argues its soundness and stays behind a safe API
statement: Every `unsafe` block says why it is sound in a `// SAFETY:` comment, every `unsafe fn` documents `# Safety`, and no safe API leaks an unchecked invariant.
enforcement: judgment
references:
  - docs/api-design.md
  - docs/toolchain.md
---

# Unsafe code argues its soundness and stays behind a safe API

Inside an `unsafe` block the compiler stops checking five things: dereferencing a raw pointer, calling an `unsafe` function, touching a `static mut`, implementing an `unsafe` trait, and reading a union field. What it stops checking somebody has to argue, and the comment is the only place the argument survives. [`docs/api-design.md`](../docs/api-design.md) explains why the argument belongs at the block and why the invariant must not escape the module that relies on it.

The rule merges the predecessor's `lex-rust-unsafe-isolation`, drawn from TiKV's buffer types and Alacritty's platform code, with the `unsafe` half of `lex-rust-ffi-safety`, drawn from the Rust book's chapter on unsafe code. The FFI half is [`ffi.md`](ffi.md).

## Conditions

1. **Every `unsafe` block and every `unsafe impl` carries a `// SAFETY:` comment directly above it, stating why each operation inside is sound.** Decided by Clippy's `clippy::undocumented_unsafe_blocks`, from the `restriction` group, denied. The comment names the invariant and where it is established: "the index was checked against `len()` on the line above", not "this is safe".

2. **Every public `unsafe fn` and `unsafe trait` documents its contract under a `# Safety` heading.** Decided by `clippy::missing_safety_doc`, which warns by default and is denied. The heading says what the caller must guarantee, because a caller of an `unsafe fn` is writing condition 1's comment and needs something to write it about.

3. **Inside an `unsafe fn`, each unsafe operation is still wrapped in an `unsafe` block.** Decided by rustc's `unsafe_op_in_unsafe_fn`, which warns by default from the 2024 edition and is denied. Without it the whole body is one undocumented block, and condition 1 has nothing to attach to.

4. **A safe function does not let its caller break an invariant that an `unsafe` block relies on.** Decided by a reviewer. A safe `pub fn` that takes an index and passes it unchecked to `get_unchecked` is unsound: undefined behaviour is reachable from safe code, which is the one thing Rust promises cannot happen. The invariant is checked inside the function, or the function is `unsafe` and says so (condition 2). The same holds for a field: a `pub` field that an `unsafe` block trusts is a public way to break it, so such a field is private.

## Where this stops

**This rule does not decide whether `unsafe` was needed.** A `get_unchecked` that saves nothing measurable is still sound when the comment is true. Replacing it with the checked call is a reviewer's suggestion, and `reviewing-rust` makes it when the safe version costs nothing the benchmark can see; [`docs/performance.md`](../docs/performance.md) says what counts as measured.

**The comment is checked for presence, not truth.** `clippy::undocumented_unsafe_blocks` accepts any text after `SAFETY:`. Whether the argument holds is condition 4's reviewer, and for code where it is subtle, Miri: `cargo +nightly miri test` executes the test suite under an interpreter that detects most undefined behaviour the tests reach. Miri is a debugging tool here, named by `debugging-rust`, not a condition, because it needs a nightly toolchain and cannot run code that calls into C.

**`#![forbid(unsafe_code)]` is not required.** It is the right attribute for a crate with no `unsafe`, and `docs/toolchain.md` recommends it. It is not a condition because a crate that needs one block would have to remove it, and the conditions above already hold every block that exists.

**A dependency's `unsafe` is not this crate's.** Choosing a dependency that uses `unsafe` is a supply-chain decision; `ahrena-engineering-security`'s supply-chain review reads it, and `cargo-geiger` counts it.
