# Evidence per symptom

Opened by step 3 of `SKILL.md`, at the class step 1 chose. Each section names the tools that read that class's evidence, what each shows, and the commonest cause in Rust. Commands were checked against Cargo and rustc 1.99; nightly-only tools are marked.

## A panic

- `RUST_BACKTRACE=1 cargo test <name>` prints the stack at the panic; `RUST_BACKTRACE=full` adds the frames inside the standard library. The first frame in the crate's own code is where to start reading.
- The message names the location. `called Option::unwrap() on a None value` and `called Result::unwrap() on an Err value` are an `unwrap` on a path that could fail — `rules/panics.md` condition 1 — and the fix is to return the error, not to add a check before the `unwrap`.
- `byte index N is not a char boundary` is a string slice at a computed index — `rules/strings.md` condition 1.
- `attempt to add with overflow` (debug builds only) is an integer overflow that a release build wraps silently, which is why the same input gives a wrong result in release instead of a panic.
- `already borrowed: BorrowMutError` is a `RefCell` borrowed twice — `rules/ownership.md` condition 4, an aliasing error moved to run time.
- A panic inside a Tokio task does not stop the program: it surfaces as a `JoinError` from the task's handle, or nowhere if the handle was dropped. A request that "silently fails" may be a panicked task; a panic hook that logs through `tracing` (`docs/error-handling.md`) makes it visible.

## A wrong result

- Narrow with the failing test: assert on intermediate values, or `dbg!(expr)`, which prints the expression, its value and its location to stderr and returns the value, so it can wrap any sub-expression without restructuring. Remove every `dbg!` before the fix lands.
- Compare debug and release (`cargo test --release`). A difference is an overflow (above), a `debug_assert!` with a side effect, or undefined behaviour (below).
- A property test with `proptest` around the function finds the smallest input that is wrong, which is often the diagnosis by itself (`docs/testing.md`).
- A regression with a known good revision: `git bisect run cargo test <name>` finds the commit, provided the test fails for only that reason across the range.

## A hang or deadlock

- In async code, the commonest cause is a blocking call on a worker thread — `rules/async-blocking.md` conditions 1 and 3 — or a `std::sync::Mutex` guard held across an `.await` — condition 2. Run `hooks/check-rust.py` and Clippy's `await_holding_lock` over the code first; both are cheap.
- `tokio-console` shows every task, how long it has been running since its last yield, and which resource it waits on. It needs `console-subscriber` installed in the program and the `tokio_unstable` cfg flag (`RUSTFLAGS="--cfg tokio_unstable"`), so it is set up in a debug build, not left in production.
- A deadlock between locks shows as threads parked in `lock()` in a debugger: `rust-lldb` or `rust-gdb` attached to the process, `thread backtrace all`. Two locks taken in opposite orders on two paths is the usual cause (`docs/async-and-concurrency.md`).
- A task waiting on a channel whose sender was never dropped never ends; a `select!` without a branch for shutdown never exits.

## A crash or undefined behaviour

- In code with no `unsafe` of its own, look at the `unsafe` blocks it depends on: its own first, then its dependencies' (`cargo geiger` lists them). Safe Rust does not cause undefined behaviour unless an `unsafe` block somewhere lets it.
- **Miri** (nightly): `cargo +nightly miri test` runs the tests under an interpreter that detects out-of-bounds access, use after free, invalid values, data races and violations of the aliasing model, and names the line. It cannot run code that calls into C or does most I/O, so a test that isolates the `unsafe` code is what it runs on.
- **AddressSanitizer** (nightly): `RUSTFLAGS=-Zsanitizer=address cargo +nightly test --target <host-triple>` catches memory errors in code Miri cannot run, including across FFI. ThreadSanitizer (`-Zsanitizer=thread`) catches data races the same way.
- Across FFI, check `rules/ffi.md`: a type whose layout C disagrees with (condition 2), memory freed by the wrong allocator (condition 3), or a panic unwinding into C, which since Rust 1.81 aborts with "panic in a function that cannot unwind".

## A flaky test

- Run it repeatedly to measure: `cargo nextest run <name> --retries 0` in a loop, or `for i in $(seq 50); do cargo test <name> -q || break; done`.
- Shared state between tests is the first suspect: a fixed temporary path, an environment variable, a global, a port. `cargo test -- --test-threads=1` making it pass confirms it; the fix is isolation (`tempfile`, a random port), not the flag.
- Time is the second: a test that sleeps and expects something to have happened. `tokio::time::pause()` makes async time deterministic (`docs/testing.md`).
- Iteration order of a `HashMap` is randomised per process; an assertion that depends on it fails sometimes. Sort, or use a `BTreeMap`.

## A build or dependency failure

- `cargo tree -d` lists crates present at two versions, the cause of "expected `Foo`, found `Foo`" when the two types come from different versions of one crate.
- `cargo tree -e features -i <crate>` shows which dependency enabled a feature. Features are unified across the build graph, so a feature one crate enables is on for every crate that depends on the same package.
- `cargo expand`, an installed subcommand, prints the code after macro expansion, which is where a derive's or a procedural macro's error is understood.
- A failure that appeared without a code change is a dependency that moved. Compare `Cargo.lock` with the last good build, and build with `cargo update --precise <crate>@<old-version>` to confirm.
- A compiler regression — the same code failing on a newer toolchain — is bisected with `cargo bisect-rustc`, and reported to rust-lang/rust with the result.

## A performance regression

- Reproduce with a `criterion` benchmark of the slow path, run on the good and the bad revision; `criterion` reports whether the difference is beyond noise.
- Profile the bad revision as `docs/performance.md` describes — `samply` or `perf`, a release build with debug symbols — and compare where the time goes with the good one.
- The commonest Rust causes: an allocation added inside a loop, a `clone` of something large, a regex compiled per call (`rules/regex-compilation.md`), a lock that now covers more work, a `Vec` that lost its pre-allocated capacity.
