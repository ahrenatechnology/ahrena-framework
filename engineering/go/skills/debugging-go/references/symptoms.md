# Go symptoms, the tool that sees each, and the rule it usually breaks

Opened by step 2 of `SKILL.md`. Each row is a symptom as it is reported, the instrument that turns it into evidence, and the rule condition the cause most often violates. The rule is a hypothesis to test, not a verdict.

## Panic

The trace names the panic, the goroutine and the stack, innermost frame first. Read down to the first frame in the project's own code: that line is where the bad value was used, and the cause is where it came from.

- **`assignment to entry in nil map`** — `rules/nil-safety.md` condition 1.
- **`invalid memory address or nil pointer dereference`** — `rules/nil-safety.md` condition 4, or `rules/resources.md` condition 2 when the pointer is an `*http.Response`.
- **`interface conversion: … is …, not …`** — a single-result type assertion, `rules/nil-safety.md` condition 3.
- **`send on closed channel` / `close of closed channel`** — `rules/concurrency.md` condition 7.
- **`fatal error: concurrent map writes`** or a similar map fault — `rules/concurrency.md` condition 2. This is a fatal error, not a panic: `recover` cannot catch it.
- **`sync: negative WaitGroup counter`** — `rules/concurrency.md` condition 4.

By default only the failing goroutine's stack is printed. The `runtime` package documents `GOTRACEBACK=all` to add every user goroutine, which is what a panic caused by another goroutine's state needs.

```sh
GOTRACEBACK=all go test ./internal/orders/ -run TestCancel -count=1
```

## A test that fails sometimes

Run it many times, with the race detector and in a shuffled order; the seed `-shuffle` prints makes an order-dependent failure reproducible.

```sh
go test ./internal/orders/ -run TestCancel -race -count=200 -shuffle=on
```

- **A race report** — `rules/concurrency.md` condition 2; the report names both accesses and both goroutines' stacks.
- **Fails only after another test** — shared package state or a leaked goroutine from the earlier test, `rules/concurrency.md` condition 1; `goleak.VerifyTestMain` in `TestMain` names the goroutine.
- **Fails only under load or on a slow machine** — a timing assumption: a `time.Sleep` standing in for synchronisation. Rewrite the test inside `synctest.Test` (Go 1.25), whose fake clock removes the timing.

## A hang

A program that stops making progress has goroutines blocked on something. Make it print them. The `os/signal` documentation: pressing `^\` (SIGQUIT) makes a Go program exit with a stack dump, and `kill -QUIT` does the same to a process. A test that hangs is stopped by `go test -timeout`, which prints every goroutine's stack when it fires.

A running service with `net/http/pprof` imported serves the same stacks without stopping: the `goroutine` profile with `debug=2` prints them in the form a dying program uses, per the `runtime/pprof` documentation.

```sh
curl -s 'localhost:6060/debug/pprof/goroutine?debug=2' > goroutines.txt
```

Group the stacks by where they are blocked. Hundreds of goroutines parked on the same channel receive is a leak, `rules/concurrency.md` condition 1; two goroutines each waiting on the other's lock is a deadlock, and the fix is a lock order or a narrower critical section (`GO-2` in the review skill's reference).

## Memory or goroutine count that grows

- **Goroutines grow** — from Go 1.27, the `goroutineleak` profile (`/debug/pprof/goroutineleak`) reports goroutines blocked on a primitive no runnable goroutine can reach. Its release notes say it finds a large class of leaks, not all, so an empty profile is not proof. `rules/concurrency.md` condition 1.
- **Heap grows** — `go tool pprof` on the `heap` profile, compared across two points in time with `-base`. Common causes: a sub-slice retaining a large buffer (`GO-4`), a cache with no bound, a timer or response body never released (`rules/resources.md` condition 1).
- **File descriptors or connections grow** — `rules/resources.md` conditions 1 and 3: a body not closed, a `defer` in a loop.

## Too slow

`go test -bench` with `-cpuprofile`, or the service's `/debug/pprof/profile`, then `go tool pprof`. Latency that is not CPU — waiting on locks, channels, the network — shows in the `block` and `mutex` profiles and in an execution trace (`go tool trace`). A slow path is a defect only when a requirement says how fast it must be; without one, this is not a debugging task.

## A wrong value

No instrument names the cause; narrow it. Shrink the failing input until it is minimal, then step through it with Delve, which the Go documentation's *Debugging Go Code with GDB* page calls "a better alternative to GDB" for Go programs. `dlv test ./internal/orders/ -- -test.run TestCancel` debugs one test.

When the value was right in an earlier revision, let git find the commit: `git bisect run go test ./internal/orders/ -run TestCancel -count=1` marks each revision by the test's exit code.

## An error that arrives as the wrong kind

A caller's `errors.Is` or `errors.As` does not match an error that should match. Follow the error back through every frame: a `%v` where a `%w` was needed, or a translation into another sentinel, breaks the chain — `rules/errors.md` conditions 2 and 3. A typed nil returned as an `error` produces the opposite symptom, an error where there was none — `rules/nil-safety.md` condition 2.
