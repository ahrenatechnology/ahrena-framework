---
id: api-design
type: doc
clade: engineering
subclade: rust
title: Designing a Rust public surface
summary: What a Rust function should accept and return, when to use generics and when trait objects, how a trait is shaped, how a type stays evolvable under semver, and how unsafe and foreign code is wrapped so callers never see it.
references:
  - rules/ownership.md
  - rules/strings.md
  - rules/non-exhaustive.md
  - rules/unsafe-code.md
  - rules/ffi.md
  - rules/error-types.md
  - docs/architecture.md
---

# Designing a Rust public surface

This is the companion to five rules that are each about one part of a crate's surface: [`ownership.md`](../rules/ownership.md) and [`strings.md`](../rules/strings.md) for what a function accepts, [`non-exhaustive.md`](../rules/non-exhaustive.md) for how a type grows, and [`unsafe-code.md`](../rules/unsafe-code.md) and [`ffi.md`](../rules/ffi.md) for what a safe surface hides. It merges three of the predecessor's codex: `codex-rust-api-design`, built on Andrew Gallant's design of `regex`, `csv` and `bstr`; `codex-rust-traits-generics`, from the Rust book; and the versioning half of `codex-rust-oss-maintenance`. Where the [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) have an item for a point, its identifier is given.

**What the specification says, and whose guidance fills the rest.** The language defines visibility ([Visibility and privacy](https://doc.rust-lang.org/reference/visibility-and-privacy.html)), traits and their coherence ([Traits](https://doc.rust-lang.org/reference/items/traits.html); [Trait implementation coherence](https://doc.rust-lang.org/reference/items/implementations.html#trait-implementation-coherence)), dyn compatibility ([Dyn compatibility](https://doc.rust-lang.org/reference/items/traits.html#dyn-compatibility)) and `impl Trait` ([Impl trait type](https://doc.rust-lang.org/reference/types/impl-trait.html)); Cargo's [SemVer guide](https://doc.rust-lang.org/cargo/reference/semver.html), refining RFC 1105, says which changes break callers. How to shape a surface within that is the community's, and this plugin follows the Rust API Guidelines as written. It departs in one place: C-DEBUG asks every public type to implement `Debug`, and a type that holds a secret implements it by hand, redacting, rather than deriving it ([`rules/redaction.md`](../rules/redaction.md)), which keeps the guideline's letter and changes its usual form. How the surfaces of several crates compose, and how SOLID and inversion of control are written in Rust, is [`architecture.md`](architecture.md).

## What a function accepts

**Borrow what it only reads, as the widest borrowed form.** `&str` accepts a literal, a `String` and a slice of either; `&String` accepts only a `String`. `&[T]` accepts a `Vec`, an array and a slice. `&Path` accepts a `PathBuf`, an `OsStr` and a `&str` via `as_ref`. [`rules/ownership.md`](../rules/ownership.md) conditions 1 and 2 hold the line, and Clippy decides both.

**Take ownership when the function keeps the value.** A constructor that stores a name takes `String`, or `impl Into<String>`, so a caller who already has a `String` moves it rather than having it copied. Taking `&str` and calling `.to_string()` inside forces the copy on everyone. This is C-CALLER-CONTROL: the caller, who knows whether it has an owned value, decides where the copy happens.

**Generic parameters widen what is accepted at a price.** `fn open(path: impl AsRef<Path>)` takes a `&str`, a `String`, a `PathBuf` and a `&Path`, and the compiler generates one copy of the function per type it is called with. For a small function on a public surface that is the right trade (C-GENERIC); for a large one, the generic wrapper calls a private non-generic inner function so only the conversion is duplicated, which is how the standard library's `fs::read` is written.

**Offer a buffer-reusing variant where the hot path needs it.** A function that returns a fresh `Vec` per call is the convenient form; one that writes into a `&mut Vec<u8>` the caller clears and reuses is the fast form. `csv`'s `read_record(&mut record)` beside its iterator, and `bstr`'s `for_byte_line` beside `byte_lines`, are the pattern. Both forms are public; the convenient one is implemented with the fast one.

## What a function returns

**A concrete type when the caller benefits from knowing it, `impl Trait` when it is a detail.** An iterator adapter chain is a detail — `impl Iterator<Item = &str>` — and naming it would freeze the implementation. A type with methods the caller wants is not: return the struct.

**A builder when construction has more than a few independent options.** `RegexBuilder::new(pattern).case_insensitive(true).build()` lets options be added without breaking a constructor's signature. The predecessor set the threshold at "more than two or three" options; it is not measured, and the real test is whether a new option would change an existing signature. If it would, a builder.

## Generics, trait objects and traits

**Static dispatch by default.** A generic `fn run<M: Matcher>(m: &M)` is compiled per type and inlined; a trait object `&dyn Matcher` is one function called through a vtable. The generic is faster and costs compile time and binary size; the trait object is smaller and is the only option for a collection of different types. ripgrep's `grep-searcher` is generic over its `Matcher` and `Sink` traits, so each regex engine and each output format is compiled into the search loop rather than called through it.

**Associated types when there is one answer per implementing type, generic parameters when there are many.** `Iterator::Item` is associated because a type iterates over one kind of item; `From<T>` is generic because `String` converts from `&str`, from `char` and from `Box<str>`.

**Closures by the least demanding trait.** Accept `FnOnce` if the closure is called once, `FnMut` if called repeatedly by one caller, `Fn` only if it must be shareable. Each accepts more closures than the next. Document whether it is called zero, one or many times, which the signature does not say.

**A trait meant to be implemented outside the crate is a promise too.** Adding a method without a default breaks every implementor. A trait meant only to be used, not implemented, is sealed (C-SEALED): a public trait with a supertrait from a private module, so outside crates can call it and cannot implement it, and the crate can add methods freely.

**Object safety is a property to decide, not discover.** A trait with a generic method or a method returning `Self` cannot be made into `dyn Trait`. If callers will want trait objects, check it with a `fn _assert(_: &dyn Trait) {}` in the crate's tests, so the change that breaks it fails there.

**The orphan rule and newtypes.** A crate may implement a trait for a type only if it owns one of them. To implement a foreign trait for a foreign type, wrap the type: `struct Wrapper(Vec<u8>)`. The same newtype is the tool for giving a primitive a meaning (`struct UserId(u64)`) so two ids cannot be swapped by accident (C-NEWTYPE).

## Keeping a surface evolvable

Under semantic versioning every `pub` item is a promise kept until the next major release. Three habits keep the promises small.

**Make public only what callers need.** `pub(crate)` is the default for anything not in the documented API; a `pub` item in a private module is still reachable through any public re-export, so the module structure is not a substitute for the keyword.

**Make growing types non-exhaustive, or give them private fields** (C-STRUCT-PRIVATE), so a new variant or field is a minor release. [`rules/non-exhaustive.md`](../rules/non-exhaustive.md) states it, and `cargo semver-checks` in the release pipeline checks the rest.

**Keep a changelog and decide what a breaking change is before making one.** The predecessor's maintenance codex asked for Keep a Changelog and strict semver, from Andrew Gallant's [My FOSS Story](https://burntsushi.net/foss/); both stand. Its advice on maintainers' boundaries, issue templates and saying no to features is about running an open-source project rather than writing Rust, and is not carried here.

## Wrapping unsafe and foreign code

`unsafe` is a property of a block, but soundness is a property of a module. A `get_unchecked` is sound only if every path to it has checked the index, and every path means every function in the module that can touch the field the index came from. So the unit of encapsulation is the module: the unsafe operation, the invariant it relies on, and every function that could break that invariant live together, with the invariant's fields private ([`rules/unsafe-code.md`](../rules/unsafe-code.md) condition 4). Outside that module the API is safe and the caller cannot get it wrong.

TiKV's buffer types and Alacritty's platform layers, which the predecessor cited, follow the shape. For foreign code the shape is the same with one more layer: a `-sys` crate publishes the raw declarations, generated with `bindgen`; the safe crate above it owns each foreign resource in a Rust type whose `Drop` frees it with the foreign library's function, checks every precondition before the call, and converts every result ([`rules/ffi.md`](../rules/ffi.md)). The caller of the safe crate writes no `unsafe` and cannot leak, double-free or pass a dangling pointer.

## Documentation is part of the surface

Every public item has a doc comment; `#![warn(missing_docs)]` in `lib.rs` makes the compiler list the ones that do not. A function that returns `Result` says when under `# Errors`, one that can panic says when under `# Panics` ([`rules/panics.md`](../rules/panics.md) condition 4), an `unsafe fn` says what the caller must guarantee under `# Safety`. The examples are doc tests and run with the test suite, which [`testing.md`](testing.md) covers.

## Where this stops

**Applications have little surface.** A binary's internal modules are not a semver promise; the habits above are worth less there, and the rules that encode them are scoped to libraries.

**Macros are not covered.** A procedural macro is its own API, with hygiene and error-reporting questions this page does not reach.

**Naming conventions are the API Guidelines' C-CASE, C-CONV and C-GETTER**, followed as written; Clippy's default `style` group enforces most of them.
