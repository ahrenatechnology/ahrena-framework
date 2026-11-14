---
id: module-boundaries
type: rule
clade: engineering
subclade: typescript
title: Module boundaries and import acyclicity
statement: The first-party import graph is acyclic, a deferred import is still an edge, and a package is reached only through its name and its exports.
enforcement: hook
enforced-by: hooks/check-boundaries.py
references:
  - docs/project-layout.md
---

# Module boundaries and import acyclicity

A TypeScript codebase is a graph of modules grouped into packages. An import edge never closes a loop, and an import that crosses into another package goes through the entry that package chose to publish, never through its files.

Every condition below is decided by `hooks/check-boundaries.py`, which builds the graph from the source with the standard library and resolves each specifier the way TypeScript does under `moduleResolution: nodenext` and `bundler`. [`docs/project-layout.md`](../docs/project-layout.md) argues the layout these conditions protect and where the layers of an application sit inside it.

## This is the TypeScript instance of dependency inversion and of acyclic dependencies

The language-agnostic engineering plugin carries a SOLID rule whose sixth condition is dependency inversion, and that condition leaves the layer map to the language. This rule fills in the part TypeScript's tooling decides — the graph and the package surface — and leaves the layer map to [`docs/project-layout.md`](../docs/project-layout.md), because a TypeScript project has no layout convention a script could hold every codebase to. The link is an ordinary relative path, as `foundation/rules/pilars.md` says a body link crosses a plugin: [`solid.md`](../../fundamentals/rules/solid.md), condition 6.

## What counts as a node and as an edge

A node is a source file: `.ts`, `.tsx`, `.mts`, `.cts`, and the JavaScript extensions beside them, because a mixed project's cycle can pass through a `.js` file.

An edge is a specifier in an `import … from`, an `export … from`, a side-effect `import "…"`, a dynamic `import("…")` or a `require("…")`, resolved against the importing file. A `.js` specifier reaches the `.ts` file beside it, `.mjs` reaches `.mts` and `.cjs` reaches `.cts`, as `nodenext` requires them written; an extensionless specifier tries each extension and then the directory's `index`. A specifier that resolves to no file in the tree is a third party's and adds no edge.

## Conditions

Each of these is decided by `hooks/check-boundaries.py`.

1. **The first-party import graph is acyclic.** A cycle is reported as the cycle — every module in it, in import order, with the line of each edge — and never as a set of files, because the set does not say which import to delete. In ECMAScript modules a cycle is not merely untidy: a module evaluated while its importer is still mid-evaluation sees that importer's `let`, `const` and `class` bindings uninitialized, and reading one throws `ReferenceError: Cannot access 'x' before initialization`. Whether that happens depends on which module the program imports first, so the same cycle passes a test and fails in production.

2. **A type-only import is not an edge, and nothing else is exempt.** `import type …` and `export type … from` are erased whole by the compiler and by Node's type stripping, so they load nothing and close no cycle. `import { type A } from "./a"` is not type-only: under `verbatimModuleSyntax`, and in Node's type stripping, it is rewritten to `import {} from "./a"`, which still loads and evaluates the module. A dynamic `import()` and a `require()` are edges like any other, and a cycle that runs through one is reported with that edge marked deferred: moving an import into a function changes when the coupling is paid and nothing else.

3. **A relative import does not reach into another package's directory.** A package is a directory with its own `package.json`. `../../packages/billing/src/charge` from another package works on the author's machine and bypasses everything the package's `exports` says about what is public; it also ties the importer to a path that the package may move in any release. The fix is to import the package by its name.

4. **A first-party package imported by name is imported at its root or at a subpath its `exports` declares.** A subpath matches an `exports` key exactly or through its single `*` pattern, as Node resolves them. A package with no `exports` field publishes no subpath at all under this condition, and the fix is to declare the entry points, not to deep-import past them: Node itself refuses an unexported subpath of a package that declares `exports` with `ERR_PACKAGE_PATH_NOT_EXPORTED`, and this condition holds a first-party package to that line before it is published.

## Where this stops

**One cycle is reported per strongly connected component.** A knot of modules that import each other contains many loops and one defect; breaking the reported loop and re-running is the procedure, and it terminates.

**A path alias is not resolved.** `compilerOptions.paths` maps `@/domain/order` to a file, and the hook does not read it; an edge through an alias is invisible, and a cycle that needs one to close is not reported. Resolving aliases means reimplementing `paths`, `baseUrl` (which 6.0 deprecates) and the bundler's own alias table, and they disagree. A project that leans on aliases adds a second detector — dependency-cruiser and madge both report cycles through them — and [`docs/project-layout.md`](../docs/project-layout.md) argues for relative imports inside a package and package names across packages, which this hook reads in full.

**A first-party package imported by name adds no edge.** Conditions 3 and 4 hold the package boundary; a cycle between two workspace packages that import each other by name is a cycle in the workspace's dependency graph, and the package manager reports it when it orders the build.

**A third-party deep import is not read.** `lodash/fp` is a public entry of a package that has no `exports`, and `zod/mini` is a declared one; telling them from `some-lib/dist/internal/x` needs the installed package, which a gate does not have. Node enforces `exports` at runtime for a package that declares it, and review reads the rest.

**A string built at runtime is not an edge.** `import(\`./locales/${lang}\`)` and a plugin registry are invisible, as in every static graph.

**Measured on four public codebases** — about 580,000 lines, at the commits [`docs/toolchain.md`](../docs/toolchain.md) records — the hook reported ten cycles and twenty-five relative imports across packages. The three cycles read in full were real: in each, both edges load values, and none is type-only. The cross-package imports were mostly a workspace's test and benchmark scripts reaching into the library's `src`, which is the shape condition 3 exists to make a decision rather than a habit.
