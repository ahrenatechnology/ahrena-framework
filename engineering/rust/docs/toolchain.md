---
id: toolchain
type: doc
clade: engineering
subclade: rust
title: The Rust toolchain, and the lints the rules lean on
summary: Which of rustfmt, Clippy, cargo-deny, cargo-audit, cargo-semver-checks and the MSRV a Rust project runs and why, the Clippy lints each rule of this plugin names and the group each sits in, the two set to the fundamentals' single-responsibility limits, what the one hook decides and what it measured, and why every Rust rule is a judgment rule.
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
---

# The Rust toolchain, and the lints the rules lean on

Rust's compiler already decides more than most languages' linters: types, lifetimes, aliasing, exhaustive matches, unused results. What it leaves is decided by Clippy, by a handful of `cargo` subcommands, and by a reader. The thirteen rules of this plugin lean on all three, and this page is where the first two are set out once, so each rule can name a lint and stop.

It is also a refusal to ship a configuration file. A `clippy.toml` copied into a project is a list of switches the project did not choose and will not reread. What follows names each switch, the rule that needs it, and the reason, and leaves the file to the project.

**What the specification says.** The tools on this page are not the language; Cargo's own documentation is normative for Cargo ([The Cargo Book](https://doc.rust-lang.org/cargo/)), and Clippy's lint list for Clippy. Where a lint below holds a rule's condition, the specification behind the condition is cited in the rule.

## What runs in CI, and why each one

**`cargo fmt --check`.** Formatting is settled by running rustfmt and accepting its output. No rule here has an opinion about layout, and none should: a reviewer who comments on brace placement is spending attention a formatter would have spent for free. `rustfmt.toml` is the project's; the defaults are fine.

**`cargo clippy --all-targets --all-features -- -D warnings`.** Every lint Clippy enables by default is denied, and the lints the rules below name are turned on in the manifest. `--all-targets` includes tests, examples and benches, so test code is linted too, with the `allow-*-in-tests` settings below carving out what tests legitimately do.

**`cargo test --all-features`**, and `cargo test --doc` when the project uses `cargo-nextest`, which does not run doc tests. [`testing.md`](testing.md) says why both kinds run.

**`cargo deny check`.** One tool for four supply-chain questions: a dependency with a known advisory (it reads the RustSec database, the same one `cargo audit` reads), a licence the project has not accepted, a crate from a source the project has not allowed, and the same crate pulled in at two versions. `cargo audit` alone covers the first; `cargo-deny` is preferred because the other three are the ones that go wrong without anyone noticing. Both need the project to state its policy in `deny.toml`, which is the point.

**`cargo semver-checks`**, for a published library, before each release. It compares the public API with the last published version and fails on a change that needs a major version. [`rules/non-exhaustive.md`](../rules/non-exhaustive.md) condition 3 names it.

**The MSRV build.** A library that promises a minimum supported Rust version declares it as `rust-version` in `Cargo.toml` and builds with exactly that toolchain in one CI job. Since Rust 1.84, the resolver of the 2024 edition reads `rust-version` and prefers dependency versions compatible with it, so declaring it also keeps `cargo update` from pulling in a dependency the project's oldest supported compiler cannot build. An application deployed with one known toolchain has no MSRV to promise and pins the toolchain in `rust-toolchain.toml` instead.

**`python3 engineering/rust/hooks/check-rust.py <crate>`**, the one hook in this plugin. It runs on the standard library alone, so CI runs it without installing anything.

## Lints the rules name

Every lint below was checked against Clippy 0.1.99 and rustc 1.99, by running it over a probe crate; the group is what decides whether it is on without configuration. "Default" means the group Clippy enables unless told otherwise — `correctness`, `suspicious`, `style`, `complexity`, `perf`. `pedantic`, `nursery` and `restriction` are off until named.

