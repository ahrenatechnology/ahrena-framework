#!/usr/bin/env python3
"""Tests for check-promises.py.

Covers #289/AC-3 for the four conditions of rules/promises.md the hook
decides. The carve-outs pinned here: a synchronous `forEach` callback, a
`catch` that does something or says why it does nothing, a process listener
that ends the process, and the two `--unhandled-rejections` modes that keep
Node's failure loud.

Usage:
    python3 engineering/typescript/hooks/test-check-promises.py
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

from harness import Case, case, main  # noqa: E402

HOOK = Path(__file__).resolve().parent / "check-promises.py"

CLEAN = """
export async function saveAll(rows: readonly string[]): Promise<void> {
  for (const row of rows) {
    await save(row);
  }
  await Promise.all(rows.map(async (row) => save(row)));
}
"""

# --- condition 2: async forEach ---------------------------------------------

ASYNC_FOREACH = """
export function saveAll(rows: readonly string[]): void {
  rows.forEach(async (row) => {
    await save(row);
  });
}
"""

ASYNC_FOREACH_FUNCTION = """
rows.forEach(async function (row) { await save(row); });
"""

SYNC_FOREACH = """
rows.forEach((row) => console.log(row));
const note = "rows.forEach(async (row) => x)";
"""

# --- condition 3: discarded rejection ---------------------------------------

EMPTY_CATCH_ARROW = """
export function fire(): void {
  save("x").catch(() => {});
}
"""

EMPTY_CATCH_FUNCTION = """
save("x").catch(function () {});
"""

EMPTY_CATCH_BLOCK = """
export async function load(): Promise<void> {
  try {
    await save("x");
  } catch (error) {}
}
"""

EMPTY_OPTIONAL_BINDING = """
try {
  run();
} catch {
}
"""

CATCH_WITH_REASON = """
export async function warm(): Promise<void> {
  try {
    await prefetch();
  } catch {
    // a cold cache is the state we started in; the next read fetches again
  }
  prefetch().catch(() => {
    /* best effort: the same as a miss */
  });
}
"""

CATCH_THAT_HANDLES = """
save("x").catch((error: unknown) => log.error({ error }, "save failed"));
try {
  run();
} catch (error) {
  report(error);
}
"""

# --- condition 4: process listeners -----------------------------------------

SWALLOWING_LISTENER = """
process.on("unhandledRejection", (reason) => {
  console.error(reason);
});
"""

SWALLOWING_UNCAUGHT = """
process.once('uncaughtException', function (error) {
  logger.error(error);
});
"""

EXITING_LISTENER = """
process.on("unhandledRejection", (reason) => {
  logger.fatal({ reason }, "unhandled rejection");
  process.exit(1);
});
process.on("uncaughtException", (error) => {
  throw error;
});
"""

LISTENER_BY_REFERENCE = """
process.on("unhandledRejection", onRejection);
"""

OTHER_EVENT = """
process.on("SIGTERM", () => {
  server.close();
});
"""

# --- condition 5: --unhandled-rejections ------------------------------------

PACKAGE_WARN = '{ "scripts": { "start": "node --unhandled-rejections=warn dist/main.js" } }'
DOCKERFILE_NONE = 'FROM node:24\nENV NODE_OPTIONS="--unhandled-rejections=none"\nCMD ["node", "main.js"]\n'
ENV_WARN_CODE = "NODE_OPTIONS=--unhandled-rejections=warn-with-error-code\n"
PACKAGE_STRICT = '{ "scripts": { "start": "node --unhandled-rejections=strict dist/main.js", "dev": "node --unhandled-rejections=throw x.js" } }'

CASES: list[Case] = [
    case("a clean module passes", {"a.ts": CLEAN}, ["no failures"], ok=True),
    # --- condition 2
    case("an async arrow passed to forEach fails", {"a.ts": ASYNC_FOREACH}, ["condition 2", "a.ts:3"]),
    case("an async function passed to forEach fails", {"a.ts": ASYNC_FOREACH_FUNCTION}, ["condition 2"]),
    case("a synchronous forEach passes", {"a.ts": SYNC_FOREACH}, ["no failures"], ok=True),
    # --- condition 3
    case("an empty catch arrow fails", {"a.ts": EMPTY_CATCH_ARROW}, ["condition 3", "a.ts:3"]),
    case("an empty catch function fails", {"a.ts": EMPTY_CATCH_FUNCTION}, ["condition 3"]),
    case("an empty catch block fails", {"a.ts": EMPTY_CATCH_BLOCK}, ["condition 3", "a.ts:5"]),
    case("an empty catch with no binding fails", {"a.ts": EMPTY_OPTIONAL_BINDING}, ["condition 3"]),
    case("a catch that says why it is empty passes", {"a.ts": CATCH_WITH_REASON}, ["no failures"], ok=True),
    case("a catch that handles passes", {"a.ts": CATCH_THAT_HANDLES}, ["no failures"], ok=True),
    # --- condition 4
    case("an unhandledRejection listener that only logs fails", {"a.ts": SWALLOWING_LISTENER}, ["condition 4", "unhandledRejection"]),
    case("an uncaughtException listener that only logs fails", {"a.ts": SWALLOWING_UNCAUGHT}, ["condition 4", "uncaughtException"]),
    case("listeners that exit or rethrow pass", {"a.ts": EXITING_LISTENER}, ["no failures"], ok=True),
    case("a listener on another event is not read", {"a.ts": OTHER_EVENT}, ["no failures"], ok=True),
    case("a listener passed by reference has no body to read", {"a.ts": LISTENER_BY_REFERENCE}, ["no failures"], ok=True),
    # --- condition 5
    case("warn in a package script fails", {"package.json": PACKAGE_WARN}, ["condition 5", "package.json", "warn"]),
    case("none in a Dockerfile fails", {"Dockerfile": DOCKERFILE_NONE}, ["condition 5", "Dockerfile:2"]),
    case("warn-with-error-code in an env file fails", {".env.production": ENV_WARN_CODE}, ["condition 5"]),
    case("strict and throw pass", {"package.json": PACKAGE_STRICT}, ["no failures"], ok=True),
]

if __name__ == "__main__":
    sys.exit(main(HOOK, CASES))
