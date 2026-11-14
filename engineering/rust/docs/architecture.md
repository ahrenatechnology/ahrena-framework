---
id: architecture
type: doc
clade: engineering
subclade: rust
title: How a Rust implementation is composed
summary: The premises every implementation choice is argued from, the crate and the module as Rust's units of packaging and the one direction between them, how SOLID and inversion of control are written with traits and generics, how a crate is extended without being edited, and what single responsibility means for a Rust function, module and file.
references:
  - rules/dependency-direction.md
  - rules/unit-tests.md
  - rules/redaction.md
  - docs/api-design.md
  - docs/toolchain.md
  - ahrena-engineering-fundamentals:docs/clean-code.md
---

# How a Rust implementation is composed

This is the companion to [`rules/dependency-direction.md`](../rules/dependency-direction.md), and the page [`skills/writing-rust`](../skills/writing-rust/SKILL.md) reads before it places any code. It answers the questions every implementation meets before its first test: which crate and which module the code goes in, what it may depend on, how a collaborator is reached, and how big a unit may grow. It follows the owner's directive on #285, items 3 to 8.

## The premises

Every choice between two implementation paths on this page is argued from three premises, and an artifact of this plugin that recommends a path names which one decides it.

- **Maintainability.** The path a later reader can change with the fewest files touched and the least to understand first.
- **Lower cyclomatic complexity.** Fewer independent paths through a unit, so fewer cases to test and fewer to reason about. In Rust the branch count is `if`, `match` arms, `?`, loops and `&&`/`||`; a `match` that the type system makes exhaustive is still one path per arm.
- **No circular reference.** Two units that need each other are one unit split badly. [`rules/dependency-direction.md`](../rules/dependency-direction.md) makes this a condition at both levels of packaging.

When the premises disagree, no circular reference wins outright, because a cycle cannot be undone by later care. Between the other two, maintainability wins over a lower count when the lower count is bought with indirection the reader must follow.

## Units of packaging

