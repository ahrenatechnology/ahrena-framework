---
id: error-handling
type: doc
clade: engineering
subclade: typescript
title: Errors in TypeScript - what is thrown, what is returned, and what a handler owes
summary: Which failures are thrown and which are returned as values, how a caught value of type unknown is narrowed, how context is added without losing the cause, what a handler at a boundary turns a failure into, and the typescript-eslint rules that hold the mechanics.
references:
  - rules/promises.md
  - rules/runtime-validation.md
---

# Errors in TypeScript: what is thrown, what is returned, and what a handler owes

[`rules/promises.md`](../rules/promises.md) refuses the handler that discards a failure, and [`rules/runtime-validation.md`](../rules/runtime-validation.md) the parse whose failure becomes a default. Neither says what a handler should do instead. This does.

## Two kinds of failure

TypeScript has no checked exceptions: a function's signature does not say what it throws, and `catch` receives a value of type `unknown`, because the language lets a `throw` carry any value at all, not only an `Error` (ECMA-262 §14.14, The throw Statement). That makes one decision central, and it is made per failure, not per codebase.

**A failure the caller is expected to handle is returned.** A payment declined, a username taken, an input that does not parse: each is an outcome of the operation, the caller has a decision to make about it, and the compiler should make the caller make it. The shape is a discriminated union the compiler narrows:

```ts
type Charge = { ok: true; receipt: Receipt } | { ok: false; reason: "declined" | "expired" };
```

Zod's `safeParse` returns exactly this shape, which is why the validation entry of [`libraries.md`](libraries.md) needs no result library beside it.

**A failure nobody can handle where it happens is thrown.** A broken invariant, a database that is down, a bug: the code that meets it has no decision to make, and the right handler is far away — the request boundary, the job runner, the process. Throwing it unwinds to that handler without every frame in between having to forward it.

The test is the caller: if a caller would write a `switch` over the failure, return it; if every caller would rethrow it, throw it.

## What is thrown is an `Error`

typescript-eslint's `only-throw-error` and `prefer-promise-reject-errors`, both in `recommendedTypeChecked`, refuse throwing or rejecting with anything that is not an `Error`. A thrown string has no stack, and a handler that reads `error.message` gets `undefined`. A domain error is a subclass with a fixed `name` and the fields a handler needs:

```ts
class OrderNotFound extends Error {
  override readonly name = "OrderNotFound";
  constructor(readonly orderId: string, options?: ErrorOptions) { super(`order ${orderId} not found`, options); }
}
```

## Context is added with `cause`, never by replacing

When a low-level failure is rethrown with a message that says what was being attempted, the original goes in `cause`, which the `Error` constructor installs from its options (ECMA-262 §20.5.1.1 and §20.5.8.1, InstallErrorCause) — MDN: "this property can be used to pass the original error". `throw new Error("loading order 42", { cause: error })` keeps the stack and the driver's message under a sentence a person can act on. Replacing the error with a new one that does not carry it is the one way to make a failure harder to diagnose than not catching it.

## A caught value is `unknown`, and is narrowed before use

`useUnknownInCatchVariables`, governed by `strict` (condition 2 of [`typing.md`](../rules/typing.md)), types the binding in `catch (error)` as `unknown`, and typescript-eslint's `use-unknown-in-catch-callback-variable` does the same for a `.catch((error) => …)` callback. The narrowing is `error instanceof OrderNotFound` for a known kind, and `error instanceof Error` before reading `.message`; anything else is logged as the value it is. `catch (error: any)` undoes the flag for that block, and is condition 4 of `typing.md`.

## A returned promise is awaited inside `try`

`return save(order)` inside a `try` returns the promise before it settles, so its rejection escapes the `catch` written around it. typescript-eslint's `return-await` says it: awaiting "allows the promise's rejection to be caught instead of leaving the error to the caller". Its default, `in-try-catch`, requires the `await` exactly where it matters.

## What a boundary turns a failure into

Every failure ends at a boundary, and each boundary has one translation:

| Boundary | Expected failure (returned) | Unexpected failure (thrown) |
|---|---|---|
| HTTP handler | a 4xx with a body naming what was wrong | a 500 with a correlation id, the error logged once with its cause chain |
| queue consumer | acknowledge and record the outcome | do not acknowledge; the broker redelivers, and a dead-letter queue takes it after the retry budget |
| CLI | a message to stderr and a non-zero exit code | the same, with the stack when a debug flag is set |
| process | — | the `unhandledRejection` / `uncaughtException` listener of condition 4 of [`promises.md`](../rules/promises.md): record, then exit |

**A failure is logged once, where it is handled, not at every frame it passes.** A `catch` that logs and rethrows produces the same failure three times in the logs, each without the others' context. Log at the boundary, with the cause chain.

## Where this stops

**It does not choose between exceptions and a result library for a whole codebase.** A team that has decided every fallible function returns a result uses neverthrow, as [`libraries.md`](libraries.md) says, and the two kinds above still apply inside it: the unexpected failure is still thrown.

**What is logged and at which level, and what a log line must not contain**, is the observability discipline's `reviewing-observability` and the security discipline's `reviewing-sensitive-data`. This page says where the log happens, not what goes in it.

**Returning a union is wrong when every caller rethrows it.** A failure that no caller ever decides about, written as `{ ok: false }`, only makes each caller convert it back into a throw; that is the signal to throw it from the start.

**Upstream detail in an error message is [`sensitive-data.md`](sensitive-data.md)'s.** What a translated error may carry across a boundary is decided there.

**Retries are [`async.md`](async.md)'s.** Whether a failure is retried, how often and with what backoff is decided with the timeout and the idempotency of the call, not with the error's type alone.

## Sources

- ECMA-262, 17th edition (ES2026): §14.14 The throw Statement; §20.5.1.1 Error ( message [ , options ] ); §20.5.8.1 InstallErrorCause. <https://262.ecma-international.org/17.0/>
- MDN, `Error()` and `cause`: <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/Error>.
- typescript-eslint `only-throw-error`, `prefer-promise-reject-errors`, `use-unknown-in-catch-callback-variable`, `return-await`: <https://typescript-eslint.io/rules/only-throw-error/>, <https://typescript-eslint.io/rules/prefer-promise-reject-errors/>, <https://typescript-eslint.io/rules/use-unknown-in-catch-callback-variable/>, <https://typescript-eslint.io/rules/return-await/>.
- Zod `safeParse`: <https://zod.dev/basics>.
