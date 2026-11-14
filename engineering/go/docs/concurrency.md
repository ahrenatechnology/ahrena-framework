---
id: concurrency
type: doc
clade: engineering
subclade: go
title: Concurrency in Go — ownership, synchronisation and cancellation
summary: Why every goroutine needs an owner and how to give it one, when a channel fits and when a mutex does, what errgroup and WaitGroup.Go add, how cancellation flows through a context, and what the memory model actually promises.
references:
  - rules/concurrency.md
  - rules/context.md
  - docs/testing.md
  - docs/libraries.md
---

# Concurrency in Go — ownership, synchronisation and cancellation

This is the companion of [`rules/concurrency.md`](../rules/concurrency.md) and [`rules/context.md`](../rules/context.md). The rules state what must hold; this argues the model behind them, so that an author writing new concurrent code reaches for the right primitive instead of finding out from a reviewer.

## Prefer not to start one

Go Code Review Comments, *Synchronous Functions*: "Prefer synchronous functions - functions which return their results directly or finish any callbacks or channel ops before returning - over asynchronous ones." Its reason is the whole of this document in two sentences: synchronous functions "keep goroutines localized within a call, making it easier to reason about their lifetimes and avoid leaks and data races", and a caller who wants concurrency can add it, while "it is quite difficult - sometimes impossible - to remove unnecessary concurrency at the caller side."

So the first question about a `go` statement is whether the function should start it at all, or return and let its caller decide.

## Every goroutine has an owner

The Go Specification, *Go statements*, defines a goroutine as "an independent concurrent thread of control" and gives the `go` statement no result: nothing it returns can be waited on or stopped. When a goroutine is warranted, Code Review Comments, *Goroutine Lifetimes*, says "make it clear when - or whether - they exit", and names the usual leak: a goroutine blocked on a channel send or receive, which the garbage collector "will not terminate … even if the channels it is blocked on are unreachable." The Uber guide's *Don't fire-and-forget goroutines* says the same in production terms.

The owner is whatever started the goroutine, and it holds two things: a way to tell it to stop, and a way to wait until it has. In practice there are three shapes.

**A group of tasks with a result.** `errgroup.WithContext` from `golang.org/x/sync/errgroup` starts each task with `g.Go`, cancels the derived context the first time one returns an error, and `g.Wait` returns that error once all have exited. `g.SetLimit(n)` bounds how many run at once, which replaces a hand-built semaphore. It is the default for fan-out inside a request.

**A group of tasks that cannot fail.** `sync.WaitGroup` with `wg.Go(f)`, added in Go 1.25, starts and counts in one call. Before 1.25, `wg.Add(1)` goes before the `go` statement, never inside the goroutine — the `sync` documentation requires that a positive `Add` on a zero counter happen before `Wait`, and condition 4 of the rule holds it.

**A long-lived worker.** A type with a `Start` or `Run(ctx)` that loops until its context is cancelled, and a way for the caller to wait for it — `Run` itself blocks until the loop exits, so the caller runs it in an `errgroup` and waits on the group. The worker's loop `select`s on `ctx.Done()` beside its work channel, so cancellation reaches it even when no work arrives.

What none of these leaves is a `go func() { … }()` with nothing holding the other end.

## Channels or a mutex

Effective Go: "Do not communicate by sharing memory; instead, share memory by communicating." That is a design preference, and the *Goroutine Lifetimes* text above is the warning that comes with it: a channel is also something a goroutine can block on forever.

The working distinction is ownership. **A channel transfers ownership** of a value from one goroutine to another: a producer hands work to a consumer and no longer touches it. A pipeline — the Go blog's *Go Concurrency Patterns: Pipelines and cancellation* — is channels end to end, and every stage closes its output when its input is done. **A mutex guards state that several goroutines share** and none owns: a cache, a counter, a connection map. Wrapping such state in a goroutine that serves requests over a channel is legal and is almost always slower and harder to read than a `sync.Mutex` beside the map.

