---
id: project-layout
type: doc
clade: engineering
subclade: go
title: Packages, internal, cmd and the direction of dependencies
summary: How a Go module is composed — packages named for what they provide, cmd/ for binaries, internal/ for what is not promised, layers depending one way, SOLID and inversion of control in Go's own form, extension by a new package rather than an edit, and modules with go.work when packages ship apart.
references:
  - rules/api-surface.md
  - rules/package-boundaries.md
  - docs/libraries.md
  - docs/sources.md
  - ahrena-engineering-fundamentals:rules/solid.md
  - ahrena-engineering-fundamentals:rules/yagni.md
---

# Packages, internal, cmd and the direction of dependencies

This is the companion of [`rules/package-boundaries.md`](../rules/package-boundaries.md) and [`rules/api-surface.md`](../rules/api-surface.md): the first states the direction packages depend in, the second what an exported surface may not leak, and this document argues how a module is arranged so that both hold by construction. Every implementation path it recommends is argued from three premises, named where they decide: maintainability (a change touches one package), lower cyclomatic complexity (a variant is a type, not a branch), and no circular reference (an arrow that points one way cannot close a loop). It is about Go's mechanics — packages, `internal/`, `cmd/`, import direction. The architecture a service follows inside them, its domain and its ports, is the backend plugin's, and this page names only how Go expresses it.

## Start from the official page, not the popular repository

The Go team publishes one layout document, *Organizing a Go module* (`go.dev/doc/modules/layout`). It starts from a single package at the module root and grows: a command goes under `cmd/`, which it calls "very useful in a mixed repository that has both commands and importable packages", and code that is not meant for other modules goes under `internal/`, which "prevents other modules from depending on packages we don't necessarily want to expose and support for external uses."

The repository called `golang-standards/project-layout` is not that page, and its own README says it "is NOT an official standard defined by the core Go dev team". Russ Cox, then the Go technical lead, wrote on its issue 117 that "these are in no way official standards". Its `pkg/` directory in particular has no meaning to the `go` tool, and adding it puts one more path segment in front of every import for nothing. A project that already uses it does not need to move; a new project starts from the official page.

## A package is named for what it provides

A package name is part of every call site — `orders.Cancel`, not `Cancel` — so it is short, lower-case, and names what the package provides, not what it contains. `util`, `common`, `helpers`, `models` and `types` name nothing: a package called `models` is a place where every type in the program ends up, and every package imports it. Go Code Review Comments, *Package Names*, says to "avoid meaningless package names like util, common, misc, api, types, and interfaces", and to drop the package name from the identifiers inside it.

Two consequences follow. A package is cut along what changes together, not along technical layers, so `orders` holds the order type, its rules and its storage interface, rather than a `models` package holding the type and a `repositories` package holding its storage. And a package does not stutter: `orders.Order` is fine, `orders.OrderService` repeats itself.

## internal/ draws the line the compiler enforces

The `go` command's rule is exact: "Code in or below a directory named "internal" is importable only by code that shares the same import path above the internal directory." (`cmd/go`, *Internal packages*.) That makes `internal/` the one boundary in a Go module that is checked by the compiler rather than by convention.

Use it for everything that is not a promise. In a service, that is nearly everything: the binary in `cmd/<name>` imports packages under `internal/`, and nothing outside the module imports any of it. In a library, the public packages sit at the root and the machinery sits under `internal/`, so a refactor of the machinery is never a breaking change.

What `internal/` does not do is stop an exported identifier in a public package from exposing an internal type in its signature. That compiles, and the importer receives a value whose type it cannot name. Condition 2 of [`rules/api-surface.md`](../rules/api-surface.md) holds it.

## cmd/ holds main, and main holds wiring

Each binary is a `main` package under `cmd/<binary-name>/`. Its `main` reads configuration, builds the dependencies with constructors, wires them together and starts the server; it contains no logic a test would want to exercise. That keeps the one place where `os.Exit` and `log.Fatal` are allowed — condition 5 of [`rules/errors.md`](../rules/errors.md) — small enough to read in one screen.

