#!/usr/bin/env python3
"""Tests for check-boundaries.py.

Covers #289/AC-3 for the four conditions of rules/module-boundaries.md. The
carve-outs pinned here: a type-only import is erased and closes no cycle, a
`.js` specifier written for `nodenext` reaches the `.ts` file beside it, a
package imported by its name and an exported subpath is the public entry, and
a third-party package this tree does not hold is not read.

Usage:
    python3 engineering/typescript/hooks/test-check-boundaries.py
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

from harness import Case, case, main  # noqa: E402

HOOK = Path(__file__).resolve().parent / "check-boundaries.py"

# --- condition 1: cycles -----------------------------------------------------

CYCLE = {
    "src/a.ts": 'import { b } from "./b";\nexport const a = (): number => b();\n',
    "src/b.ts": 'import { c } from "./c.js";\nexport const b = (): number => c();\n',
    "src/c.ts": 'import { a } from "./a";\nexport const c = (): number => a();\n',
}

INDEX_CYCLE = {
    "src/orders/index.ts": 'export { place } from "./place";\n',
    "src/orders/place.ts": 'import { audit } from "../audit";\nexport const place = (): void => audit();\n',
    "src/audit.ts": 'import { place } from "./orders";\nexport const audit = (): void => void place;\n',
}

TYPE_ONLY = {
    "src/a.ts": 'import type { B } from "./b";\nexport const a = (value: B): B => value;\n',
    "src/b.ts": 'import { a } from "./a";\nexport type B = { a: typeof a };\n',
}

INLINE_TYPE_ONLY = {
    "src/a.ts": 'import { type B } from "./b";\nexport const a = (value: B): B => value;\n',
    "src/b.ts": 'import { a } from "./a";\nexport type B = { a: typeof a };\n',
}

EXPORT_TYPE_ONLY = {
    "src/a.ts": 'export type { B } from "./b";\nexport const a = 1;\n',
    "src/b.ts": 'import { a } from "./a";\nexport type B = typeof a;\n',
}

DEFERRED = {
    "src/a.ts": 'import { b } from "./b";\nexport const a = (): number => b();\n',
    "src/b.ts": 'export async function b(): Promise<number> {\n  const { a } = await import("./a");\n  return a();\n}\n',
}

REQUIRE = {
    "src/a.cts": 'const { b } = require("./b.cjs");\nexport const a = 1;\n',
    "src/b.cts": 'const { a } = require("./a.cjs");\nexport const b = 2;\n',
}

ACYCLIC = {
    "src/a.ts": 'import { b } from "./b";\nimport "./polyfill";\nimport express from "express";\nexport const a = (): number => b();\n',
    "src/b.ts": "export const b = (): number => 1;\n",
    "src/polyfill.ts": "export {};\n",
    "src/note.ts": 'export const doc = "import { a } from \'./a\'";\n',
}

# --- conditions 3 and 4: packages -------------------------------------------

WORKSPACE_PACKAGE = '{ "name": "@acme/billing", "exports": { ".": "./src/index.ts", "./testing": "./src/testing.ts" } }'
WORKSPACE_WILDCARD = '{ "name": "@acme/ui", "exports": { ".": "./src/index.ts", "./icons/*": "./src/icons/*.ts" } }'
WORKSPACE_NO_EXPORTS = '{ "name": "@acme/legacy", "main": "./src/index.ts" }'

RELATIVE_INTO_PACKAGE = {
    "packages/billing/package.json": WORKSPACE_PACKAGE,
    "packages/billing/src/index.ts": 'export { charge } from "./charge";\n',
    "packages/billing/src/charge.ts": "export const charge = (): number => 1;\n",
    "apps/api/package.json": '{ "name": "api" }',
    "apps/api/src/main.ts": 'import { charge } from "../../../packages/billing/src/charge";\nexport const run = (): number => charge();\n',
}

DEEP_BY_NAME = {
    "packages/billing/package.json": WORKSPACE_PACKAGE,
    "packages/billing/src/index.ts": 'export { charge } from "./charge";\n',
    "packages/billing/src/charge.ts": "export const charge = (): number => 1;\n",
    "apps/api/package.json": '{ "name": "api", "dependencies": { "@acme/billing": "workspace:*" } }',
    "apps/api/src/main.ts": 'import { charge } from "@acme/billing/src/charge";\nexport const run = (): number => charge();\n',
}

PUBLIC_BY_NAME = {
    "packages/billing/package.json": WORKSPACE_PACKAGE,
    "packages/billing/src/index.ts": "export const charge = (): number => 1;\n",
    "packages/billing/src/testing.ts": "export const fake = (): number => 0;\n",
    "packages/ui/package.json": WORKSPACE_WILDCARD,
    "packages/ui/src/index.ts": "export const ui = 1;\n",
    "packages/ui/src/icons/star.ts": "export const star = 1;\n",
    "apps/api/package.json": '{ "name": "api", "dependencies": { "@acme/billing": "workspace:*", "@acme/ui": "workspace:*" } }',
    "apps/api/src/main.ts": (
        'import { charge } from "@acme/billing";\n'
        'import { fake } from "@acme/billing/testing";\n'
        'import { star } from "@acme/ui/icons/star";\n'
        'import { z } from "zod/mini";\n'
        "export const run = (): number => charge() + fake() + star;\n"
    ),
}

NO_EXPORTS_DEEP = {
    "packages/legacy/package.json": WORKSPACE_NO_EXPORTS,
    "packages/legacy/src/index.ts": "export const old = 1;\n",
    "packages/legacy/src/inner.ts": "export const inner = 1;\n",
    "apps/api/package.json": '{ "name": "api", "dependencies": { "@acme/legacy": "workspace:*" } }',
    "apps/api/src/main.ts": 'import { inner } from "@acme/legacy/src/inner";\nexport const run = inner;\n',
}

INSIDE_ONE_PACKAGE = {
    "packages/billing/package.json": WORKSPACE_PACKAGE,
    "packages/billing/src/index.ts": 'export { charge } from "./domain/charge";\n',
    "packages/billing/src/domain/charge.ts": 'import { money } from "../money";\nexport const charge = (): number => money;\n',
    "packages/billing/src/money.ts": "export const money = 1;\n",
}

# --- conditions 5 and 6: the workspace's package graph ------------------------

PACKAGE_CYCLE = {
    "packages/a/package.json": '{ "name": "@acme/a", "exports": { ".": "./src/index.ts" }, "dependencies": { "@acme/b": "workspace:*" } }',
    "packages/a/src/index.ts": "export const a = 1;\n",
    "packages/b/package.json": '{ "name": "@acme/b", "exports": { ".": "./src/index.ts" }, "devDependencies": { "@acme/a": "workspace:*" } }',
    "packages/b/src/index.ts": "export const b = 2;\n",
}

PACKAGE_DAG = {
    "packages/a/package.json": '{ "name": "@acme/a", "exports": { ".": "./src/index.ts" }, "dependencies": { "@acme/b": "workspace:*", "zod": "^4.6.0" } }',
    "packages/a/src/index.ts": 'import { b } from "@acme/b";\nexport const a = b;\n',
    "packages/b/package.json": '{ "name": "@acme/b", "exports": { ".": "./src/index.ts" } }',
    "packages/b/src/index.ts": "export const b = 2;\n",
}

UNDECLARED = {
    "packages/a/package.json": '{ "name": "@acme/a", "exports": { ".": "./src/index.ts" } }',
    "packages/a/src/index.ts": 'import { b } from "@acme/b";\nexport const a = b;\n',
    "packages/b/package.json": '{ "name": "@acme/b", "exports": { ".": "./src/index.ts" } }',
    "packages/b/src/index.ts": "export const b = 2;\n",
}

CASES: list[Case] = [
    case("an acyclic tree passes", ACYCLIC, ["no failures"], ok=True),
    # --- condition 1
    case(
        "a three-module cycle fails and is reported as the cycle",
        CYCLE,
        ["condition 1", "src/a.ts:1 -> src/b.ts", "src/b.ts:1 -> src/c.ts", "src/c.ts:1 -> src/a.ts"],
    ),
    case("a cycle through a directory index fails", INDEX_CYCLE, ["condition 1", "src/orders/index.ts"]),
    case("a type-only import closes no cycle", TYPE_ONLY, ["no failures"], ok=True),
    # Under verbatimModuleSyntax, `import { type B }` is rewritten to
    # `import {} from "./b"` and still loads the module: it is an edge.
    case("an import whose every name is inline type is still an edge", INLINE_TYPE_ONLY, ["condition 1", "src/b.ts"]),
    case("a type-only re-export closes no cycle", EXPORT_TYPE_ONLY, ["no failures"], ok=True),
    # --- condition 2
    case("a dynamic import is the same edge", DEFERRED, ["condition 1", "deferred"]),
    case("require is an edge", REQUIRE, ["condition 1", "src/a.cts"]),
    # --- condition 3
    case("a relative import into another package fails", RELATIVE_INTO_PACKAGE, ["condition 3", "@acme/billing"]),
    case("relative imports inside one package pass", INSIDE_ONE_PACKAGE, ["no failures"], ok=True),
    # --- condition 4
    case("a deep import by name past exports fails", DEEP_BY_NAME, ["condition 4", "@acme/billing/src/charge"]),
    case("exported subpaths, wildcards and third parties pass", PUBLIC_BY_NAME, ["no failures"], ok=True),
    # --- conditions 5 and 6
    case("a cycle between workspace packages fails", PACKAGE_CYCLE, ["condition 5", "@acme/a -> @acme/b -> @acme/a"]),
    case("a workspace whose packages point one way passes", PACKAGE_DAG, ["no failures"], ok=True),
    case("a package imported but not declared fails", UNDECLARED, ["condition 6", "@acme/b", "packages/a/package.json"]),
    case("a subpath of a package with no exports fails", NO_EXPORTS_DEEP, ["condition 4", "declares no exports"]),
]

if __name__ == "__main__":
    sys.exit(main(HOOK, CASES))