For a single counter or flag, the typed atomics in `sync/atomic` — `atomic.Int64`, `atomic.Bool`, `atomic.Pointer[T]` — are the right size. The Uber guide still recommends its own `go.uber.org/atomic` here; that advice predates the typed atomics the standard library added in Go 1.19, and the standard library is the answer now.

A mutex is held by pointer once used — the `sync` documentation says "A Mutex must not be copied after first use", and `go vet`'s `copylocks` checks it — and its zero value is an unlocked mutex, so it needs no constructor. The critical section is kept to the state it guards: a lock held across a network call serialises every caller behind the slowest response.

## What the memory model promises

The Go memory model defines a data race as a write to a memory location concurrent with another read or write to the same location, and states the consequence for programs plainly: "Programs that modify data being simultaneously accessed by multiple goroutines must serialize such access." It also gives its most useful advice in one line: "If you must read the rest of this document to understand the behavior of your program, you are being too clever. Don't be clever."

In practice that means every shared access goes through a channel operation, a `sync` primitive or a `sync/atomic` operation, which are what the model defines happens-before edges for. A `bool` flag read in a loop without one of them is a race even when it "works" on the developer's machine. The race detector reports it the first time a test runs both sides; condition 2 of the rule requires it to report nothing.

Maps deserve their own sentence: since Go 1.6 the runtime detects some concurrent misuse of a map and crashes the program rather than corrupting it. A map shared between goroutines is guarded by a mutex, or is a `sync.Map` when the access pattern is the one its documentation describes — keys written once and read many times, or disjoint key sets per goroutine.

## Cancellation flows through the context

A `context.Context` carries the deadline and the cancellation of the operation that created it, and every function below inherits them only if it is passed down. The `context` package documentation fixes how: "Do not store Contexts inside a struct type; instead, pass a Context explicitly to each function that needs it. The Context should be the first parameter, typically named ctx." The Go blog's *Contexts and structs* argues the first half; [`rules/context.md`](../rules/context.md) holds all three conditions with a hook.

The Go Specification has no notion of cancellation; it is the `context` package's, and its documentation is the normative text for this section. A goroutine started inside a request takes the request's context, so it stops when the request is abandoned. Work that must outlive the request — an audit write after the response is sent — takes `context.WithoutCancel(ctx)`, added in Go 1.21 by accepted proposal golang/go#40221, which keeps the request's values (its trace, its tenant) and drops its cancellation. Reaching for `context.Background()` instead drops the values too, and the trace breaks.

Every `WithCancel`, `WithTimeout` and `WithDeadline` returns a `CancelFunc` that is called on every path, usually by `defer cancel()` on the next line; `go vet`'s `lostcancel` checks it. Go 1.20 and 1.21 added `WithCancelCause`, `WithDeadlineCause` and `WithTimeoutCause`, whose cause `context.Cause` reports — worth using where "context canceled" in a log would leave the reader asking why.

## Testing concurrent code

Three tools, each covering what the others cannot. `go test -race` finds the races the tests execute. `testing/synctest`, generally available since Go 1.25, runs a test in a bubble with a fake clock, so code that waits on timers is tested deterministically and fast. `go.uber.org/goleak` fails a package whose tests leave goroutines behind, and the runtime's `goroutineleak` profile, generally available in Go 1.27, finds goroutines blocked on something unreachable in a running program — its release notes are candid that it detects "a large class" of leaks, not all. [`docs/testing.md`](testing.md) shows where each goes in a suite.

## Where this stops

**No pattern catalogue.** Worker pools, pipelines, pub-sub and rate limiters are built from the primitives above, and the Go blog's pipeline post is a better tutorial than a summary would be.

**Performance is not argued.** Whether a channel or a mutex is faster for a given contention profile is a benchmark's question, and a page that answered it without one would be inventing a number.

**Distributed concurrency is not here.** Locks across processes, leader election and idempotent consumers are the reliability plugin's subject; this page stops at the process boundary.

**The libraries named here are chosen in [`docs/libraries.md`](libraries.md)**, with what each lacks and when it is wrong.
