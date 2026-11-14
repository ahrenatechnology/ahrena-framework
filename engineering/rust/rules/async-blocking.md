---
id: async-blocking
type: rule
clade: engineering
subclade: rust
title: Nothing blocks an async worker thread
statement: An async body in Rust makes no blocking call, holds no sync lock guard across `.await`, and moves CPU-bound work off the runtime with `spawn_blocking`.
enforcement: judgment
references:
  - docs/async-and-concurrency.md
  - docs/toolchain.md
---

# Nothing blocks an async worker thread

An async runtime multiplexes many tasks over a few threads, and a task gives its thread back only at an `.await`. A task that blocks between two `.await` points holds a worker the other tasks were waiting for, so one slow call becomes latency for every request on that thread, and enough of them stall the runtime. [`docs/async-and-concurrency.md`](../docs/async-and-concurrency.md) explains the scheduling and the choice between the remedies.

Inherited from the predecessor's `lex-rust-no-blocking-in-async`, which drew on Tokio's `spawn_blocking` and Meilisearch's split between its async HTTP layer and its synchronous index scheduler. The source enforced it with Clippy's `disallowed_methods`, which bans a function everywhere, including in the synchronous code where calling it is correct; condition 1 is decided by a hook instead, which reads only async bodies.

## Conditions

1. **No call from the closed blocking list inside an async function, async block or async closure, outside the closure handed to `spawn_blocking`, `block_in_place`, `thread::spawn` or `thread::scope`.** Decided by `hooks/check-rust.py`. The list: `std::thread::sleep`; the free functions of `std::fs` and `std::fs::File::open`, `create` and `create_new`; `std::net::TcpStream::connect` and `connect_timeout`; any method whose name starts with `blocking_`, which is how Tokio names the synchronous halves of its channels and locks, each documented to panic when called from async code; and anything under `reqwest::blocking`. A name is resolved through the file's `use` declarations, so `fs::read` is a finding only where `fs` is `std::fs`. Test code is not read.

2. **No `std::sync::MutexGuard`, `RwLock` guard or `RefCell` borrow is held across an `.await`.** Decided by Clippy's `clippy::await_holding_lock` and `clippy::await_holding_refcell_ref`, both in the default `suspicious` group, denied. A guard held across a suspension point blocks every other task that wants the lock for as long as the suspended task stays parked; Tokio's own documentation for its `Mutex` says it is the one to use only when the lock has to span an `.await`. A project that adds its own guard types names them in `await-holding-invalid-types` in `clippy.toml`.

3. **Work that runs longer than 10 to 100 microseconds without reaching an `.await` runs on `spawn_blocking`, on `rayon`, or on a dedicated thread.** Decided by a reviewer, with a profiler or `tokio-console` when it is in doubt. The figure is Alice Ryhl's, a Tokio maintainer, in [Async: What is blocking?](https://ryhl.io/blog/async-what-is-blocking/): no more than 10 to 100 microseconds between each `.await`. It is a rule of thumb from the people who wrote the scheduler, not a measurement of any project, and it is kept because the alternative is no figure at all. Hashing a password, compressing a file, parsing a large document and a tight loop over a large collection are the usual cases.

## Where this stops

**Condition 1's list is closed, and a blocking call off it is not reported.** `std::process::Command::output` blocks and is not on it, because its async counterpart has the same method name and the hook cannot tell the receiver's type. Neither is a synchronous database driver, an SDK's blocking client or a foreign function that does I/O. Those are condition 3's reviewer.

**A project's own offloading wrapper is not recognised.** A call inside a closure handed to a helper that itself calls `spawn_blocking` is reported. Measured over the 310 crates in a local Cargo registry, about 415,000 lines, all 34 findings of condition 1 were of this shape, and all were inside Tokio's own `tokio::fs`, which implements the async file API by exactly that delegation. The fix in a consuming project is to call `spawn_blocking` at the call site or to exclude the wrapper's file by path, and to write down which.

**A synchronous function called from an async body is not followed.** The hook reads the async body's own calls. A helper `fn load()` that calls `std::fs::read` and is called from an `async fn` blocks just the same, and a reviewer follows it.

**`std::sync::Mutex` in async code is allowed.** For a short critical section with no `.await` inside, it is cheaper than an async mutex, and Tokio's documentation recommends it. Condition 2 is about the guard's lifetime, not about the type.

**A `main` that sets up the runtime may block before it starts.** Reading a configuration file in a synchronous `main` before `Runtime::block_on` runs nothing on a worker. The hook does not read a `main` that is not `async`; an `#[tokio::main] async fn main` is async and is read.