A dependency-injection framework is not needed for this. Constructors that take their dependencies as parameters, called in order in `main`, are dependency injection, and the wiring is ordinary code a reader can follow.

## Dependencies point one way

The packages that hold the rules of the domain import nothing that does I/O: no `database/sql`, no `net/http`, no SDK client. The packages that do I/O — the HTTP handlers, the store, the client of another service — import the domain, never the reverse. The premise that decides it is the third: a dependency that points one way cannot close a loop.

The Go Specification already makes half of this a compile error — "It is illegal for a package to import itself, directly or indirectly" (*Import declarations*) — so a domain package that needs storage cannot import a store that imports the domain. What the compiler does not see is a direction that is wrong without being circular: a `domain` package importing an `infra` package that imports nothing back compiles cleanly. [`rules/package-boundaries.md`](../rules/package-boundaries.md) names the layers — `domain` below `application` below `infra`, the same words the Python plugin uses — and its hook, `hooks/check-packages.py`, reports an import pointing up them. It also reports the one cycle the `go` command tolerates on purpose: two modules of one repository that require each other.

The way the domain reaches storage without importing it is an interface the domain declares.

## Interfaces are declared by the package that uses them

Go Code Review Comments, *Interfaces*, says Go interfaces "generally belong in the package that uses values of the interface type, not the package that implements those values", that "the implementing package should return concrete (usually pointer or struct) types", and "Do not define interfaces before they are used". The Google Go style guide, decisions, *Interfaces*, says the consumer should define it.

This is what makes the inward dependency work. The `orders` package declares `type Store interface { Get(ctx context.Context, id ID) (Order, error) }` with exactly the methods it calls. The `postgres` package returns a concrete `*Store` that happens to satisfy it, and never mentions `orders.Store`. Go's interfaces are satisfied implicitly, so the implementer does not import the consumer, and the arrow stays pointing inward.

It is also why a fake in a test is small: the interface it implements has the two methods the consumer uses, not the twenty the implementation offers. [`docs/libraries.md`](libraries.md) recommends hand-written fakes for that reason.

The cost is that an interface is declared once per consumer, and two consumers of the same store may declare overlapping interfaces. That duplication is deliberate: each states what that consumer needs, and neither breaks when the other grows.

## SOLID and inversion of control, in Go's form

The conditions are the fundamentals plugin's, in `ahrena-engineering-fundamentals:rules/solid.md`, with the arbitration of `rules/yagni.md` that it already states: an abstraction is due when a second real consumer or a test that exists today needs the seam, and not before. This plugin does not restate them. It says how Go expresses each, and where the language stops them.

- **Single responsibility** is held at three sizes. A function or method is held to the statement and nesting limits of the fundamentals' `rules/clean-code.md` and `rules/kiss.md`; a file solves one problem and has its own test beside it ([`rules/test-placement.md`](../rules/test-placement.md)); a package is named for one thing it provides. Go has no class, so `solid.md`'s cohesion measure applies to a type and its methods: methods that share no field and call nothing in common are two types.
- **Open/closed** is a package that accepts what it does not know: an interface parameter, a function type, a `func(http.Handler) http.Handler` middleware. A new behaviour is a new package that satisfies it, not an edit to the base — condition 5 of [`rules/package-boundaries.md`](../rules/package-boundaries.md). The section below says how the packages are composed.
- **Liskov substitution** is what an implicitly satisfied interface asks of every type that satisfies it, and Go cannot check it: the compiler checks method sets, not behaviour. The detector is `solid.md`'s own, the interface's test suite run against each implementation, which in Go is a shared table test that takes the implementation as a parameter.
- **Interface segregation** is the Go Code Review Comments position quoted above: small interfaces declared by their consumer. `io.Reader` has one method, and a consumer that needs two declares two.
- **Dependency inversion** is a constructor that takes its dependencies as parameters, typed as the consumer's own interfaces, and returns a concrete type. `main` calls the constructors in order; that call sequence is the whole of inversion of control in Go, and it is ordinary code a reader can follow. A dependency-injection container or a framework that wires by reflection is not needed and is not recommended: it moves the wiring out of the code a compiler checks.

