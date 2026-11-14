---
id: dependency-direction
type: rule
clade: engineering
subclade: rust
title: Crates and modules depend in one direction
statement: Rust code is split into workspace crates by layer and modules by concern; a crate depends only on lower layers, and no module cycle exists inside a crate.
enforcement: judgment
references:
  - docs/architecture.md
  - docs/toolchain.md
---

# Crates and modules depend in one direction

A Rust program is composed of two units of packaging: the crate, which Cargo builds and versions, and the module, which organises a crate's code into a tree of files. This rule makes the dependencies between both units point one way. A cycle is a violation, not a smell: two units that need each other cannot be understood, tested, replaced or extended one at a time. [`docs/architecture.md`](../docs/architecture.md) argues the layout, the layers and how a unit is extended without being edited.

**What the specification says, and what it leaves open.** The Rust Reference defines a crate as a compilation unit with a tree of modules ([Crates and source files](https://doc.rust-lang.org/reference/crates-and-source-files.html), [Modules](https://doc.rust-lang.org/reference/items/modules.html)). It forbids a cycle of `pub use` re-exports ([Use declarations](https://doc.rust-lang.org/reference/items/use-declarations.html): a cycle of such redirections is a compile-time error), and nothing else: two modules of one crate may `use` each other freely. Cargo refuses a cycle among packages' normal dependencies with a "cyclic package dependency" error, and permits one through `[dev-dependencies]`. So the language decides the crate-level cycle, and the module-level cycle and the direction between layers are left open. This rule closes both, on the premise [`docs/architecture.md`](../docs/architecture.md) states: no circular reference.

The rule is new to this plugin. It comes from the owner's directive on #285, item 4, and has no predecessor lexis.

## Conditions

1. **No two modules of one crate reach each other, directly or round a longer cycle.** Decided by `hooks/check-rust.py`. A module is a file under the crate's `src/` (`lib.rs`, or `main.rs` in a crate with no library, is the root; `a.rs` and `a/mod.rs` are `crate::a`). An edge is every `crate::`, `self::` and `super::` path the file names, in a `use` or inline, resolved to the deepest module it reaches. A module and its own ancestor or descendant are not an edge, because the module tree is the crate's ownership: `lib.rs` re-exporting a child, and a child naming its parent's items, are how a crate is meant to be assembled. Each strongly connected component is reported once, as its shortest cycle, with the other modules in it named.

2. **In a workspace that declares layers, a crate depends only on crates of its own layer or below.** Decided by `hooks/check-rust.py`. The workspace lists its layers, lowest first, in its root manifest, and each member names its layer in its own; Cargo ignores both tables and reserves them for tools ([The metadata table](https://doc.rust-lang.org/cargo/reference/manifest.html#the-metadata-table)):

   ```toml
   [workspace.metadata.ahrena]
   layers = ["domain", "application", "infrastructure", "app"]

   [package.metadata.ahrena]
   layer = "domain"
   ```

   A normal dependency on a crate of a higher layer is reported; so is a member that names a layer the workspace does not list. `[dev-dependencies]` are not read, because a test may assemble the layers above the one it tests.

3. **No cycle among the workspace's crates, including through `[dev-dependencies]`.** Cargo decides the normal-dependency case by refusing to resolve it. A cycle closed by a dev-dependency builds, and is decided by a reviewer reading `cargo tree -e dev`; it is what makes a crate's tests depend on the crate that depends on it, and it is broken by moving the shared test support into a crate below both.

## Where this stops

**Inline modules are not separated.** A `mod inner { … }` written inside a file is read as part of that file's module. A crate whose cycle runs between two inline modules of one file is not reported; such a file is already a candidate for splitting by the single-responsibility limits [`docs/architecture.md`](../docs/architecture.md) cites.

**Paths through a renamed import or a macro are not followed.** `use crate::a as alpha;` followed by `alpha::f()` is one edge, from the `use`; a path built by a macro is none. Glob imports (`use crate::a::*`) are an edge to the module they name, which is the right reading.

**A workspace with no layers is held to conditions 1 and 3 only.** The layer map is the project's to write, as `ahrena-engineering-fundamentals:rules/solid.md` condition 6 already says of its policy and mechanism map; this plugin ships none and does not guess one from crate names.

**Measured over a local Cargo registry**, 328 crate directories and about 415,000 lines, condition 1 found module cycles in 69 crates, among them Tokio, rustls and syn, and reports them as 133 findings, one per strongly connected component. The language permits them and those crates are correct; they are what this rule exists to keep out of new code, and why it is a rule here and not a description of the ecosystem's habits. Condition 2 found nothing, because no published crate declares the layer metadata.

**Target-specific dependencies are not read.** A dependency under `[target.'cfg(…)'.dependencies]` is a reviewer's for condition 2.
