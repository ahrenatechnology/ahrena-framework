---
id: async-and-concurrency
type: doc
clade: engineering
subclade: rust
title: Async and concurrency in Rust
summary: How Tokio schedules tasks and why a blocking call stalls other requests, how to choose between a lock, a channel and an actor, what cancellation does to a future, how a service shuts down, and what `Send` and `Sync` guarantee and do not.
references:
  - rules/async-blocking.md
  - rules/unsafe-code.md
  - docs/libraries.md
---

# Async and concurrency in Rust

This is the companion to [`rules/async-blocking.md`](../rules/async-blocking.md). It merges the predecessor's `codex-rust-async-architecture`, drawn from Tokio, Meilisearch and TiKV, with its `codex-rust-concurrency-guarantees`, drawn from the Rust book's chapters on concurrency and on choosing between smart pointers. Each claim about Tokio below was checked against its documentation as of version 1.54.

**What the specification says, and what it leaves open.** The language defines futures, `async` functions and blocks, and `.await` ([Async functions](https://doc.rust-lang.org/reference/items/functions.html#async-functions); [Await expressions](https://doc.rust-lang.org/reference/expressions/await-expr.html); RFC 2394, [async/await](https://rust-lang.github.io/rfcs/2394-async_await.html)), and the `Send` and `Sync` traits ([Special types and traits](https://doc.rust-lang.org/reference/special-types-and-traits.html#send)). It defines no runtime, no scheduler and no channel. Everything about scheduling below is Tokio's documentation and its maintainers' practice, used where the specification is silent, as the owner's directive on #285 allows.

## How the runtime schedules, and why blocking hurts

Tokio's multi-threaded runtime runs tasks on a fixed set of worker threads, by default one per CPU core. A task runs until it reaches an `.await` on something not ready, and then gives its thread back so another task can run. Nothing pre-empts a task that does not reach an `.await`. That is the whole mechanism, and everything in the rule follows from it: a task that blocks — on a file read, a sleep, a lock, a long computation — keeps its worker for as long as it blocks, and every task queued behind it on that worker waits too. Work stealing moves queued tasks to idle workers, which softens the damage until every worker is blocked.

Alice Ryhl, one of Tokio's maintainers, puts the budget at [no more than 10 to 100 microseconds between each `.await`](https://ryhl.io/blog/async-what-is-blocking/), which is the figure [`rules/async-blocking.md`](../rules/async-blocking.md) condition 3 uses.

The remedies, in order of preference:

1. **An async API for the same operation**: `tokio::fs`, `tokio::time::sleep`, `tokio::net`, an async database driver. The task suspends instead of blocking.
2. **`tokio::task::spawn_blocking`** for a synchronous call with no async counterpart, or a bounded computation. It runs on a separate pool sized for blocking work (512 threads by default), and the async task awaits its result.
3. **`rayon`** for CPU-bound work that parallelises, started from `spawn_blocking` or reporting back over a channel; `spawn_blocking`'s pool is sized for waiting, not for computing.
4. **A dedicated thread**, with a channel in and out, for work that never ends — a synchronous event loop, a device driver.

`block_in_place` is the exception that proves the order: it turns the current worker into a blocking thread, which is cheap to write and only available on the multi-threaded runtime.

## Locks, channels and actors

The Rust book's slogan, from Go, is "do not communicate by sharing memory; share memory by communicating". It is a preference, not a rule, and the choice depends on what the shared state is.

| The state | Use |
|---|---|
| Read by many, never written after start | `Arc<T>`, no lock |
| A counter or a flag | an atomic (`AtomicU64`, `AtomicBool`) |
| A small value written briefly, never across an `.await` | `std::sync::Mutex` or `RwLock` inside `Arc` |
| Written across an `.await` | `tokio::sync::Mutex`, which Tokio's documentation reserves for exactly this |
| Owned by one long-running piece of logic that others ask things of | an actor: a task owning the state, an `mpsc` channel of commands, a `oneshot` for each reply |
| A value many readers watch for changes | `tokio::sync::watch` |
| Events every subscriber must see | `tokio::sync::broadcast` |

`std::sync::Mutex` is the default for the third row and is faster than Tokio's; Tokio's own documentation recommends it when the guard does not cross an `.await`, and [`rules/async-blocking.md`](../rules/async-blocking.md) condition 2 holds the line. An actor is the right shape when the state has invariants spanning several fields, because the single task serialises every change without a lock to forget.

**Bound every channel.** An unbounded channel moves back-pressure into memory: a slow consumer becomes a growing queue and, eventually, an out-of-memory kill. A bounded `mpsc::channel(n)` makes the producer wait instead. The predecessor forbade `for_each_concurrent(None)` on the same ground, and the argument generalises: any unbounded fan-out — spawning a task per item of an unbounded stream — needs a `Semaphore` or a `JoinSet` with a cap.

**`Send` and `Sync` prevent data races, not deadlocks.** A type is `Send` when it may move to another thread and `Sync` when `&T` may be shared between threads; the compiler derives both and refuses to move a non-`Send` value into `tokio::spawn`. That rules out data races in safe code. It does nothing about two tasks taking two locks in opposite orders, which deadlocks just as it would in any language; taking locks in one global order, or holding one at a time, is the remedy. An `unsafe impl Send` asserts a property the compiler could not prove, and [`rules/unsafe-code.md`](../rules/unsafe-code.md) condition 1 asks for the argument.

## Cancellation

A future does nothing until polled, and dropping it cancels it at whichever `.await` it was suspended on. `tokio::select!` drops every branch but the one that completes, `tokio::time::timeout` drops the inner future when time runs out, and a client that disconnects drops its handler. The code after the `.await` simply never runs.

That is safe when the future holds nothing half-done. Tokio's documentation for `select!` lists which of its own operations are cancel-safe: `mpsc::Receiver::recv`, `broadcast::Receiver::recv`, `watch::Receiver::changed`, `TcpListener::accept`, `AsyncReadExt::read` and `AsyncWriteExt::write`, `StreamExt::next`. Some are not, and lose data: `read_exact`, `read_to_end`, `read_to_string` and `write_all`. Others lose only their place in a fair queue: `Mutex::lock`, `Semaphore::acquire`, `Notify::notified`. A branch of a `select!` in a loop is one of the safe ones, or it is restructured so the unsafe operation runs in its own task and the `select!` awaits a channel from it.

The same reasoning applies to a handler with side effects: if a request can be cancelled after writing to the database and before writing the outbox, the two writes belong in one transaction or in a spawned task that is not cancelled with the request.

## Shutting down

A service stops in three steps: stop accepting work, let work in flight finish within a deadline, then exit. `tokio::signal` delivers `SIGTERM` and Ctrl-C; a `tokio_util::sync::CancellationToken` or a `watch` channel carries "stop" to every long-running task, each of which `select!`s on it beside its own work; and a `JoinSet` or `TaskTracker` holds the handles the shutdown waits on. `axum::serve(…).with_graceful_shutdown(signal)` implements the first two steps for the HTTP server. A task spawned and forgotten is one the shutdown cannot wait for.

## Batching, from Meilisearch and TiKV

The predecessor's `codex-rust-system-design` described two systems that receive many small writes and apply them in batches: Meilisearch's index scheduler queues tasks durably and applies them together, and TiKV's batch system groups requests per region. The pattern is a general one — an actor whose queue is drained in chunks, amortising a cost paid per batch rather than per item — and it is worth reaching for when that per-batch cost dominates, as a disk sync or an index rebuild does. It is not a default, and neither system's specifics carry over.

## Where this stops

**Runtimes other than Tokio are not covered.** [`libraries.md`](libraries.md) says why Tokio is the default; `smol` and `embassy` schedule differently, and the 10-to-100-microsecond figure is Tokio's.

**Lock-free data structures are not covered.** `crossbeam`'s queues and epoch reclamation, atomics beyond counters and flags, and memory orderings other than `SeqCst` are specialist territory; a change that introduces them gets a reviewer who knows them.

**Distributed concurrency is not this page's.** Two processes updating one row is a database question; idempotency of a retried request is `ahrena-engineering-reliability`'s.
