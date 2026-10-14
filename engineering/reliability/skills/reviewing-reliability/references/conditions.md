# Reliability

The conditions `reviewing-reliability` applies. Each gives the state, how it is detected, what exempts it, and the correction. Every one is decided on a pair: the call the change makes, and what happens to the caller when that call is slow, fails, or arrives twice. The party who pays is whoever waits on the request or is charged, double-booked or corrupted when the failure is not handled.

### REL-1 A call with no timeout

- **State:** an outbound call — an HTTP request, a database query, an RPC, a lock, a queue or stream wait — issued with no timeout or deadline, so a stalled peer blocks the caller until something else gives up.
- **Detect:** each outbound call the route pointed at. Read whether a timeout, deadline or cancellation is set on the call or on the client it is made through.
- **Exempt:** a client configured with a timeout at construction that the repository already sets, when the finding can name where; a deliberately long-lived stream or subscription whose wait is the feature.
- **Correct:** set a timeout on the call, or a deadline on the context it carries, so a slow peer fails fast instead of holding the caller.

### REL-2 A retry with no backoff or no bound

- **State:** a retry loop with no delay between attempts, no backoff, or no maximum number of attempts, so a struggling dependency is hit harder the moment it is weakest.
- **Detect:** each loop or decorator that repeats a failed call. Read whether it waits between attempts, grows that wait, and stops after a fixed count.
- **Exempt:** a retry a library or the platform already bounds with backoff, when the finding can name it.
- **Correct:** cap the attempts and space them with exponential backoff and jitter; retry only errors that a second attempt can resolve, and give up to the caller otherwise.

### REL-3 A non-idempotent effect on a retried path

- **State:** an operation with an external effect — a charge, an email, a stock decrement, an insert — on a path that can run twice: behind a retry, a webhook handler, or a queue or stream consumer, all of which redeliver.
- **Detect:** for each effect, ask whether its path is retried or redelivered, and whether running it twice produces the effect twice.
- **Exempt:** an effect that is already idempotent — an upsert keyed by the caller's identifier, a write guarded by a dedup key the repository persists.
- **Correct:** make the effect idempotent, keyed by an identifier the caller supplies or the event carries, so a replay is a no-op. When the fix is an idempotency key on a published mutation, `cross-cutting-concerns` condition 4 is the rule that names it.

### REL-4 An error swallowed

- **State:** an exception caught and discarded, an empty `catch`, an error return ignored, or a failure that is logged and then execution continues as if it had succeeded — so a broken operation reports done.
- **Detect:** each handler and each error-returning call the route pointed at. Read whether the failure changes the control flow or is absorbed. A `catch` whose body only logs, with no re-raise and no fallback, continues as success.
- **Exempt:** a failure the code is deliberately tolerating, where the catch is narrow to the expected error and a comment or a fallback states the intent; a cleanup path that must run regardless.
- **Correct:** handle the error — retry it, fall back, or propagate it — so the caller learns the operation did not succeed. Narrow a broad catch to the error actually expected.

### REL-5 A resource acquired and not released

- **State:** a connection, a file, a socket, a lock, a transaction, a pool handle or a subscription opened on a path where an early return or a raised error skips its release, so the resource leaks until the process is restarted.
- **Detect:** each acquisition the route pointed at. Follow every path out of the scope — the return, the branch, the raised error — and check that release runs on all of them.
- **Exempt:** a resource bound to a language construct that releases it on every exit — a `with`, a `defer`, a `try-with-resources`, an RAII guard.
- **Correct:** acquire the resource through the construct the language provides for guaranteed release, so the exit path cannot skip it.

### REL-6 A dependency with no degradation

- **State:** a feature that calls a non-essential dependency — a cache, a recommendation service, an analytics sink, an enrichment API — and fails the whole request when that dependency is down, so a peripheral outage becomes a total one.
- **Detect:** each call to a dependency that is not on the critical path. Read what the caller does when it is unavailable: whether it falls back, serves degraded, or propagates the failure.
- **Exempt:** a dependency whose absence genuinely is unrecoverable — the primary datastore, the identity provider — where stopping is the correct behaviour.
- **Correct:** catch the dependency's failure and degrade — serve stale, skip the enrichment, return the core result — so the non-essential stays non-essential. Whether a given dependency is essential is a **question** for the owner when the change does not settle it.

### REL-7 A destructive change with no reversal

- **State:** a migration or schema change that drops a column, a table or an index, truncates, or rewrites data in place, shipped with no down path and no backfill or backup named, so a bad deploy cannot be rolled back.
- **Detect:** each migration or destructive statement the route pointed at. Read whether a reverse operation, a backup, or a staged expand-then-contract is present.
- **Exempt:** a destructive step that is the contract half of an expand-then-contract already deployed and verified, when the finding can name the prior expand.
- **Correct:** stage the change so the old and new shapes coexist and the drop lands only after the new shape is proven; keep a down path or a backup so the deploy is reversible.
