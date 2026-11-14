---
id: ffi
type: rule
clade: engineering
subclade: rust
title: Foreign functions stay behind a safe wrapper
statement: Rust exposes no foreign function directly, passes C only FFI-safe types, frees C memory with C's own function, and lets no panic reach a C caller.
enforcement: judgment
references:
  - docs/api-design.md
  - docs/toolchain.md
---

# Foreign functions stay behind a safe wrapper

A function declared in an `unsafe extern` block is a promise Rust cannot check: its signature is whatever the author typed, and nothing compares it with the C header. The conditions below keep that promise in one module, behind functions whose callers never write `unsafe`. Every `unsafe` block they contain is also held by [`unsafe-code.md`](unsafe-code.md); this rule adds what is particular to crossing into another language. [`docs/api-design.md`](../docs/api-design.md) argues the wrapper's shape.

Inherited from the predecessor's `lex-rust-ffi-safety`, which drew on the first edition of the Rust book. That edition predates three changes that alter the rule, and the conditions below follow the current language: since the 2024 edition an `extern` block must be written `unsafe extern`; since Rust 1.64 the C types live in `core::ffi` and need no `libc`; and since Rust 1.81 a panic unwinding out of an `extern "C"` function aborts the process instead of being undefined behaviour.

**What the specification says.** External blocks, and the `unsafe` the 2024 edition requires on them, are in [External blocks](https://doc.rust-lang.org/reference/items/external-blocks.html) and RFC 3484, [unsafe extern blocks](https://rust-lang.github.io/rfcs/3484-unsafe-extern-blocks.html). The C layout of condition 2 is [The C representation](https://doc.rust-lang.org/reference/type-layout.html#the-c-representation). Condition 4 rests on [Unwinding](https://doc.rust-lang.org/reference/items/functions.html#unwinding): a Rust panic that reaches a non-unwinding ABI boundary such as `extern "C"` is turned into an abort, while a foreign unwind entering one is undefined behaviour ([Unwinding across FFI boundaries](https://doc.rust-lang.org/reference/panic.html#unwinding-across-ffi-boundaries)); RFC 2945, [C-unwind ABI](https://rust-lang.github.io/rfcs/2945-c-unwind-abi.html), introduced the ABI that permits unwinding.

## Conditions

1. **A crate's public API exposes no foreign function, only a safe Rust function that calls it.** Decided by a reviewer. The declaration inside `unsafe extern` is private to its module, and the `pub fn` beside it checks every precondition the C function has — a non-null pointer, a buffer at least as long as the length passed, a string terminated by a nul — and converts every result. A `*-sys` crate is the exception by convention: its job is to publish the raw declarations, and the safe crate built on it is the one this condition reads.

2. **Every type crossing the boundary has a layout C agrees with: a `core::ffi` C type, a `#[repr(C)]` struct or enum, a raw pointer, or a type the standard library documents as FFI-safe.** Decided by rustc's `improper_ctypes` and `improper_ctypes_definitions`, both warn-by-default and denied. A Rust `i32` for a C `int` compiles and is right on most targets; `core::ffi::c_int` is right on all of them, and the reader does not have to know which targets those are. Neither lint catches that substitution, because `i32` is FFI-safe; it is the reviewer's half of this condition.

3. **Memory that C allocated is released by the matching C function, from the `Drop` of the Rust type that owns it.** Decided by a reviewer. Rust's allocator did not allocate it and must not free it: turning the pointer into a `Box` or a `Vec` hands it to the wrong allocator, and forgetting it leaks. The owning type holds the pointer privately, frees it once in `drop`, and is neither `Clone` nor `Copy`.

4. **A Rust function called from C does not unwind into it.** Decided by a reviewer. A `pub extern "C" fn` whose body can panic catches the panic with `std::panic::catch_unwind` and returns an error the C side understands. Since Rust 1.81 an uncaught panic there aborts the process rather than corrupting it, which is safe and still takes the caller's whole process down for one failed call. `extern "C-unwind"` is the declared alternative when the foreign side is built to unwind, and the choice is written on the signature where the C side can see it.

## Where this stops

**The signature is not checked against the header.** Nothing in the toolchain compares a hand-written `unsafe extern` declaration with the C function it names. `bindgen` generates the declarations from the header, and when a crate binds more than a handful of functions, generating them is how the mismatch is avoided; when it binds two, a reviewer reading the header is cheaper.

**Thread safety across the boundary is the C library's documentation.** Whether a handle may be used from two threads is a fact about the C library, and it decides whether the Rust wrapper is `Send` or `Sync`. The `unsafe impl` that asserts it is condition 1 of [`unsafe-code.md`](unsafe-code.md), and its `// SAFETY:` comment cites the documentation.

**Calling into C from async code is [`async-blocking.md`](async-blocking.md)'s.** A foreign function that does I/O blocks like any other.

**Rust exported as a C library — `cdylib` or `staticlib` with a hand-written header — is in scope only for condition 4.** Its own surface design is a C API design question, and `cbindgen` is where its header comes from.
