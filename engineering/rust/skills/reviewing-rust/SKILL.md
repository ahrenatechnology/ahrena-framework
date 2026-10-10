---
name: reviewing-rust
description: Use when a change under review edits Rust (.rs) and the question is what a Rust reader would catch - an unwrap or expect on a path that can fail, an unsafe block that does not justify itself, an as cast that truncates, a clone that hides a design problem, a Result swallowed, a public surface that leaks or over-constrains. Reads the routed files against the conditions below; every finding names the condition.
type: skill
clade: engineering
subclade: quality
references:
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Rust

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold in any language. The Rust compiler and the borrow checker have already decided more than most languages' do. This skill reads what is left to a Rust reader: the panics a library should not take, the `unsafe` that has to earn its place, the ownership choices the compiler accepts but a reader questions, and the API surface.

The conditions are checklists in `references/`, identified by a prefix and a number. A finding cites the identifier. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `rust` route on the changed `.rs` files. Those are the files this skill reads.

Read whether the crate is a library or a binary (`Cargo.toml`, `lib.rs` vs `main.rs`): a `panic!` or an `unwrap` that is acceptable in a top-level binary is a defect in a library others depend on. Read the project's Clippy configuration and whether CI runs `cargo clippy -- -D warnings`: a lint it enforces — `clippy::unwrap_used`, `clippy::as_conversions` — is settled, and not reported again. Read `#![forbid(unsafe_code)]` or its absence. A green Clippy decides what it covers.

## 2. Open the checklists the change calls for

| What the change touches | Reference |
|---|---|
| an `unwrap`, `expect`, `panic!`, `unsafe`, an `as` cast, an array index, arithmetic | `references/panics-and-safety.md` |
| a `clone`, a borrow, a lifetime, `Rc`/`RefCell`/`Arc`/`Mutex`, a `Send`/`Sync` boundary | `references/ownership-and-concurrency.md` |
| a `Result`/`Option` handled, an error type, a `pub` item, a trait, a generic bound | `references/errors-and-surface.md` |

## 3. Read beyond the hunk

Follow each changed item to its callers and to what it borrows from. Whether an `unwrap` is safe is decided by what the function it calls can return, which its signature and body show. Whether a lifetime is right is decided by what outlives what. Read the base revision before calling a line wrong.

## 4. Apply the routed conditions

Work condition by condition. Give the scenario in Rust terms: the input or state, the panic, the truncation, or the needless allocation, and what it should have been. A condition whose answer is a project convention the repository does not state is a `question`.

Read each condition's `Exempt` line. An `unwrap` on an invariant the code guarantees, an `unsafe` with a correct safety comment, a `clone` that is genuinely cheapest — each is correct, and reporting it costs the reviewer's credit.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the condition identifier and a correction that is an instruction.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Length, nesting, duplication, a premature trait with one implementor: those are `reviewing-diffs` and the fundamentals rules.

**What the compiler already rejects.** A use-after-move, an aliased mutable borrow, a missing lifetime: the borrow checker decides these and the change would not compile. This skill reads what compiles and is still wrong.

**Security of the change.** Untrusted input reaching a command or a query, a secret, deserialisation of hostile data: that is the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`).

**Another language.** A `.py`, `.ts` or `.go` file in the same change is read by that language's skill.
