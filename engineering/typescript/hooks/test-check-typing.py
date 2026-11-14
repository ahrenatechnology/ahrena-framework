#!/usr/bin/env python3
"""Tests for check-typing.py.

Covers #289/AC-3 for the five conditions of rules/typing.md the hook decides.
Every condition is pinned by a failing fixture and by the carve-out it must
not flag, because the carve-outs are where a lexical detector goes wrong:
`any` inside a string, a comment or a property name is not a type; a tool
directive is not a reason, unless it carries the description its own syntax
gives it; a `.d.ts` someone else generated is not the project's surface.

Usage:
    python3 engineering/typescript/hooks/test-check-typing.py
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

from harness import Case, case, main  # noqa: E402

HOOK = Path(__file__).resolve().parent / "check-typing.py"

STRICT = '{\n  // comments and trailing commas are JSONC, as tsc reads it\n  "compilerOptions": {\n    "noUncheckedIndexedAccess": true,\n  },\n}\n'

CLEAN = """
export function add(left: number, right: number): number {
  return left + right;
}
"""

# --- condition 2: tsconfig ---------------------------------------------------

STRICT_OFF = '{ "compilerOptions": { "strict": false, "noUncheckedIndexedAccess": true } }'
FAMILY_OFF = '{ "compilerOptions": { "strictNullChecks": false, "noUncheckedIndexedAccess": true } }'
NO_INDEX = '{ "compilerOptions": { "strict": true } }'
BASE = '{ "compilerOptions": { "noUncheckedIndexedAccess": true } }'
CHILD = '{ "extends": "./tsconfig.base.json", "include": ["src"] }'
CHILD_UNSETS = '{ "extends": "./tsconfig.base.json", "compilerOptions": { "noUncheckedIndexedAccess": false } }'
PACKAGE_BASE = '{ "extends": "@tsconfig/strictest/tsconfig.json" }'
INSTALLED_BASE = '{ "compilerOptions": { "noUncheckedIndexedAccess": true } }'

# --- condition 4: explicit any ----------------------------------------------

BARE_ANY = """
export function parse(raw: any): number {
  return raw.length;
}
"""

ANY_IN_GENERIC = """
export const cache: Map<string, any> = new Map();
"""

AS_ANY = """
export function width(el: unknown): number {
  return (el as any).width;
}
"""

THREE_ON_ONE_LINE = """
export type Loose = Map<any, any> | Set<any>;
"""

ANY_WITH_REASON = """
// the plugin host passes an untyped bag; narrowed by readSettings below
export function load(settings: any): void {
  readSettings(settings);
}
"""

ANY_WITH_SAME_LINE_REASON = """
export function load(settings: any /* host API ships no types, see #12 */): void {}
"""

ANY_WITH_DIRECTIVE_ONLY = """
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function load(settings: any): void {}
"""

ANY_WITH_DIRECTIVE_REASON = """
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- host API ships no types
export function load(settings: any): void {}
"""

ANY_NOT_A_TYPE = """
const message = "pass any value: it is coerced";
// any comment that says any
const flags = { any: true, other: false };
const matched = list.some((item) => item.any);
const pattern = /any: [a-z]+/;
const label = `any: ${count}`;
export function anyOf(values: readonly string[]): boolean {
  return values.length > 0 && flags.any;
}
"""

# --- condition 5: ts directives ---------------------------------------------

TS_IGNORE = """
// @ts-ignore
const total: number = "1";
"""

TS_NOCHECK = """// @ts-nocheck
export const x = 1;
"""

EXPECT_ERROR_BARE = """
// @ts-expect-error
const total: number = "1";
"""

EXPECT_ERROR_DESCRIBED = """
// @ts-expect-error: the fixture is deliberately the wrong type
const total: number = "1";
"""

TS_IGNORE_IN_STRING = """
export const doc = "write // @ts-ignore above the line";
"""

# --- condition 6: double assertion ------------------------------------------

DOUBLE_CAST = """
interface User { id: string }
export function adopt(row: { id: number }): User {
  return row as unknown as User;
}
"""

DOUBLE_CAST_WITH_REASON = """
interface User { id: string }
export function adopt(row: { id: number }): User {
  // the ORM brands ids as numbers at the type level and strings at runtime
  return row as unknown as User;
}
"""

SINGLE_UNKNOWN = """
export function erase(value: string): unknown {
  return value as unknown;
}
"""

# --- condition 7: exported return types -------------------------------------

EXPORT_NO_RETURN = """
export function total(rows: readonly number[]) {
  return rows.length;
}
"""

EXPORT_ASYNC_NO_RETURN = """
export async function load(id: string) {
  return id;
}
"""

EXPORT_DEFAULT_NO_RETURN = """
export default function handler(input: string) {
  return input;
}
"""

EXPORT_ARROW_NO_RETURN = """
export const total = (rows: readonly number[]) => rows.length;
"""

EXPORT_ARROW_TYPED_BINDING = """
type Total = (rows: readonly number[]) => number;
export const total: Total = (rows) => rows.length;
"""

EXPORT_ARROW_WITH_RETURN = """
export const total = async (rows: readonly number[]): Promise<number> => rows.length;
"""

EXPORT_GENERIC_WITH_RETURN = """
export function first<T extends { id: string }>(rows: readonly T[]): T | undefined {
  return rows[0];
}
"""

LOCAL_NO_RETURN = """
function total(rows: readonly number[]) {
  return rows.length;
}
export const count: number = total([1]);
"""

EXPORT_OVERLOADS = """
export function pick(value: string): string;
export function pick(value: number): number;
export function pick(value: string | number): string | number {
  return value;
}
"""

# --- the walk ----------------------------------------------------------------

VENDORED = """
export function parse(raw: any) {
  return raw;
}
"""

CASES: list[Case] = [
    case("a clean project passes", {"tsconfig.json": STRICT, "src/a.ts": CLEAN}, ["no failures"], ok=True),
    # --- condition 2
    case("strict turned off fails", {"tsconfig.json": STRICT_OFF}, ["condition 2", "turns strict off"]),
    case("a strict-family flag turned off fails", {"tsconfig.json": FAMILY_OFF}, ["condition 2", "strictNullChecks"]),
    case("noUncheckedIndexedAccess unset fails", {"tsconfig.json": NO_INDEX}, ["condition 2", "noUncheckedIndexedAccess"]),
    case(
        "a relative base that sets the flag passes",
        {"tsconfig.base.json": BASE, "tsconfig.json": CHILD},
        ["no failures"],
        ok=True,
    ),
    case(
        "a child that unsets the base's flag fails",
        {"tsconfig.base.json": BASE, "tsconfig.json": CHILD_UNSETS},
        ["condition 2", "tsconfig.json"],
    ),
    case(
        "a package base that is not installed fails, naming it",
        {"tsconfig.json": PACKAGE_BASE},
        ["condition 2", "@tsconfig/strictest"],
    ),
    case(
        "a package base that is installed is read",
        {"tsconfig.json": PACKAGE_BASE, "node_modules/@tsconfig/strictest/tsconfig.json": INSTALLED_BASE},
        ["no failures"],
        ok=True,
    ),
    # --- condition 4
    case("a bare any fails", {"tsconfig.json": STRICT, "a.ts": BARE_ANY}, ["condition 4", "a.ts:2"]),
    case("an any inside a generic fails", {"tsconfig.json": STRICT, "a.ts": ANY_IN_GENERIC}, ["condition 4"]),
    case("three on one line are one finding", {"tsconfig.json": STRICT, "a.ts": THREE_ON_ONE_LINE}, ["1 failure(s)", "condition 4"]),
    case("as any fails", {"tsconfig.json": STRICT, "a.ts": AS_ANY}, ["condition 4", "a.ts:3"]),
    case("an any with a reason above passes", {"tsconfig.json": STRICT, "a.ts": ANY_WITH_REASON}, ["no failures"], ok=True),
    case(
        "an any with a reason on its line passes",
        {"tsconfig.json": STRICT, "a.ts": ANY_WITH_SAME_LINE_REASON},
        ["no failures"],
        ok=True,
    ),
    case(
        "a lint directive alone is not a reason",
        {"tsconfig.json": STRICT, "a.ts": ANY_WITH_DIRECTIVE_ONLY},
        ["condition 4"],
    ),
    case(
        "a lint directive with its description is a reason",
        {"tsconfig.json": STRICT, "a.ts": ANY_WITH_DIRECTIVE_REASON},
        ["no failures"],
        ok=True,
    ),
    case(
        "any in strings, comments, keys, regexes and templates is not a type",
        {"tsconfig.json": STRICT, "a.ts": ANY_NOT_A_TYPE},
        ["no failures"],
        ok=True,
    ),
    # --- condition 5
    case("@ts-ignore fails", {"tsconfig.json": STRICT, "a.ts": TS_IGNORE}, ["condition 5", "@ts-ignore"]),
    case("@ts-nocheck fails", {"tsconfig.json": STRICT, "a.ts": TS_NOCHECK}, ["condition 5", "@ts-nocheck"]),
    case("a bare @ts-expect-error fails", {"tsconfig.json": STRICT, "a.ts": EXPECT_ERROR_BARE}, ["condition 5"]),
    case(
        "a described @ts-expect-error passes",
        {"tsconfig.json": STRICT, "a.ts": EXPECT_ERROR_DESCRIBED},
        ["no failures"],
        ok=True,
    ),
    case(
        "a directive inside a string is not a directive",
        {"tsconfig.json": STRICT, "a.ts": TS_IGNORE_IN_STRING},
        ["no failures"],
        ok=True,
    ),
    # --- condition 6
    case("a double assertion fails", {"tsconfig.json": STRICT, "a.ts": DOUBLE_CAST}, ["condition 6", "a.ts:4"]),
    case(
        "a double assertion with a reason passes",
        {"tsconfig.json": STRICT, "a.ts": DOUBLE_CAST_WITH_REASON},
        ["no failures"],
        ok=True,
    ),
    case("widening to unknown passes", {"tsconfig.json": STRICT, "a.ts": SINGLE_UNKNOWN}, ["no failures"], ok=True),
    # --- condition 7
    case("an exported function with no return type fails", {"tsconfig.json": STRICT, "a.ts": EXPORT_NO_RETURN}, ["condition 7", "total"]),
    case("an exported async function with no return type fails", {"tsconfig.json": STRICT, "a.ts": EXPORT_ASYNC_NO_RETURN}, ["condition 7", "load"]),
    case("a default export with no return type fails", {"tsconfig.json": STRICT, "a.ts": EXPORT_DEFAULT_NO_RETURN}, ["condition 7", "handler"]),
    case("an exported arrow with no return type fails", {"tsconfig.json": STRICT, "a.ts": EXPORT_ARROW_NO_RETURN}, ["condition 7", "total"]),
    case(
        "an exported arrow whose binding is typed passes",
        {"tsconfig.json": STRICT, "a.ts": EXPORT_ARROW_TYPED_BINDING},
        ["no failures"],
        ok=True,
    ),
    case(
        "an exported arrow with a return type passes",
        {"tsconfig.json": STRICT, "a.ts": EXPORT_ARROW_WITH_RETURN},
        ["no failures"],
        ok=True,
    ),
    case(
        "a generic with a constraint and a return type passes",
        {"tsconfig.json": STRICT, "a.ts": EXPORT_GENERIC_WITH_RETURN},
        ["no failures"],
        ok=True,
    ),
    case("a function that is not exported passes", {"tsconfig.json": STRICT, "a.ts": LOCAL_NO_RETURN}, ["no failures"], ok=True),
    case("overload signatures pass", {"tsconfig.json": STRICT, "a.ts": EXPORT_OVERLOADS}, ["no failures"], ok=True),
    # --- the walk
    case(
        "node_modules and dist are not walked",
        {"tsconfig.json": STRICT, "node_modules/x/index.ts": VENDORED, "dist/a.ts": VENDORED},
        ["no failures"],
        ok=True,
    ),
]

if __name__ == "__main__":
    sys.exit(main(HOOK, CASES))
