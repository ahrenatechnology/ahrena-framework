# Go concurrency

Opened by step 2 of `SKILL.md` when the change touches a `go` statement, a channel, a `sync` primitive, a context or a shared variable. The race detector and `go vet` catch some of this; a reader catches the leaks and the misuse they do not.

### GO-7 A goroutine that can leak

- **State:** a `go func()` that blocks on a channel send/receive or a lock with no exit path — no `context` it selects on, no closed channel, no timeout — so when its caller returns the goroutine lives forever.
- **Detect:** read every `go` the change starts. Ask how it ends. A goroutine writing to an unbuffered channel whose only reader has gone away blocks forever.
- **Exempt:** a goroutine meant to run for the program's life (a supervisor loop), started once, documented.
- **Correct:** pass a `context.Context` and `select` on `ctx.Done()`; ensure the channel is closed or buffered; give blocking ops a timeout.

### GO-8 A `context.Context` dropped, stored or ignored

- **State:** a function that drops the `ctx` its caller passed and uses `context.Background()`/`context.TODO()` instead; a `ctx` stored in a struct field rather than passed as the first argument; a blocking call that takes a `ctx` but is given one that is never cancelled.
- **Detect:** follow the context from the entry point. A dropped context means cancellation and deadlines stop propagating, and the leak in GO-7 follows.
- **Exempt:** a genuine top-level or detached task that must outlive the request, started with a fresh context on purpose, with a comment.
- **Correct:** thread `ctx` as the first parameter and pass it down; select on `ctx.Done()` in loops and blocking waits.

### GO-9 A data race on shared state

- **State:** a variable, map or slice read and written from more than one goroutine with no mutex, channel or atomic; a `sync.WaitGroup` whose `Add` runs inside the goroutine instead of before it; a map written concurrently (which panics, not just races).
- **Detect:** find state that outlives one goroutine and is touched by another. The race detector finds these only on a code path a test exercises, so a review still reads them.
- **Exempt:** state handed off by value through a channel and never shared, or guarded by a mutex held across every access.
- **Correct:** guard with `sync.Mutex`/`RWMutex`, move ownership to one goroutine behind a channel, or use `sync/atomic` for a counter; call `wg.Add` before `go`.

### GO-10 A loop variable captured by a goroutine or closure (Go before 1.22)

- **State:** `for _, v := range xs { go func(){ use(v) }() }` on a module whose `go.mod` declares a version below 1.22, where every goroutine sees the final `v`.
- **Detect:** check `go.mod`. From 1.22 each iteration has its own variable and this is fixed; below it, the capture is a bug.
- **Exempt:** Go 1.22+, or the value passed as an argument (`go func(v T){...}(v)`).
- **Correct:** pass the value as an argument, or `v := v` inside the loop; or raise the module's Go version.

### GO-11 A channel closed wrong or selected without a default

- **State:** a channel closed by a receiver or by more than one sender (a close on a closed channel panics); a send on a channel that may be closed; a `select` with no `default` where a non-blocking path was intended, or a busy `default` loop that spins.
- **Detect:** read who closes and who sends. The sender closes, exactly once; receivers never close.
- **Exempt:** a single-sender channel closed once by that sender.
- **Correct:** close from the sole sender; coordinate multiple senders with a `sync.WaitGroup` then close; use `ctx` or a done channel to stop receivers.

### GO-12 A mutex copied or held across a blocking call

- **State:** a struct containing a `sync.Mutex` copied by value (passed or returned), which copies the lock state; a lock held across I/O, a channel op or a long call, serialising everything; a `Lock` with no deferred or guaranteed `Unlock` on an error path.
- **Detect:** `go vet` flags a copied lock; a reader catches the held-too-long and the missing unlock.
- **Exempt:** a lock deliberately held across a short critical section.
- **Correct:** hold a `*T` with the mutex, never copy it; `defer mu.Unlock()` right after `Lock`; shrink the critical section to exclude I/O.
