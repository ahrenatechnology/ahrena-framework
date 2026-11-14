---
name: reviewing-rust
description: Use when a change under review edits Rust (.rs) and the question is what a Rust reader would catch - an unwrap or expect on a path that can fail, an unsafe block that does not justify itself, a blocking call in async code, an opaque library error, a module cycle or a dependency against the layers, a unit with no test beside it, a secret or a dependency's error reaching an output, a pattern imported from another language, an as cast that truncates, a clone that hides a design problem, a Result swallowed, a public surface that leaks or over-constrains. Reads the routed files against this plugin's Rust rules and the conditions below; every finding names the rule condition or the checklist condition.
type: skill
clade: engineering
subclade: quality
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
  - rules/dependency-direction.md
  - rules/unit-tests.md
  - rules/redaction.md
  - docs/architecture.md
  - docs/toolchain.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Rust

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold in any language. The Rust compiler and the borrow checker have already decided more than most languages' do. This skill reads what is left to a Rust reader: the panics a library should not take, the `unsafe` that has to earn its place, the ownership choices the compiler accepts but a reader questions, and the API surface.

The conditions come from two places. The plugin's rules, in `rules/`, state what Rust code here may never do, each condition with its detector; a finding against one cites the rule's path and the condition's number, as `rules/panics.md` condition 1. The checklists in `references/` hold what a Rust reader catches that no rule states, identified by a prefix and a number, as RS-4; a finding against one cites the identifier. The checklists do not restate the rules. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `rust` route on the changed `.rs` files. Those are the files this skill reads.

Read whether the crate is a library or a binary (`Cargo.toml`, `lib.rs` vs `main.rs`): `rules/error-types.md` and `rules/non-exhaustive.md` bind a library and not a binary, and an `anyhow` that is right in `main.rs` is a finding in `lib.rs`. Read the project's Clippy configuration and whether CI runs `cargo clippy -- -D warnings`. A rule condition decided by a lint the project denies — `clippy::unwrap_used`, `clippy::undocumented_unsafe_blocks` — is settled by a green run and not reported again; one decided by a lint the project has not enabled is read here, by eye, and the finding says which lint would have decided it, as `docs/toolchain.md` lists them.

Run the plugin's hook over the changed crate. It decides condition 1 of `rules/error-types.md`, `rules/async-blocking.md`, `rules/unit-tests.md` and `rules/redaction.md`, and conditions 1 and 2 of `rules/dependency-direction.md`; each line it prints on a changed line, or about a file or module the change added, is a finding as it stands.

```sh
python3 <rust-plugin>/hooks/check-rust.py <crate-dir>
```

`<rust-plugin>` is where this plugin is installed, `engineering/rust` in the framework repository.

## 2. Open the checklists the change calls for

| What the change touches | Rules | Checklist |
|---|---|---|
| an `unwrap`, `expect`, `panic!`, `unreachable!` | `rules/panics.md` | |
| `unsafe`, an `unsafe impl`, a raw pointer | `rules/unsafe-code.md` | |
| an `extern` block, an `extern "C" fn`, a C type | `rules/ffi.md`, `rules/unsafe-code.md` | |
| an `as` cast, arithmetic, an index, a dropped `Result` | | `references/panics-and-safety.md` |
| an `async fn`, an `.await`, a lock, a channel, `spawn` | `rules/async-blocking.md` | `references/ownership-and-concurrency.md` |
| a `clone`, a parameter's type, a lifetime, `Rc`/`RefCell`/`Arc` | `rules/ownership.md` | `references/ownership-and-concurrency.md` |
| a string slice, a length used as a character count | `rules/strings.md` | |
| bytes read from a file, stdin, a pipe or a socket | `rules/utf8-io.md` | |
| a regex, `aho-corasick`, a matcher built at run time | `rules/regex-compilation.md` | |
| an error type, a `?` conversion, a `map_err` | `rules/error-types.md` | `references/errors-and-surface.md` |
| a `pub` enum or struct, a trait, a generic bound, a re-export | `rules/non-exhaustive.md` | `references/errors-and-surface.md` |
| a new crate, module, `use` across modules, or dependency in `Cargo.toml` | `rules/dependency-direction.md` | `references/errors-and-surface.md`, with `docs/architecture.md` |
| a new function, or a new file under `src/` | `rules/unit-tests.md` | |
| a log, a trace, `#[instrument]`, a `Debug` or `Serialize` derive, an error's `Display`, a response body | `rules/redaction.md` | |

A finding under `rules/redaction.md` is blocking whatever the route says, and cites, beside the condition, the general exposure rule tracked in #294 of `ahrena-framework`: the 2026-11-12 incident that rule records was a dependency's error returned to a caller, and both reviews that read the change passed it.

## 3. Read beyond the hunk

Follow each changed item to its callers and to what it borrows from. Whether an `unwrap` is safe is decided by what the function it calls can return, which its signature and body show. Whether a lifetime is right is decided by what outlives what. Read the base revision before calling a line wrong.

## 4. Apply the routed conditions

Work condition by condition, the routed rules' conditions first and then the checklists'. Give the scenario in Rust terms: the input or state, the panic, the truncation, or the needless allocation, and what it should have been. A condition whose answer is a project convention the repository does not state is a `question`.

Read each rule's `Where this stops` and each checklist condition's `Exempt` line. An `expect` that names a real invariant, an `unsafe` whose safety comment is true, a `clone` of an `Arc` handle — each is correct, and reporting it costs the reviewer's credit.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the rule path and condition number or the checklist identifier, and a correction that is an instruction.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Length, nesting, duplication, a premature trait with one implementor: those are `reviewing-diffs` and the fundamentals rules.

**What the compiler already rejects.** A use-after-move, an aliased mutable borrow, a missing lifetime: the borrow checker decides these and the change would not compile. This skill reads what compiles and is still wrong.

**Security of the change.** Untrusted input reaching a command or a query, a secret, deserialisation of hostile data: that is the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`).

**Another language.** A `.py`, `.ts` or `.go` file in the same change is read by that language's skill.
