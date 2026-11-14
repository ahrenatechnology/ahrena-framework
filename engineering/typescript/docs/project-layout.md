---
id: project-layout
type: doc
clade: engineering
subclade: typescript
title: Laying out a TypeScript project
summary: How a TypeScript codebase is cut into packages and modules - the module settings for an application, a bundled app and a library, a package's public entry, imports across and inside packages, where the layers of a service sit, where tests live, and where the program is assembled.
references:
  - rules/module-boundaries.md
---

# Laying out a TypeScript project

This is the companion to [`rules/module-boundaries.md`](../rules/module-boundaries.md). The rule holds the graph acyclic and the package boundary closed; this argues the layout that makes both easy, and the choices the rule leaves to a project because no script could hold every codebase to one answer.

## Three kinds of code, three module settings

`module` and `moduleResolution` decide how a specifier becomes a file, and the right pair depends on what runs the output. TypeScript's own guide, *Modules — Choosing Compiler Options*, gives three answers, and this plugin takes them unchanged.

**An application Node runs** uses `"module": "nodenext"`, which implies `moduleResolution: nodenext`. Relative specifiers carry the extension of the emitted file — `./order.js` for `order.ts` — because that is what Node will look for at runtime; the guide adds to "set `"type": "module"` or use `.mts` files if you intend to emit ES modules". Under Node's type stripping the file that runs is the `.ts` file itself, and a `.ts` specifier with `allowImportingTsExtensions` is the alternative; a project picks one and holds to it.

**An application a bundler builds** — a browser app, a Next.js server — uses `"module": "esnext"` with `"moduleResolution": "bundler"`. Extensions may be omitted because the bundler resolves them. The guide recommends "*not* to set `{ "type": "module" }` or use `.mts` files in bundler projects for now".

**A library** uses `"module": "node18"`, with no `moduleResolution` beside it. The guide's reason is the one that decides it: "When a codebase is compatible with Node.js's module system, it almost always works in bundlers as well." The reverse is not true, so a library written under `bundler` can publish code that only bundlers can load.

The hook of [`rules/module-boundaries.md`](../rules/module-boundaries.md) resolves all three: a `.js` specifier reaches the `.ts` file beside it, and an extensionless one tries each extension and the directory's index.

## A package and its public entry

A package is a directory with a `package.json`, and it is the unit of publication, of versioning and of the boundary condition 3 of the rule holds. Its `exports` field is its public surface: Node's documentation says that once `exports` is defined, "all subpaths of the package are encapsulated and no longer available to importers". So every package declares `exports`, even one that is never published, because that is what lets condition 4 tell an entry from a file.

The root entry is one `src/index.ts` that exports what the package offers, by name. It is the only barrel in the package. A barrel deeper inside — an `index.ts` that re-exports a whole directory — makes importing one name load every module beside it, is the most common place an import cycle hides (one of the cycles the rule's hook found in a public codebase ran through exactly such a file), and is TS-15 of `reviewing-typescript`. Inside the package, a module imports the module it needs.

A subpath is exported on purpose, for a second audience: `"./testing"` for the fakes a consumer's tests need, `"./client"` for the half of a package that runs in a browser. Each is a public entry with the same weight as the root.

## Imports across and inside packages

**Across packages, by name.** `import { charge } from "@acme/billing"`, resolved through the workspace (pnpm's `workspace:` protocol, [`libraries.md`](libraries.md)), so the importer depends on the package's declared surface and its version, not on where its files sit.

**Inside a package, relative.** `import { money } from "../money.js"`. A relative import says where the file is, Node and every bundler resolve it the same way, and the rule's hook reads it.

**Not through `paths` aliases.** `compilerOptions.paths` maps a prefix such as `@/` to a directory for the compiler only: Node's type stripping ignores `tsconfig.json`, so an alias that type-checks fails at runtime unless a bundler or a loader repeats the mapping, and the rule's hook cannot see through one. Where a long relative path is the problem, it is usually a package boundary that has not been drawn yet; where it is not, Node's own subpath imports — an `"imports"` field in `package.json` with `#`-prefixed keys — are understood by Node and by TypeScript alike.

## The layers of a service

A service is laid out by bounded context, and each context by layer, inside out:

```
src/
  orders/
    domain/          entities, value objects, domain errors; imports nothing below
    application/     use cases and the ports they need; imports domain
    infrastructure/  adapters that implement the ports: database, HTTP, queues
  main.ts            the composition root
```

The direction is the one condition 6 of the fundamentals' SOLID rule states: policy does not import mechanism. Unlike Python's, this plugin's boundary rule does not hold the layer names, because TypeScript projects have no convention a script could hold every codebase to, and a configurable layer map is a setting rather than a rule. A project that wants the direction checked declares it in dependency-cruiser, which [`libraries.md`](libraries.md) names; the order in which the layers are built test-first is the backend clade's `building-backend-inside-out`.

## Where the program is assembled

**`main.ts` builds the object graph and starts the program; nothing else does work at import.** It parses the configuration ([`libraries.md`](libraries.md), "Configuration"), constructs the adapters, hands them to the use cases, and starts the server or the consumer. A module that opens a connection, reads `process.env` into a constant, or registers a global at its top level does that work for every importer, tests included, in an order none of them controls — TS-19 of `reviewing-typescript`.

## Where tests live

**Beside the code: `order.ts` and `order.test.ts` in one directory.** Vitest's default `include` and Node's test runner both find `*.test.ts` files wherever they are, and a test beside its module is found, read and deleted with it. A test that needs a running database or another service sits under the package's `test/` directory and runs as a separate command, as [`testing.md`](testing.md) argues.

## Generated code

**In its own directory, written by its generator, never edited by hand**: an OpenAPI client, a database's table types, a protobuf module. The rules' hooks are given paths, and the generated directory is left out of them in the command line where the exclusion is visible, as the Python plugin's typing rule asks for its own carve-outs.

## Where this stops

**This is not a framework's layout.** Next.js, Nest, Angular and the rest bring a directory structure of their own, and inside them the framework's wins; the package boundary and the import rules above still hold around it. The frontend clade's `ahrena-engineering-frontend` owns the layout of components and state.

**It does not decide how many packages a repository holds.** One deployable and its libraries is the common case; the boundary rule applies the same way to two packages or forty.
