#!/usr/bin/env python3
"""Tests for check-tests.py.

Covers #289/AC-3 for the two conditions of rules/colocated-tests.md. The
carve-outs pinned here: a file that only declares types, constants or
re-exports holds no unit to test; a declaration file, a configuration file and
anything under a test or fixture directory is not a unit either; and a test
for a `.tsx` unit may be `.test.tsx` or `.spec.tsx`.

Usage:
    python3 engineering/typescript/hooks/test-check-tests.py
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

from harness import Case, case, main  # noqa: E402

HOOK = Path(__file__).resolve().parent / "check-tests.py"

FUNCTION = "export function total(rows: readonly number[]): number {\n  return rows.length;\n}\n"
ARROW = "export const total = (rows: readonly number[]): number => rows.length;\n"
CLASS = "export class Ledger {\n  readonly rows: number[] = [];\n}\n"
TEST = 'import { total } from "./order.js";\n'

TYPES_ONLY = """
export interface Order { id: string; total: (rows: number[]) => number }
export type Handler = (order: Order) => Promise<void>;
export type Status = "open" | "closed";
"""

TYPES_NO_SEMICOLONS = """
export type Callback<TResult = any> = (error?: Error | null, result?: TResult) => void
export type Handler<TEvent = unknown, TResult = unknown> = (
  event: TEvent,
  callback: Callback<TResult>,
) => void | Promise<TResult>
export interface Context {
  done: () => void
}
"""

CONSTANTS = 'export const LIMIT = 30;\nexport const NAMES = ["a", "b"] as const;\n'
BARREL = 'export { total } from "./order.js";\nexport type { Order } from "./types.js";\n'

CASES: list[Case] = [
    case(
        "a unit with its test beside it passes",
        {"src/order.ts": FUNCTION, "src/order.test.ts": TEST},
        ["no failures"],
        ok=True,
    ),
    # --- condition 1 #289
    case("a function with no test beside it fails", {"src/order.ts": FUNCTION}, ["condition 1", "src/order.ts", "order.test.ts"]),
    case("an exported arrow with no test fails", {"src/order.ts": ARROW}, ["condition 1"]),
    case("a class with no test fails", {"src/ledger.ts": CLASS}, ["condition 1", "ledger.test.ts"]),
    case("a test in another folder does not count", {"src/order.ts": FUNCTION, "test/order.test.ts": TEST}, ["condition 1"]),
    case(
        "a spec file beside a tsx unit passes",
        {"src/Button.tsx": "export function Button(): null {\n  return null;\n}\n", "src/Button.spec.tsx": TEST},
        ["no failures"],
        ok=True,
    ),
    case("a types-only module holds no unit", {"src/types.ts": TYPES_ONLY}, ["no failures"], ok=True),
    case("types with defaults and no semicolons hold no unit", {"src/types.ts": TYPES_NO_SEMICOLONS}, ["no failures"], ok=True),
    case("a constants module holds no unit", {"src/limits.ts": CONSTANTS}, ["no failures"], ok=True),
    case(
        "a barrel holds no unit",
        {"src/index.ts": BARREL, "src/order.ts": FUNCTION, "src/order.test.ts": TEST},
        ["no failures"],
        ok=True,
    ),
    case(
        "declarations, configuration and fixtures are not units",
        {
            "src/env.d.ts": "declare function boot(): void;\n",
            "vitest.config.ts": "export default { test: { include: [] } };\nexport const f = (): number => 1;\n",
            "src/__fixtures__/make.ts": FUNCTION,
            "test/helpers/make.ts": FUNCTION,
        },
        ["no failures"],
        ok=True,
    ),
    # --- condition 2 #289
    case("a test whose unit is gone fails", {"src/order.test.ts": TEST}, ["condition 2", "src/order.test.ts", "order.ts"]),
    case(
        "a test under a test directory is not an orphan",
        {"test/checkout.test.ts": TEST},
        ["no failures"],
        ok=True,
    ),
]

if __name__ == "__main__":
    sys.exit(main(HOOK, CASES))
