---
id: async
type: doc
clade: engineering
subclade: typescript
title: Writing async TypeScript so no promise floats
summary: How async code is written so the promises rule holds without effort - await by default, Promise.all and allSettled chosen by what the tasks are, a timeout and a cancellation signal on every outside call, retries only for idempotent work, bounded concurrency, and resources released with await using.
references:
  - rules/promises.md
---

# Writing async TypeScript so no promise floats

[`rules/promises.md`](../rules/promises.md) refuses a promise nobody awaits and a rejection nobody hears. This is how async code is written so that the rule is never close to failing, and what to reach for when the plain `await` is not enough.

## `await` is the default

An `async` function that calls another one awaits it, on the line it is called. The result arrives in order, the rejection becomes a throw the surrounding `try` sees, and the stack trace shows the caller. Everything below is an exception to this default, taken on purpose.

**Fire-and-forget is written, not implied.** When a call is genuinely not waited for — a metric sent after the response — it is marked `void` and given its own handler: `void send(metric).catch((error: unknown) => log.warn({ error }, "metric dropped"))`. `void` alone tells typescript-eslint's `no-floating-promises` the author meant it, and it accepts that by default (`ignoreVoid`); the `.catch` is what keeps the rejection from becoming an unhandled one.

## Several promises: chosen by what the tasks are

| The tasks are | Write | Because |
|---|---|---|
| independent, all must succeed | `await Promise.all(tasks)` | one rejection rejects the whole, and the caller handles one failure |
| independent, each may fail alone | `await Promise.allSettled(tasks)` | every outcome comes back; one failure does not discard the successes |
| ordered, each needs the last | `for (const x of xs) await step(x)` | the order is the point |
| many, against one upstream | a bounded pool, below | `Promise.all` over ten thousand calls is ten thousand open requests |

`rows.forEach(async (row) => …)` is none of these: `forEach` "expects a synchronous function — it does not wait for promises" (MDN), and condition 2 of [`promises.md`](../rules/promises.md) refuses it.

**Concurrency is bounded when the input is.** A list that comes from a user or a table has no upper bound, and mapping it straight into `Promise.all` opens one connection per item. A small pool — process the list in fixed-size slices, or use a semaphore around the call — keeps the upstream's limit and this process's sockets in hand.

## Every call that leaves the process has a deadline and a way to stop

**A timeout.** `fetch` has none of its own. `AbortSignal.timeout(ms)` (Node 17.3 and 16.14) produces a signal that aborts after the delay, and it is passed to every outside call: `fetch(url, { signal: AbortSignal.timeout(5_000) })`. A call without one waits as long as the far side lets it, which in an incident is forever.

**Cancellation that propagates.** A request handler receives a signal for the request; the calls it makes pass that signal down, combined with their own timeout through `AbortSignal.any([request.signal, AbortSignal.timeout(ms)])` (Node 20.3 and 18.17). When the client goes away, the work it started stops.

**A response is checked before it is read.** `fetch` rejects only on a network failure; MDN is explicit that it "does not reject if the server responds with HTTP status codes that indicate errors". `response.ok` is checked, and the body is then parsed against a schema, as [`rules/runtime-validation.md`](../rules/runtime-validation.md) requires.

## Retries are for work that can be repeated

A retry repeats a request whose first attempt may have succeeded. That is safe for a read and for a write that carries an idempotency key the far side honours, and it is a duplicate charge otherwise. So a retry policy is attached to a call only after the call is known to be repeatable, with a bounded number of attempts, exponential backoff with jitter, and a circuit breaker so that a failing dependency is not retried into the ground. [`libraries.md`](libraries.md) names cockatiel for the composed policy and p-retry for the single call.

## Resources are released with `await using`

TypeScript 5.2 added `using` and `await using` for ECMAScript's Explicit Resource Management, and Node 24's V8 runs them natively. A connection, a lock or a temporary directory whose type implements `Symbol.asyncDispose` is released when the block exits, by return or by throw:

```ts
await using connection = await pool.connect();
```

It replaces the `try`/`finally` whose `finally` someone forgets to write. Where the target runtime does not support it, `try`/`finally` is the same guarantee written out.

## Where this stops

**It does not cover worker threads or child processes.** CPU-bound work moved off the event loop is a design decision about the service; its messages are a boundary under [`rules/runtime-validation.md`](../rules/runtime-validation.md) like any other.

**It does not cover streams in depth.** Node streams and web streams carry back-pressure that a `for await` loop respects and a `.on("data")` handler does not; reaching for `for await` is the default, and the rest is Node's documentation.

**Whether a dependency's slowness or absence is survived** — fallbacks, bulkheads, degraded modes — is the reliability discipline's `reviewing-reliability`. This page gives the mechanics it reads.
