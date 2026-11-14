---
id: error-types
type: rule
clade: engineering
subclade: rust
title: A library returns its own error type
statement: A Rust library's public functions fail with its own error type, never `anyhow`, a boxed `dyn Error` or a string; it is `Send + Sync` and keeps its source.
enforcement: judgment
references:
  - docs/error-handling.md
  - docs/toolchain.md
---

# A library returns its own error type

A caller decides what to do about a failure — retry, fall back, map it to an HTTP status, show it to a person — by looking at what kind of failure it is. An error type the caller cannot match on takes that decision away: an `anyhow::Error` or a `Box<dyn Error>` can only be printed or downcast by guessing, and a `String` can only be printed. Inside an application that is fine, because the application is the last caller. On a library's surface it is a decision made for every caller the library will ever have, and changing it later is a breaking release. [`docs/error-handling.md`](../docs/error-handling.md) argues the split between libraries and applications and the choice of `thiserror`.

This rule merges two lexis of the predecessor that stated it twice: `lex-rust-library-error-types`, drawn from Meilisearch's mapping of errors to HTTP codes and ripgrep's regex error types, and `lex-rust-library-must-define-error-type`, drawn from Andrew Gallant's [Error Handling in Rust](https://burntsushi.net/rust-error-handling/), whose advice to library authors is to define their own error type and implement `std::error::Error`.

## Conditions

1. **No public function, method or type alias of a library crate fails with an opaque error.** Decided by `hooks/check-rust.py`. Opaque is: `anyhow::Result`, `anyhow::Error`, `eyre::Result`, `eyre::Report` or `color_eyre`'s; a `Box<dyn Error>` with any bounds, written out or through a type alias in the same file; `String`, `&str` or `&'static str`. Only the error channel is read — the `E` of an outermost `Result<T, E>`, or anyhow's and eyre's own `Result` — so a function that returns a boxed error as its value, or a callback type whose own return is boxed, is not a finding. A `Result` imported from `anyhow` is anyhow's. Public is bare `pub`: `pub(crate)`, `pub(super)` and private items are not the surface, and neither is an item marked `#[doc(hidden)]`. Library is a file under `src/` of a crate that has a `src/lib.rs` or a `[lib]` table, other than `src/main.rs` and `src/bin/`. Test code is not read.

2. **The library's error type implements `std::error::Error`, `Debug` and `Display`, and is `Send + Sync + 'static`.** `Error` is decided by the compiler at the first `?` that converts into a caller's `Box<dyn Error>`; the auto traits are decided by a test the crate carries, `fn assert_send_sync<T: Send + Sync + 'static>() {}` called with the error type, because nothing else fails when a later variant wraps an `Rc`. Without them, the error cannot cross a thread or an `.await` and cannot be boxed by a caller who wants to. The Rust API Guidelines call this C-GOOD-ERR.

3. **A conversion into the library's error keeps the error it converts.** Decided by Clippy's `clippy::map_err_ignore`, from the `restriction` group, denied. `.map_err(|_| Error::Parse)` drops the cause a caller would need to diagnose the failure; the variant holds it, as `#[source]` or `#[from]` with `thiserror`, and `Error::source` returns it.

## Where this stops

**A binary's top level is out of scope, by construction.** `src/main.rs`, `src/bin/` and the functions a binary alone uses are the last caller, and `anyhow` with `.context()` is the right tool there. A module declared only from `main.rs` but placed elsewhere under `src/` of a crate that also has a library is read as library source; the fix is to move it, or to make it `pub(crate)`, which it should have been.

**Cross-file aliases are not followed.** `type BoxError = Box<dyn Error + Send + Sync>` declared in `lib.rs` and used as the error of a function in another file is not seen; within one file it is. Neither is a re-export (`pub use anyhow::Result`) or a macro that generates the signature.

**A middleware that wraps errors it does not own is a judgment call the hook cannot make.** Tower and the crates built on it use a boxed error deliberately, because a layer's error is whatever the service inside it fails with, and no enum of the layer's can name it. Such a crate excludes the file by path and writes down why. In 310 crates of a local Cargo registry, about 415,000 lines, condition 1 found 18 functions, every one of them an opaque error on a public library function by this definition: 7 returning a string, 11 returning `anyhow` from build-time helper libraries. None was a misreading of a signature.

**The error type's variants are not designed here.** How many variants, whether to expose an `ErrorKind`, whether the type is an enum or a struct with a kind: `docs/error-handling.md` discusses the trade. Whether a public error enum can grow without a breaking release is [`non-exhaustive.md`](non-exhaustive.md).

**This rule does not reach a library's private plumbing.** Inside the crate, an internal helper may return whatever is convenient as long as the public function converts it before it crosses the surface.