| Lint | Group | Rule and condition |
|---|---|---|
| `clippy::unwrap_used` | restriction | [`panics.md`](../rules/panics.md) 1 |
| `clippy::panic`, `clippy::todo`, `clippy::unimplemented` | restriction | `panics.md` 3 |
| `clippy::missing_panics_doc` | pedantic | `panics.md` 4 |
| `clippy::undocumented_unsafe_blocks` | restriction | [`unsafe-code.md`](../rules/unsafe-code.md) 1 |
| `clippy::missing_safety_doc` | style (default) | `unsafe-code.md` 2 |
| `unsafe_op_in_unsafe_fn` (rustc) | warn by default since the 2024 edition | `unsafe-code.md` 3 |
| `improper_ctypes`, `improper_ctypes_definitions` (rustc) | warn by default | [`ffi.md`](../rules/ffi.md) 2 |
| `clippy::await_holding_lock`, `clippy::await_holding_refcell_ref` | suspicious (default) | [`async-blocking.md`](../rules/async-blocking.md) 2 |
| `clippy::map_err_ignore` | restriction | [`error-types.md`](../rules/error-types.md) 3 |
| `clippy::exhaustive_enums`, `clippy::exhaustive_structs` | restriction | [`non-exhaustive.md`](../rules/non-exhaustive.md) 1 |
| `clippy::lines_filter_map_ok` | suspicious (default) | [`utf8-io.md`](../rules/utf8-io.md) 2 |
| `clippy::regex_creation_in_loops` | perf (default) | [`regex-compilation.md`](../rules/regex-compilation.md) 1 |
| `clippy::invalid_regex` | correctness (default, deny) | `regex-compilation.md` 4 |
| `clippy::ptr_arg` | style (default) | [`ownership.md`](../rules/ownership.md) 1 |
| `clippy::needless_pass_by_value` | pedantic | `ownership.md` 2 |
| `clippy::unnecessary_to_owned` | perf (default) | `ownership.md` 3 |
| `clippy::redundant_clone` | nursery | `ownership.md` 3 |
| `clippy::needless_lifetimes` | complexity (default) | `ownership.md` 5 |
| `clippy::string_slice` | restriction | [`strings.md`](../rules/strings.md) 1, as a finder, not denied |

The ones outside the default groups go in the manifest, where every crate in a workspace inherits them:

```toml
[workspace.lints.clippy]
unwrap_used = "deny"
undocumented_unsafe_blocks = "deny"
```

