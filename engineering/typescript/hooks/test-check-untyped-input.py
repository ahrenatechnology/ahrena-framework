#!/usr/bin/env python3
"""Tests for check-untyped-input.py.

Covers #289/AC-3 for condition 2 of rules/runtime-validation.md: a value that
enters untyped is not given a type by assertion. The carve-outs pinned here:
asserting to `unknown` is the honest move and passes, a schema's `parse` is
the dishonest move's replacement and passes, and the same words in a string or
a comment are not code.

Also covers #289/AC-6: the last case runs the framework's artifact gate over
the whole repository, so a change to this plugin that breaks the gate fails
here as well as in CI.

Usage:
    python3 engineering/typescript/hooks/test-check-untyped-input.py
"""

from __future__ import annotations

import subprocess
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

from harness import Case, case, main  # noqa: E402

HOOK = Path(__file__).resolve().parent / "check-untyped-input.py"
REPOSITORY = Path(__file__).resolve().parents[3]
GATE = REPOSITORY / "foundation" / "hooks" / "validate-artifacts.py"

PARSE_AS = """
interface Order { id: string }
export function read(raw: string): Order {
  return JSON.parse(raw) as Order;
}
"""

PARSE_ANGLE = """
export const order = <Order>JSON.parse(raw);
"""

RESPONSE_AS = """
export async function load(url: string): Promise<Order> {
  const response = await fetch(url);
  return (await response.json()) as Order;
}
"""

RESPONSE_PROMISE_AS = """
export function load(response: Response): Promise<Order> {
  return response.json() as Promise<Order>;
}
"""

ENV_AS = """
export const mode = process.env.APP_MODE as "live" | "test";
export const region = process.env["AWS_REGION"] as string;
"""

NESTED_CALL = """
export const order = JSON.parse(read(path, "utf8")) as Order;
"""

HONEST = """
import { z } from "zod";
const Order = z.object({ id: z.string() });
export function read(raw: string): z.infer<typeof Order> {
  const data: unknown = JSON.parse(raw);
  const body = (await response.json()) as unknown;
  const mode = process.env.APP_MODE;
  return Order.parse(data);
}
"""

NOT_CODE = """
// JSON.parse(raw) as Order is what this module refuses to do
export const doc = "JSON.parse(raw) as Order";
"""

CASES: list[Case] = [
    case("a schema parse passes", {"a.ts": HONEST}, ["no failures"], ok=True),
    case("JSON.parse asserted fails", {"a.ts": PARSE_AS}, ["condition 2", "a.ts:4", "JSON.parse"]),
    case("JSON.parse asserted with angle brackets fails", {"a.ts": PARSE_ANGLE}, ["condition 2", "JSON.parse"]),
    case("a response body asserted fails", {"a.ts": RESPONSE_AS}, ["condition 2", "a.ts:4", ".json()"]),
    case("a response promise asserted fails", {"a.ts": RESPONSE_PROMISE_AS}, ["condition 2", ".json()"]),
    case("an environment variable asserted fails", {"a.ts": ENV_AS}, ["condition 2", "a.ts:2", "a.ts:3", "process.env"]),
    case("a nested call inside JSON.parse is followed to its close", {"a.ts": NESTED_CALL}, ["condition 2"]),
    case("the same words in a string or a comment pass", {"a.ts": NOT_CODE}, ["no failures"], ok=True),
]


def gate_passes() -> int:
    """#289/AC-6: the artifact gate passes over the repository."""
    result = subprocess.run([sys.executable, "-B", str(GATE), str(REPOSITORY)], capture_output=True, text=True)
    if result.returncode == 0:
        print("ok    the artifact gate passes over the repository")
        return 0
    print("FAIL  the artifact gate passes over the repository")
    for line in (result.stdout + result.stderr).splitlines():
        print(f"      {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main(HOOK, CASES) | gate_passes())