Rust has two, and the specification defines both. A **crate** is the unit of compilation and of versioning: Cargo builds it, publishes it and resolves its dependencies, and refuses a cycle among them ([Crates and source files](https://doc.rust-lang.org/reference/crates-and-source-files.html); [Cargo workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)). A **module** is the unit of namespace and privacy inside a crate, one file each in the layout this plugin uses ([Modules](https://doc.rust-lang.org/reference/items/modules.html); [Visibility and privacy](https://doc.rust-lang.org/reference/visibility-and-privacy.html)).

**A layer is a crate; a concern is a module.** A service is a Cargo workspace whose members are its layers — `domain`, `application`, `infrastructure` and the binary that wires them, in the vocabulary of `ahrena-engineering-fundamentals`; the project's component map may name them otherwise. Each layer is a crate because only a crate boundary is enforced by the compiler: a module can reach any other module of its crate that is visible to it, and a `pub(crate)` item is visible everywhere in the crate. A crate can reach only what it declares as a dependency. So the direction between layers is held by Cargo's dependency list, and checked against the declared layer map by the hook ([`rules/dependency-direction.md`](../rules/dependency-direction.md) condition 2). Inside a crate, modules are split by concern — one aggregate, one port, one adapter per file — and kept acyclic by condition 1.

**Premise: no circular reference.** Cargo makes a cycle between crates impossible to build, so putting each layer in a crate turns the layering from a convention into something the build enforces. The cost is compile-time boundaries a small program does not need: a single crate with modules is the right shape until a second layer exists, and [`docs/toolchain.md`](toolchain.md) says when to split.

**The recommended tool is Cargo's own workspace.** It is part of the toolchain, so there is nothing to install, and `[workspace.dependencies]` and `[workspace.lints]` keep every member on one version of each dependency and one lint policy. The alternative is separate repositories, which are the better choice when two crates have different owners, release on different schedules, or must be consumed by projects that should not see each other's code; a workspace whose crates release independently adds `release-plz` or `cargo-release` to version them one at a time.

## SOLID and inversion of control, in Rust's form

The conditions are `ahrena-engineering-fundamentals:rules/solid.md`'s, arbitrated by its `rules/yagni.md`, and this plugin does not restate them. What follows is how Rust expresses each, and where the language stops it.

- **Dependency inversion** is a trait owned by the consumer's crate. The domain crate declares `pub trait OrderRepository { … }`; the infrastructure crate depends on the domain and implements it; the application takes the trait. The dependency arrow points from infrastructure to domain, the opposite of the call. This is the inversion, and it is why the layer map can order `domain` lowest.
- **Inversion of control** is the binary's `main`, which constructs the concrete adapters and passes them in. Rust has no reflection and no runtime container, and does not need one: a constructor that takes its collaborators (`OrderService::new(repo, clock)`) is the whole mechanism. A service-locator or a global registry of trait objects is a pattern imported from runtimes that have containers, against the grain of this one, and `reviewing-rust` reports it.
- **Static or dynamic dispatch.** A collaborator is a generic parameter (`struct OrderService<R: OrderRepository>`) when the concrete type is known at the composition root, which is almost always: it costs nothing at run time and keeps the type visible. It is a trait object (`Arc<dyn OrderRepository>`) when the implementation is chosen at run time, when a collection holds several, or when generic parameters would spread through every type that holds the service. Both satisfy dependency inversion; [`api-design.md`](api-design.md) covers the trade, and the trait must be dyn-compatible for the second ([Dyn compatibility](https://doc.rust-lang.org/reference/items/traits.html#dyn-compatibility)).
- **Interface segregation** is small traits. Rust's coherence rules let a type implement any number of them ([Trait implementation coherence](https://doc.rust-lang.org/reference/items/implementations.html#trait-implementation-coherence)), so a consumer asks for the one it calls.
- **Liskov substitution** is a trait's documented contract, which the compiler checks only as far as signatures go; a shared test suite run against every implementation is what checks the rest.
- **Single responsibility and open/closed** are the next two sections.

Where the language limits the principle: Rust has no inheritance, so "extend a class" becomes "implement a trait" or "wrap a type"; and the orphan rule ([Orphan rules](https://doc.rust-lang.org/reference/items/implementations.html#orphan-rules)) forbids implementing a foreign trait for a foreign type, so an adapter for two third-party crates is a newtype the adapter crate owns. A trait with one implementation and no test that needs a second is `rules/yagni.md` condition 1's to delete; the trait at a layer boundary usually has its in-memory test double as the second.

## Extending without modifying

A crate is open to extension and closed to modification. A new behaviour is a new crate that depends on the base one and plugs into the extension points the base publishes; the base is not edited for it. Rust gives three such points, in order of preference.

1. **A trait the base crate defines and accepts.** The base takes `impl Exporter` or `Box<dyn Exporter>`; a new crate implements `Exporter` for its type, and the application passes it in. The base never learns the new crate's name. **Premise: no circular reference** — the extension depends on the base and nothing points back.
2. **A generic parameter with a default.** `pub struct Client<T: Transport = HttpTransport>` lets a caller substitute a transport without the base changing, and costs nothing at run time.
3. **A Cargo feature, where the extension is optional and ships with the base.** A feature compiles in an integration the base maintains — `serde` support, a TLS backend — and Cargo's guide asks that features be additive, because they are unified across the build ([Feature unification](https://doc.rust-lang.org/cargo/reference/features.html#feature-unification)). A feature is the wrong tool for a behaviour a third party writes: that is the first mechanism, in its own crate.

A sealed trait ([C-SEALED](https://rust-lang.github.io/api-guidelines/future-proofing.html#c-sealed)) is the deliberate opposite: an extension point closed to outside crates, so the base may add methods. Choosing which traits are open and which sealed is the base crate's design decision, and [`api-design.md`](api-design.md) discusses it.

## Single responsibility, down to the function and the file

The limits are `ahrena-engineering-fundamentals`'s, and this plugin adds no number of its own: a function body of at most 30 statements and a statement after an unconditional exit never (`rules/clean-code.md` conditions 1 and 2); control flow nested at most 3 deep and no branch on a boolean parameter (`rules/kiss.md` conditions 1 and 2); at most 4 named parameters (`rules/value-semantics.md` condition 1); and a type whose methods split into unconnected groups is two types (`rules/solid.md` condition 1).

In Rust the units are these:

- **The function or method** is the unit of behaviour and of test. Its receiver (`self`, `&self`, `&mut self`) is not one of its four parameters, as the receiver is excluded in the fundamentals rule.
- **The module, which is one file,** solves one problem: one aggregate and its invariants, one port, one adapter, one parser. Its tests sit in it ([`rules/unit-tests.md`](../rules/unit-tests.md)).
- **The crate** is one layer, or one extension.

A unit is tested in isolation by the `#[cfg(test)] mod tests` of its own file, which reaches its private items, with any collaborator replaced through the trait it is given (section above). A unit that cannot be tested that way has a hidden collaborator: a global, a `static`, a direct call to the clock, the file system or the network.

The tools that report a unit past the limit, configured to the fundamentals' numbers in `clippy.toml`, are in [`docs/toolchain.md`](toolchain.md): `clippy::too_many_arguments` at 4 and `clippy::excessive_nesting` at 3. Two limits have no Clippy counterpart and are read by a reviewer: the 30-statement count, because Clippy's `too_many_lines` counts lines and [`clean-code.md`](../../fundamentals/docs/clean-code.md) explains why a line count is the wrong measure; and the branch on a boolean parameter.

## Sensitive data stays in its layer

The layer that owns a secret, a credential, an access policy or an infrastructure detail is the only one that sees it in full. A value crosses a layer boundary as a type the next layer can use and cannot print, and an error crosses it translated. [`rules/redaction.md`](../rules/redaction.md) states how Rust holds this, under the general rule tracked in #294.

## Where this stops

**Small programs need less of this.** A single-binary tool of a few modules is one crate with acyclic modules and tests beside its functions; the layer workspace is for a service with a domain worth protecting.

**Runtime plug-ins are not covered.** Loading an extension from a shared library at run time crosses an unstable ABI and is FFI ([`rules/ffi.md`](../rules/ffi.md)); a WebAssembly host is the usual better answer, and both are specialist territory.

**The layer names are examples.** The direction is the rule; the names come from the project's component map.
