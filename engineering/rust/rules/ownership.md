---
id: ownership
type: rule
clade: engineering
subclade: rust
title: Borrow what is only read, own what is kept
statement: Rust borrows a value it only reads, clones only what it must own, and adds no `Rc`, `Arc` or `RefCell` to quiet the borrow checker.
enforcement: judgment
references:
  - docs/api-design.md
  - docs/toolchain.md
---

# Borrow what is only read, own what is kept

The borrow checker decides whether a program is memory-safe. It does not decide whether the program asked for the right thing: a function that takes ownership of a value it only reads compiles, and so does the `.clone()` its caller then writes to keep using the value. Each is a copy nobody needed, and a signature that asks for more than it uses forces that copy on every caller. This rule holds the choices the compiler accepts and a reader questions. [`docs/api-design.md`](../docs/api-design.md) argues the shape of a parameter list.

Inherited from the predecessor's `lex-rust-ownership-borrowing`, which drew on the Rust book's chapters on ownership, references and lifetimes. The source's own first condition — at most one mutable reference or any number of shared ones — is the borrow checker's rule and cannot be broken by code that compiles, so it is not restated here.

**What the specification says.** Ownership, borrowing and moves are the language's own semantics, and the borrow checker enforces them; nothing below restates what it decides. Condition 5 rests on [Lifetime elision](https://doc.rust-lang.org/reference/lifetime-elision.html). Conditions 1 to 3 are not about soundness but about what a signature asks of its caller, which the API Guidelines address in [C-CALLER-CONTROL](https://rust-lang.github.io/api-guidelines/flexibility.html#c-caller-control) and [C-GENERIC](https://rust-lang.github.io/api-guidelines/flexibility.html#c-generic), and which this rule follows.

## Conditions

1. **A parameter that is only read is borrowed as the most general slice or reference: `&str`, `&[T]`, `&Path`, not `&String`, `&Vec<T>`, `&PathBuf`.** Decided by Clippy's `clippy::ptr_arg`, in the default `style` group, denied.

2. **A parameter taken by value is consumed: moved, stored or returned.** Decided by `clippy::needless_pass_by_value`, from the `pedantic` group, denied. A `String` parameter the body only reads is a `&str` parameter that cost every caller an allocation.

3. **No clone or conversion to owned of a value that is dropped, or only borrowed, right after.** Decided by `clippy::unnecessary_to_owned`, in the default `perf` group, and `clippy::redundant_clone`, from the `nursery` group, both denied. The nursery lint has had false positives, which is why it sits there; the condition stands and a reviewer settles a disputed case. A clone that remains is either cheap by construction — a `Copy` type, an `Rc` or `Arc` handle — or the simplest correct option on a path the profile does not show.

4. **`Rc`, `Arc`, `RefCell`, `Mutex`, and a clone whose copy and original both stay in use, are introduced for shared ownership or shared mutation the design has, not to make a borrow error go away.** Decided by a reviewer. A clone that exists so a value can be borrowed in two places at once has duplicated state to dodge the checker, and the next change to one copy forgets the other. A `RefCell` that exists so two `&mut` borrows compile moves the aliasing error from compile time to a runtime panic; an `Rc` that exists so a struct need not carry a lifetime moves a design question into a reference count. Each has a legitimate use — a graph, a shared cache, state shared across threads — and the reviewer asks which one this is.

5. **No explicit lifetime that elision would infer.** Decided by `clippy::needless_lifetimes`, in the default `complexity` group, denied.

## Where this stops

**Owned types in a struct are not a finding.** A struct that holds a `String` rather than a `&'a str` costs a copy and gains a type with no lifetime parameter, which every user of the struct appreciates. The rule reaches parameters and clones, not the choice to own data that is kept; the predecessor's advice to prefer owned fields in ordinary data structures stands.

**Generic parameters are not required.** `impl AsRef<Path>` accepts more callers than `&Path` and costs a monomorphised copy per type. [`docs/api-design.md`](../docs/api-design.md) says when that trade is worth it; this rule only asks that a borrowed parameter not be a borrowed owner.

**Performance is not measured here.** A clone in a hot loop is a performance question, and `docs/performance.md` says to profile before rewriting. The conditions above are the cases where the clone or the ownership is visibly unneeded, whatever it costs.

**`mut` on a binding that is never mutated is rustc's.** The `unused_mut` lint warns by default, and the project's `-D warnings` in CI denies it with everything else.