and so on for each row, with `[lints] workspace = true` in each member ([The `lints` table](https://doc.rust-lang.org/cargo/reference/workspaces.html#the-lints-table)). `[workspace.lints]` has been stable since Rust 1.74, and it is the reason a lint configuration no longer needs to live in `.cargo/config.toml` flags or a `#![deny]` at the top of every crate root.

The library-only lints — `exhaustive_enums`, `exhaustive_structs`, `missing_panics_doc` — cannot be added on top of the inherited set: Cargo 1.99 refuses a member that sets `workspace = true` and also lists its own `[lints.clippy]` ("cannot override `workspace.lints` in `lints`"). So a library crate leaves out `workspace = true` and lists, in its own `[lints.clippy]`, the workspace's lints plus its three. The duplication is the price of Cargo's all-or-nothing inheritance, and it is paid only by library crates, because an application's types break nobody by growing.

`clippy.toml` carries the four settings that keep the restriction lints off test code, each checked against Clippy 0.1.99: `allow-unwrap-in-tests`, `allow-expect-in-tests`, `allow-panic-in-tests` and `allow-indexing-slicing-in-tests`, all `true`.

## Lints set to the single-responsibility limits

[`docs/architecture.md`](architecture.md) holds every function and file to the limits of `ahrena-engineering-fundamentals`, and this plugin adds no number of its own. Two of those limits have a Clippy lint that counts the same thing, and `clippy.toml` sets each to the fundamentals' figure. Both lints are in the default `complexity` group, so setting the threshold is enough to turn them on, which a probe crate on Clippy 0.1.99 confirmed.

| Setting | Lint | Fundamentals limit |
|---|---|---|
| `too-many-arguments-threshold = 4` | `clippy::too_many_arguments` | `rules/value-semantics.md` condition 1, at most 4 named parameters; the receiver is not counted by either |
| `excessive-nesting-threshold = 3` | `clippy::excessive_nesting` | `rules/kiss.md` condition 1, control flow nested at most 3 deep; Clippy counts nested blocks, closures included, so it is the stricter of the two |

The other limits have no lint that measures them. `rules/clean-code.md` condition 1 counts statements, and Clippy's `too_many_lines`, from `pedantic`, counts lines, which the fundamentals' [`clean-code.md`](../../fundamentals/docs/clean-code.md) doc refuses as a measure because the formatter decides it; a reviewer counts. A branch on a boolean parameter (`rules/kiss.md` condition 2) and a type whose methods do not share state (`rules/solid.md` condition 1) are a reviewer's too; `clippy::fn_params_excessive_bools` reports more than three boolean parameters, which is a different question.

**What is deliberately not on the list.** `clippy::expect_used` would forbid the `expect` that [`panics.md`](../rules/panics.md) condition 2 allows. `clippy::indexing_slicing` and `clippy::arithmetic_side_effects` decide real defects and fire on every loop over a slice and every sum; denying them crate-wide produces an `allow` per function and no finding. `clippy::pedantic` as a whole is not enabled: it is a collection of opinions, several of which contradict each other's fixes, and a project that wants it can have it. `#![forbid(unsafe_code)]` is recommended for a crate with no `unsafe` and not required, for the reason [`unsafe-code.md`](../rules/unsafe-code.md) gives.

## The hook, and what it measured

`hooks/check-rust.py` decides six conditions that the source decides and no Clippy lint does: condition 1 of [`error-types.md`](../rules/error-types.md), [`async-blocking.md`](../rules/async-blocking.md), [`unit-tests.md`](../rules/unit-tests.md) and [`redaction.md`](../rules/redaction.md), and conditions 1 and 2 of [`dependency-direction.md`](../rules/dependency-direction.md). It reads a masked copy of each file — comments, strings and character literals blanked, offsets kept — because the hooks take no dependency and Python's standard library has no Rust parser. A signature, a call path, a module path, a derive list and a field's type survive masking; nothing the hook decides needs more. The layer map of condition 2 is read from the manifests with the standard library's `tomllib`.

It was run over every crate in a local Cargo registry: 328 crate directories, about 8,400 source files outside `tests/`, about 415,000 lines. The run that counts reported 4,609 findings:

| Rule, condition | Findings | What they are |
|---|---|---|
| `error-types` 1 | 18 | each an opaque error on a public library function: 7 string errors (in `cc`, `find-msvc-tools`, `dom_query`, `notify-rust`, `ring`'s test utilities, `tauri`, `zerovec`) and 11 `anyhow` returns in Tauri's build-time helper crates |
| `async-blocking` 1 | 34 | all inside Tokio's own `tokio::fs`, which offloads through an internal wrapper the hook does not know; the rule says what a consuming project does about that |
| `dependency-direction` 1 | 133 | module cycles in 69 crates, one finding per strongly connected component |
| `dependency-direction` 2 | 0 | no published crate declares the layer metadata |
| `unit-tests` 1 | 4,421 | files with functions and no unit test, in 292 crates; much of the ecosystem tests through `tests/` and doc tests instead |
| `redaction` 1 | 3 | a URL's password component held in a `String` on `urlpattern`'s `Debug` types |

The last three rows are conditions the ecosystem does not hold and this framework asks of the code it writes; their numbers describe the ecosystem, not false positives. Earlier runs did report false positives, and each became a case in `hooks/test-check-rust.py` before its fix: boxed errors inside callback types and errors returned as values (`error-types`), a `tests.rs` module declared with `#[cfg(test)] mod tests;` (`async-blocking`), syntax tokens and boolean flags read as secrets (`redaction`, 31 findings before the fix), one finding per path round a cycle rather than per cycle (`dependency-direction`, 433 before), and a `#[cfg(test)]` on a field that hid the item after it, which Argos found in review. Every condition is pinned first by a failing case.

## Why every rule here is judgment

Each rule names a detector per condition, and for most conditions the detector is a Clippy lint the consuming project runs. `enforcement: hook` would mean a script inside this plugin decides the whole rule, and a hook rule contributes nothing to the instruction file — its statement never reaches the agent writing the code. Five rules have a condition the hook decides, and each has other conditions that need Clippy, Cargo or a reader. Declaring them `hook` would drop the requirement to run Clippy at all, which is the same reasoning `ahrena-engineering-python`'s typing rule gives for requiring mypy.

The cost is counted. Thirteen statements, 1,868 characters in all, reach the instruction file of a project that installs this plugin. A project that installs it is writing Rust, and each line names a defect a Rust agent is otherwise likely to write.

## Workspaces and layout

The predecessor's `codex-rust-system-design` recommended a Cargo workspace above 5,000 lines of code and `#[tracing::instrument]` on every important component. Neither threshold was measured or attributed, and neither survives as a number. What survives is the mechanism: a workspace with `[workspace.dependencies]` keeps every member on one version of each dependency, and `[workspace.lints]` keeps one lint policy, as above. A service puts each layer in its own crate, for the reason [`architecture.md`](architecture.md) gives: only a crate boundary is one the compiler holds. Beyond the layers, a part becomes its own crate when it has a reason to compile, test or publish on its own — ripgrep's `grep-searcher`, `grep-regex` and `ignore` are published separately and used by other tools — or when it extends a base crate without editing it, and not before. A single-binary tool of a few modules stays one crate. [`api-design.md`](api-design.md) covers the public surface each crate then has.

## Where this stops

**No version numbers.** The tools above change their flags and their defaults; the commands are the ones current at Clippy 0.1.99 and Cargo 1.99, and a project pins its own tool versions in its CI.

**No configuration file is shipped.** The `[workspace.lints]` excerpt is an excerpt. The table is the content; which lints a project adds beyond it is the project's.

**CI provider specifics are out of scope.** Caching `target/`, `sccache` and matrix builds are build engineering, not Rust correctness.