**A pattern imported from another language against Go's grain is a review finding**, `GO-6` in the `reviewing-go` skill's reference: an interface declared beside its only implementation and named `IStore` or `StoreInterface`, a getter named `GetName` (Effective Go, *Getters*: "it's neither idiomatic nor necessary to put Get into the getter's name"), a class hierarchy rebuilt from embedded structs, an error turned into a `panic` and caught as an exception, a constructor returning an interface "for testability". Each of these is a premise of another language carried into one that does not share it.

## Extending a package without modifying it

The base package exposes extension points — the interfaces, function types and options it accepts — and an extension is a new package that imports the base and supplies one. The base never imports its extensions. Premises: maintainability, because the base is not edited and its tests do not change; lower cyclomatic complexity, because a variant is a type that satisfies an interface instead of another `case` in a `switch`; and no circular reference, because the arrow points from extension to base only.

`database/sql` is the model in the standard library. It defines the `driver` interfaces, and a driver is a separate module that implements them and registers itself; `database/sql` imports no driver.

**Inside one module**, an extension is a package beside the base, and nothing more is needed. This is the default, and the official module layout page starts there.

**Across modules**, when the base and its extensions are released and versioned apart — "A module is a collection of packages that are released, versioned, and distributed together" (the module reference) — each lives in its own module, and the recommended tool for developing them together is a Go workspace: a `go.work` file, added in Go 1.18 by accepted proposal golang/go#45713, which lists the module directories so that the `go` command builds them as one set of main modules without a `replace` in any `go.mod`. It ships in the toolchain, needs no install and is understood by `gopls`, which is the reason it is recommended over the alternatives.

**When an alternative is better.** A `replace` directive pointing at a local path is the older mechanism and is still right in one case: a single module that must build against an unreleased fork, permanently, in CI, where a workspace would be a second file to keep in step. A build system such as Bazel is the sturdier choice for a repository with many modules in several languages, where the build graph and its caching outgrow the `go` command; it is a large adoption and is not justified for a Go repository of a handful of modules. And a multi-module repository is itself the wrong choice when the packages are never released apart: a second `go.mod` buys independent versioning and costs a release process per module, which is a cost with nothing in return inside one service.

Whichever is used, the modules of one repository require each other in one direction only, which condition 3 of [`rules/package-boundaries.md`](../rules/package-boundaries.md) holds.

## Tests sit beside the code

A test file sits beside the file it tests, as `x_test.go` for `x.go`, which [`rules/test-placement.md`](../rules/test-placement.md) holds with a hook. A test in `package orders` can reach unexported identifiers; a test in `package orders_test`, in the same directory, sees only the exported surface and is the right place for a test that documents the API. Fixtures go in `testdata/`, which the `go` tool ignores. [`docs/testing.md`](testing.md) covers both.

## Where this stops

**No directory tree is prescribed beyond `cmd/` and `internal/`.** A project's own component map names its folders, and the fundamentals plugin's component-map skill is where a builder reads it. This page argues the Go mechanics that any such map is expressed in.

**Architecture is not here.** Whether a service has a domain layer, use cases and adapters, and what each may know, is the backend plugin's subject and the fundamentals' rules on domain models. This page says only that Go's interface and import rules are how those boundaries are kept.

**Release engineering for multi-module repositories is not covered.** Tagging each module, ordering their releases and keeping `go.work` out of a published module's build are the module reference's subject; this page argues only when several modules are worth having and how they depend on each other.

**Package size has no threshold.** No source measures the right number of files or lines in a package, and this page invents none. A package that is hard to name is the signal.
