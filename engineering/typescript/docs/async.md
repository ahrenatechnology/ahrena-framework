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

An `async` function that calls another one awaits it, on the line it is called. `await` suspends the function until the promise settles and resumes it with the value, or throws the rejection at that point (ECMA-262 §27.7.5.3, Await; §15.8, Async Function Definitions): the result arrives in order, the rejection becomes a throw the surrounding `try` sees, and the stack trace shows the caller. Everything below is an exception to this default, taken on purpose.

**Fire-and-forget is written, not implied.** When a call is genuinely not waited for — a metric sent after the response — it is marked `void` and given its own handler: `void send(metric).catch((error: unknown) => log.warn({ error }, "metric dropped"))`. `void` alone tells typescript-eslint's `no-floating-promises` the author meant it, and it accepts that by default (`ignoreVoid`); the `.catch` is what keeps the rejection from becoming an unhandled one.

## Several promises: chosen by what the tasks are

| The tasks are | Write | Because |
|---|---|---|
| independent, all must succeed | `await Promise.all(tasks)` | one rejection rejects the whole, and the caller handles one failure (ECMA-262 §27.2.4.1) |
| independent, each may fail alone | `await Promise.allSettled(tasks)` | every outcome comes back; one failure does not discard the successes (§27.2.4.2) |
| ordered, each needs the last | `for (const x of xs) await step(x)` | the order is the point |
| many, against one upstream | a bounded pool, below | `Promise.all` over ten thousand calls is ten thousand open requests |

`rows.forEach(async (row) => …)` is none of these: `forEach` "expects a synchronous function — it does not wait for promises" (MDN), and condition 2 of [`promises.md`](../rules/promises.md) refuses it.

**Concurrency is bounded when the input is.** A list that comes from a user or a table has no upper bound, and mapping it straight into `Promise.all` opens one connection per item. A pool — the list processed in fixed-size slices, or a semaphore around the call — keeps the upstream's limit and this process's sockets in hand. The size is not this plugin's number: it is the upstream's own documented concurrency or rate limit, or the connection pool size of the client that makes the call, whichever is lower, read from the provider's documentation or the client's configuration and written beside the pool.

## Every call that leaves the process has a deadline and a way to stop

**A timeout.** `fetch` has none of its own. `AbortSignal.timeout(ms)` (added in Node 17.3.0 and 16.14.0) produces a signal that aborts after the delay, and it is passed to every outside call: `fetch(url, { signal: AbortSignal.timeout(5_000) })`. A call without one waits as long as the far side lets it, which in an incident is forever.

**Cancellation that propagates.** A request handler receives a signal for the request; the calls it makes pass that signal down, combined with their own timeout through `AbortSignal.any([request.signal, AbortSignal.timeout(ms)])` (added in Node 20.3.0 and 18.17.0). When the client goes away, the work it started stops.

**A response is checked before it is read.** `fetch` rejects only on a network failure; MDN is explicit that it "does not reject if the server responds with HTTP status codes that indicate errors". `response.ok` is checked, and the body is then parsed against a schema, as [`rules/runtime-validation.md`](../rules/runtime-validation.md) requires.

## Retries are for work that can be repeated

A retry repeats a request whose first attempt may have succeeded. That is safe for a read and for a write that carries an idempotency key the far side honours, and it is a duplicate charge otherwise. So a retry policy is attached to a call only after the call is known to be repeatable, with a bounded number of attempts, exponential backoff with jitter, and a circuit breaker so that a failing dependency is not retried into the ground. [`libraries.md`](libraries.md) names cockatiel for the composed policy and p-retry for the single call.

## Resources are released with `await using`

TypeScript 5.2 added `using` and `await using` for ECMAScript's Explicit Resource Management. The proposal is at Stage 4 and expected in ES2027, so it is not yet in the published ES2026 edition; Node 24 enabled it (its v24.0.0 release lists explicit resource management with V8 13.6). A connection, a lock or a temporary directory whose type implements `Symbol.asyncDispose` is released when the block exits, by return or by throw:

```ts
await using connection = await pool.connect();
```

It replaces the `try`/`finally` whose `finally` someone forgets to write. Where the target runtime does not support it, `try`/`finally` is the same guarantee written out.

## Where this stops

**A timeout on every call is wrong for a transfer whose length is the point.** A large download or a long-poll stream is given an idle timeout — no bytes for N seconds — rather than a total deadline, or a healthy transfer is cut at the deadline. The deadline principle holds; its form changes.

**It does not cover worker threads or child processes.** CPU-bound work moved off the event loop is a design decision about the service; its messages are a boundary under [`rules/runtime-validation.md`](../rules/runtime-validation.md) like any other.

**It does not cover streams in depth.** Node streams and web streams carry back-pressure that a `for await` loop respects and a `.on("data")` handler does not; reaching for `for await` is the default, and the rest is Node's documentation.

**Whether a dependency's slowness or absence is survived** — fallbacks, bulkheads, degraded modes — is the reliability discipline's `reviewing-reliability`. This page gives the mechanics it reads.

## Sources

- ECMA-262, 17th edition (ES2026): §27.7.5.3 Await; §15.8 Async Function Definitions; §27.2.4.1 Promise.all; §27.2.4.2 Promise.allSettled; §23.1.3.15 Array.prototype.forEach. <https://262.ecma-international.org/17.0/>
- TC39, Explicit Resource Management (Stage 4, expected 2027): <https://github.com/tc39/proposal-explicit-resource-management>, <https://github.com/tc39/proposals/blob/main/finished-proposals.md>; TypeScript 5.2 release notes: <https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-2.html>; Node v24.0.0 release: <https://nodejs.org/en/blog/release/v24.0.0>.
- Node.js, `AbortSignal.timeout` and `AbortSignal.any`, `fetch`: <https://nodejs.org/api/globals.html>.
- MDN, `fetch` does not reject on HTTP error status: <https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch>; `Response.ok`: <https://developer.mozilla.org/en-US/docs/Web/API/Response/ok>; `forEach`: <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/forEach>.
- typescript-eslint `no-floating-promises` (`ignoreVoid`): <https://typescript-eslint.io/rules/no-floating-promises/>.
