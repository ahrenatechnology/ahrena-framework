---
id: api-surface
type: rule
clade: engineering
subclade: go
title: An exported surface that does not leak
statement: An exported Go API returns no unexported or internal type, returns concrete types, documents every exported name, and copies slices and maps it keeps.
enforcement: judgment
references:
  - docs/project-layout.md
  - docs/toolchain.md
---

# An exported surface that does not leak

A package's exported identifiers are a promise to every importer, and Go makes two kinds of leak easy. One is a type the importer cannot name: an exported function that returns an unexported type, or a type from an `internal/` package, hands the caller a value it can use but cannot declare a variable of, write a function signature with, or mock. The other is state the importer was never meant to share: a slice handed in and kept, or an internal map handed out, which both sides then mutate. The conditions below are those leaks, and the two conventions that keep the surface small and readable.

[`docs/project-layout.md`](../docs/project-layout.md) argues where an interface belongs and how `internal/` draws the line between the surface and the rest.

## Conditions

1. **No exported function or method returns a value of an unexported type.** Decided by `revive`'s `unexported-return` rule, enabled by the project, which reports unexported interface types too. The fix is to export the type, or to declare an exported alias for it.

2. **No identifier exported from a package outside an `internal/` tree has, in its signature, its fields or its embedded types, a type declared in an `internal/` package.** An importer outside the tree cannot import that package, so it cannot name the type. Decided by [`hooks/check-source.py`](../hooks/check-source.py), which reads each non-test file of a non-`main` package outside any `internal/` directory of its module, and reports an internal package's type spelled in an exported function's or exported type's method signature, in an exported struct's exported or embedded field, or in an exported interface's method. An exported alias of the internal type (`type Record = store.Record`) is the remedy `revive` itself suggests for condition 1, and the hook lets it through. Source: the `go` command documentation, *Internal packages* — "Code in or below a directory named "internal" is importable only by code that shares the same import path above the internal directory."

3. **A constructor returns a concrete type, and an interface is declared in the package that consumes it.** Decided by a reviewer, who reads each new interface against its implementations and its consumers. Sources: Go Code Review Comments, *Interfaces* — "The implementing package should return concrete (usually pointer or struct) types", and "Do not define interfaces before they are used"; the Google Go style guide, decisions, *Interfaces*.
   - **Exempt:** an interface the package exports on purpose as a contract with several implementations, as `io.Reader` is, and a function that returns `error`.

4. **Every exported identifier has a doc comment that begins with its name.** Decided by `revive`'s `exported` rule, enabled by the project. `staticcheck` also checks the form, but its `ST1020` to `ST1022` are off in its default configuration. Sources: Go Code Review Comments, *Doc Comments* — "All top-level, exported names should have doc comments"; Go Doc Comments, `go.dev/doc/comment`.
   - **Exempt:** a `main` package, and a method that implements a documented interface method whose meaning is unchanged.

5. **A slice or map that crosses the exported surface is copied when the package retains it or when it exposes the package's own.** A setter that stores the caller's slice, and a getter that returns the package's internal map, both share backing storage with the other side. Decided by a reviewer. Sources: the Uber Go style guide, *Copy Slices and Maps at Boundaries*; Go Code Review Comments, *Copying*.
   - **Exempt:** a function whose doc comment says it takes ownership of the argument or returns a view the caller must not modify, as `bytes.Buffer.Bytes` does.

## Where this stops

**Condition 1 does not reach a field.** An exported struct with an exported field of unexported type leaks the same way and `unexported-return` does not see it. A reviewer reads it with condition 2.

**Condition 2 is decided by spelling, not by the package graph.** No linter in `golangci-lint`'s catalogue reports an internal type on a public surface, so this plugin's hook does, and it recognises an internal type by the name the file imports an `internal/` path under. It does not see an internal type reached through a public alias declared in another package, an exported variable or constant of internal type, or an anonymous struct nested inside an exported one; a reviewer reads those. It also treats every `internal/` import as unreachable, which is exact for importers outside the module and over-reports for a public package that is only ever imported from beneath the same parent — a layout the official module-layout page does not describe and a project can exclude by path.

**Condition 3 is not a ban on interfaces.** It decides where an interface is declared and what a constructor returns, not whether an interface should exist. Whether an interface with one implementation is premature is condition 1 of the fundamentals' YAGNI rule, [`yagni.md`](../../fundamentals/rules/yagni.md), which Go makes easy to violate.

**Condition 4 checks that a comment exists and starts correctly, not that it says anything.** A comment that restates the name in a sentence passes. Whether it tells the caller what they need is a reviewer's.

**Condition 5 has no opinion on performance.** A copy at every boundary costs an allocation, and a hot path may document the shared view instead. That is the exemption, and it is the doc comment that makes it one.

**This rule declares judgment although one condition has a hook.** Condition 2 is decided by [`hooks/check-source.py`](../hooks/check-source.py); the other four are decided by linters the project enables or by a reviewer, and a rule declared `hook` is replaced by its script, which would drop them. The hook has not been measured on a public corpus, for the reason [`context.md`](context.md) gives.

**Versioning is not here.** Whether a change to an exported identifier is a breaking change, and whether it needs a new major version, is the contract-break review in the quality plugin, not a condition of this rule.
