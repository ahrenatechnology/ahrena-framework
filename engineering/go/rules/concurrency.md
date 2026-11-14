---
id: concurrency
type: rule
clade: engineering
subclade: go
title: Goroutines with an owner, state with a guard
statement: Every goroutine has an owner that stops and waits for it, shared state is synchronised, sync values are never copied, and every CancelFunc is called.
enforcement: judgment
references:
  - docs/concurrency.md
  - docs/toolchain.md
---

# Goroutines with an owner, state with a guard

A `go` statement costs one keyword, and nothing in the language ties the goroutine it starts to anything: no handle is returned, nothing waits for it, nothing stops it. Every one of the conditions below is a way of putting back the tie the language leaves out — an owner who can stop the goroutine and waits for it, a lock or a channel between it and any state it shares, a cancellation that is actually called.

Four are decided by `go vet` and `staticcheck`, which the consuming project runs; one by the race detector, which only sees what the tests execute; three need a reader. [`docs/concurrency.md`](../docs/concurrency.md) argues the ownership model and the choice between channels, mutexes and `errgroup`; [`docs/toolchain.md`](../docs/toolchain.md) says where `-race` runs and why it is not optional.

## Conditions

1. **Every goroutine has an owner that can make it stop and that waits for it to finish.** The owner is the function, type or `errgroup.Group` that started it; it holds a way to signal it — a context it cancels, a channel it closes — and it does not return, or does not report itself shut down, before the goroutine has exited. Decided by a reviewer, who reads every `go` statement and asks how it ends. A test can confirm it: `go.uber.org/goleak` fails a test that leaves a goroutine running, and the runtime's `goroutineleak` profile — an experiment in Go 1.26, generally available in Go 1.27 through `runtime/pprof` and `/debug/pprof/goroutineleak` — reports goroutines blocked on a primitive no runnable goroutine can reach. Sources: Go Code Review Comments, *Goroutine Lifetimes*; the Uber Go style guide, *Don't fire-and-forget goroutines*.
   - **Exempt:** a goroutine started once from `main` that runs for the life of the process, with a comment saying so.

2. **No memory location is written by one goroutine while another reads or writes it without synchronisation.** Decided by the race detector: `go test -race` over the project's tests reports nothing. The detector reports only races that happen on a path a test executes, so a reviewer reads the state a change shares across goroutines that no test runs concurrently. A map is not merely raced: since Go 1.6 the runtime detects some concurrent misuse of a map and crashes the program. Source: the Go memory model — "Programs that modify data being simultaneously accessed by multiple goroutines must serialize such access."

3. **No value of a `sync` type, or a struct containing one, is copied after first use.** `sync.Mutex`, `RWMutex`, `WaitGroup`, `Once`, `Cond`, `Map` and the `sync/atomic` types are held by pointer once used. Decided by `go vet`'s `copylocks` analyzer, which runs by default. Source: the `sync` package documentation — "A Mutex must not be copied after first use."

4. **`WaitGroup.Add` runs before the `go` statement whose goroutine it counts.** An `Add` inside the goroutine races with `Wait`, which may see a zero counter and return early. Decided by `go vet`'s `waitgroup` analyzer from Go 1.25, and by `staticcheck`'s `SA2000` on earlier toolchains. `WaitGroup.Go`, added in Go 1.25, starts and counts in one call and cannot get the order wrong. Source: the `sync` package documentation for `WaitGroup.Add`.

5. **Every `CancelFunc` returned by `context.WithCancel`, `WithTimeout` or `WithDeadline` is called on every path.** An uncalled cancel leaks the context's resources until its parent is cancelled. Decided by `go vet`'s `lostcancel` analyzer, which runs by default. Source: the `context` package documentation, which names that check.

6. **No `nil` is passed where a `context.Context` is expected.** Decided by `staticcheck`'s `SA1012`. Source: the `context` package documentation — "Do not pass a nil Context, even if a function permits it. Pass `context.TODO` if you are unsure about which Context to use."

7. **A channel is closed only by its sending side, exactly once, and nothing sends on it afterwards.** With several senders, the owner closes it after a `WaitGroup` says they are all done. Decided by a reviewer, who reads who sends and who closes. Source: the Go specification, *Close* — sending to or closing a closed channel causes a run-time panic.

8. **On a module whose `go.mod` declares a version below 1.22, no closure that outlives a loop iteration captures the loop variable.** Decided by `go vet`'s `loopclosure` analyzer. From Go 1.22 each iteration declares its own variable and the condition no longer exists. Source: the Go 1.22 release notes.

## Where this stops

**Condition 1 has no static detector, and that is not for want of looking.** Whether a goroutine can end depends on what it blocks on and who still holds the other end, which is a property of the running program. `goleak` and the leak profile see it at run time, on the paths a test drives; a reviewer sees it on the paths no test drives. Neither is complete.

**Condition 2 is only as strong as the tests are concurrent.** A race on a path no test runs with two goroutines is invisible to `-race`. The detector has no false positives — every report is a real race — so the threshold is zero, and the gap is coverage, not tolerance.

**Nothing here chooses between a channel and a mutex.** Effective Go's "share memory by communicating" is a design preference, not a defect when it is not followed. A mutex around a map is correct; [`docs/concurrency.md`](../docs/concurrency.md) argues when each fits.

**A lock held across a blocking call is not a condition.** It serialises everything behind one slow call, but whether a call blocks for long depends on what is on the other side of it. The review skill reads it as a finding with a scenario, not as a rule.

**Condition 8 is moot on a modern module and stays because old modules exist.** A module that raises its `go` directive to 1.22 retires it, and `go vet` stops reporting it there.

**How a context is passed is not here.** That a context is the first parameter, never stored in a struct, and not replaced halfway down is [`context.md`](context.md), which a hook decides.
