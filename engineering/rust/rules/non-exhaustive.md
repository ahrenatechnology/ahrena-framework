---
id: non-exhaustive
type: rule
clade: engineering
subclade: rust
title: A public type that will grow is non-exhaustive
statement: A Rust library marks every public enum and all-public-field struct that may grow `#[non_exhaustive]`, and a closed one says why it is closed.
enforcement: judgment
references:
  - docs/api-design.md
  - docs/toolchain.md
---

# A public type that will grow is non-exhaustive

A caller that matches on every variant of a public enum, or builds a public struct with a literal, breaks the day a variant or a field is added. Under semantic versioning that addition is then a major release, so a library that did not plan for growth either stops growing or breaks its callers. `#[non_exhaustive]` is the plan: callers outside the crate must write a wildcard arm and cannot use a struct literal, and adding to the type becomes a minor release. [`docs/api-design.md`](../docs/api-design.md) places this among the other ways a public surface is kept evolvable.

Inherited from the predecessor's `lex-rust-non-exhaustive-types`, drawn from ripgrep's error kinds and Tokio's practice of evolving its API without major releases. The source cited the Rust API Guidelines for it; the guidelines checklist has no `#[non_exhaustive]` item, and its nearest, C-STRUCT-PRIVATE, asks for private fields instead. Both are the same protection, and condition 1 accepts either.

## Conditions

1. **In a library crate, every public enum, and every public struct whose fields are all public, is `#[non_exhaustive]` or carries `#[allow(clippy::exhaustive_enums, reason = "…")]` or `#[allow(clippy::exhaustive_structs, reason = "…")]` saying why it is closed.** Decided by Clippy's `clippy::exhaustive_enums` and `clippy::exhaustive_structs`, from the `restriction` group, denied in library crates. The struct lint already stays quiet on a struct with a private field, which cannot be built by a literal outside the crate and is therefore closed to callers by construction. The `reason` is the documentation of the decision: "the four cardinal directions" closes an enum; "nobody has asked for a fifth" does not.

2. **A struct that is `#[non_exhaustive]` or has private fields, and that callers need to build, has a constructor or a builder.** Decided by a reviewer. A non-exhaustive struct cannot be built outside its crate at all without one, so forgetting it ships a type that callers can receive and never create.

3. **A release of the library does not change its public API incompatibly without a major version.** Decided by `cargo semver-checks`, run in the release pipeline against the last published version. It catches the break condition 1 exists to prevent and the dozens of others no attribute does — a removed method, a narrowed bound, a changed signature.

## Where this stops

**Binaries and internal crates are out of scope.** A type nothing outside the workspace matches on breaks nobody by growing. The lints are enabled per crate, in the library's manifest, not across a workspace that also holds applications.

**A closed type is closed by decision, not by default.** `Option`-shaped enums, a two-state `Ordering`, a coordinate struct: each is a fact about the domain, and the `allow` with its reason says so. What the rule refuses is the enum that is exhaustive because nobody thought about it.

**`#[non_exhaustive]` costs the caller.** A wildcard arm hides a new variant the caller might have wanted to handle; the compiler no longer tells them. That is the trade, and it is the right one for a library's error kinds and configuration structs, where the caller's fallback is usually correct. For an enum whose every variant the caller must handle — a protocol's message types — exhaustiveness is the feature, and condition 1's `reason` is where to say so.

**`cargo semver-checks` does not know about behaviour.** A function that keeps its signature and changes what it returns passes it. That is the release notes' and the reviewer's.
