---
id: project-layout
type: doc
clade: engineering
subclade: go
title: Packages, internal, cmd and the direction of dependencies
summary: How a Go module is laid out — packages named for what they provide, cmd/ for binaries, internal/ for what is not promised, dependencies pointing inward, interfaces declared by their consumer — and why the popular "standard layout" is not a standard.
references:
  - rules/api-surface.md
  - docs/libraries.md
---

# Packages, internal, cmd and the direction of dependencies

This is the companion of [`rules/api-surface.md`](../rules/api-surface.md): the rule states what an exported surface may not leak, and this document argues how a module is arranged so that the surface stays small enough to hold to it. It is about Go's mechanics — packages, `internal/`, `cmd/`, import direction. The architecture a service follows inside them, its domain and its ports, is the backend plugin's, and this page names only how Go expresses it.

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

## Dependencies point inward

The packages that hold the rules of the domain import nothing that does I/O: no `database/sql`, no `net/http`, no SDK client. The packages that do I/O — the HTTP handlers, the store, the client of another service — import the domain, never the reverse. Go makes this cheap to keep and the compiler makes cycles impossible: an import cycle is a build error, so a domain package that needs storage cannot import the store, and the design question is forced early.

The way the domain reaches storage without importing it is an interface the domain declares.

## Interfaces are declared by the package that uses them

Go Code Review Comments, *Interfaces*, says Go interfaces "generally belong in the package that uses values of the interface type, not the package that implements those values", that "the implementing package should return concrete (usually pointer or struct) types", and "Do not define interfaces before they are used". The Google Go style guide, decisions, *Interfaces*, says the consumer should define it.

This is what makes the inward dependency work. The `orders` package declares `type Store interface { Get(ctx context.Context, id ID) (Order, error) }` with exactly the methods it calls. The `postgres` package returns a concrete `*Store` that happens to satisfy it, and never mentions `orders.Store`. Go's interfaces are satisfied implicitly, so the implementer does not import the consumer, and the arrow stays pointing inward.

It is also why a fake in a test is small: the interface it implements has the two methods the consumer uses, not the twenty the implementation offers. [`docs/libraries.md`](libraries.md) recommends hand-written fakes for that reason.

The cost is that an interface is declared once per consumer, and two consumers of the same store may declare overlapping interfaces. That duplication is deliberate: each states what that consumer needs, and neither breaks when the other grows.

## Tests sit beside the code

A test file sits in the package it tests, as `x_test.go`. A test in `package orders` can reach unexported identifiers; a test in `package orders_test`, in the same directory, sees only the exported surface and is the right place for a test that documents the API. Fixtures go in `testdata/`, which the `go` tool ignores. [`docs/testing.md`](testing.md) covers both.

## Where this stops

**No directory tree is prescribed beyond `cmd/` and `internal/`.** A project's own component map names its folders, and the fundamentals plugin's component-map skill is where a builder reads it. This page argues the Go mechanics that any such map is expressed in.

**Architecture is not here.** Whether a service has a domain layer, use cases and adapters, and what each may know, is the backend plugin's subject and the fundamentals' rules on domain models. This page says only that Go's interface and import rules are how those boundaries are kept.

**Multi-module repositories are not covered.** A repository with several `go.mod` files, and a `go.work` file to develop them together, is occasionally right for a library family and is usually a cost a service does not need. The official layout page starts from one module, and so does this one.

**Package size has no threshold.** No source measures the right number of files or lines in a package, and this page invents none. A package that is hard to name is the signal.
