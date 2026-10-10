# TypeScript modules and surface

Opened by step 2 of `SKILL.md` when the change touches an export, a barrel, a public declaration or a `.d.ts`. These are the conditions about what the change offers the code that imports it.

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
- **Detect:** compare the exported surface with its base version; find importers. This is the contract question, and `ahrena-engineering-fundamentals:skills/detecting-contract-breaks/SKILL.md` owns it when the surface is a published contract.
- **Exempt:** a purely additive change (an optional field, a new overload).
- **Correct:** keep it compatible, or ship it as a version per the contract-break procedure.

### TS-18 A type-only import or export not marked

- **State:** a value import used only as a type (or the reverse) in a project with `isolatedModules`/`verbatimModuleSyntax`, which can pull a module into the runtime bundle that was only needed at compile time.
- **Detect:** read what each imported name is used as. A type imported as a value keeps the module in the build.
- **Exempt:** a project without those flags, where it does not matter.
- **Correct:** `import type` / `export type` for type-only names.

### TS-19 A module-level side effect

- **State:** work at the top level of a module that runs on import — a network call, a singleton built eagerly, a global registered, `console` output, reading `process.env` into a frozen constant.
- **Detect:** read the module's top level. It runs once at first import, in an order the importer does not control, before any function is called.
- **Exempt:** a pure constant, or an intentional registration a comment explains.
- **Correct:** move the work into a function or a lazily-initialised accessor the consumer calls.
