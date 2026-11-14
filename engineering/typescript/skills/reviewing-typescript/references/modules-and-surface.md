# TypeScript modules and surface

Opened by step 4 of `SKILL.md` when the change touches an export, a barrel, a public declaration or a `.d.ts`. These are the conditions about what the change offers the code that imports it.

The import graph and the package boundary are `rules/module-boundaries.md`, decided by `hooks/check-boundaries.py`: a cycle, a relative import into another package, and a deep import past a package's `exports` are reported under that rule, not here. An exported function with no return type is condition 7 of `rules/typing.md`.

### TS-15 A barrel that pulls in more than the importer needs

- **State:** a new or widened `index.ts` that re-exports a whole directory, so importing one name loads and runs every module's top level — and defeats tree-shaking.
- **Detect:** read the barrel the change adds to. A side effect at a re-exported module's top level now runs on any import from the barrel.
- **Exempt:** a package's single curated public entry point, with no side-effectful modules behind it.
- **Correct:** export the names the surface needs; import from the module, not the barrel, inside the package.

### TS-16 A default export where a named one was meant

- **State:** a `export default` on a shared module, which lets each importer rename it freely and breaks `import *` tooling and refactors.
- **Detect:** the project's convention decides this; read whether its other modules use named exports.
- **Exempt:** a framework that requires a default export (a Next.js page, a dynamic import target).
- **Correct:** a named export, matching the project's convention. If the project has no convention, it is a `question`.

### TS-17 A breaking change to an exported type with no version

- **State:** an exported type, interface or function signature narrowed or renamed — a field removed, a parameter added without a default, a return widened — that a consumer outside this module compiles against.
- **Detect:** compare the exported surface with its base version; find importers. This is the contract question, and `ahrena-engineering-quality:skills/detecting-contract-breaks/SKILL.md` owns it when the surface is a published contract.
- **Exempt:** a purely additive change (an optional field, a new overload).
- **Correct:** keep it compatible, or ship it as a version per the contract-break procedure.

### TS-18 A type-only import or export not marked

- **State:** a name used only as a type imported without `type`, in a project with `verbatimModuleSyntax`, which keeps the import and loads the module at runtime; or `import { type A }` where every name is a type, which `verbatimModuleSyntax` rewrites to `import {} from "…"` and so still loads the module.
- **Detect:** read what each imported name is used as. Under condition 2 of `rules/module-boundaries.md`, only a statement-level `import type` is erased, so the other two forms are edges of the graph and can close a cycle.
- **Exempt:** a project without `verbatimModuleSyntax` or `isolatedModules`, where the compiler elides unused imports itself.
- **Correct:** `import type` / `export type` at the statement level for type-only names.

### TS-19 A module-level side effect

- **State:** work at the top level of a module that runs on import — a network call, a singleton built eagerly, a global registered, `console` output, reading `process.env` into a frozen constant.
- **Detect:** read the module's top level. It runs once at first import, in an order the importer does not control, before any function is called.
- **Exempt:** a pure constant, or an intentional registration a comment explains.
- **Correct:** move the work into a function or a lazily-initialised accessor the consumer calls.
