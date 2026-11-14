# Go conditions no rule holds

Opened by step 2 of `SKILL.md` for the defects a Go reader catches that are not a rule's condition: each depends on what the surrounding code intends, so it is read with a scenario rather than decided. A finding cites the identifier. Every defect a rule holds is cited by the rule's path and condition number instead, and is not repeated here.

### GO-1 A deferred call that captures a value too early

- **State:** a `defer` whose arguments are evaluated when the `defer` statement runs, not when the deferred call does, so it acts on a stale value — `defer log.Printf("took %v", time.Since(start))` reports zero, `defer fmt.Println(status)` prints the status before the function changed it.
- **Detect:** read each `defer` the change adds and ask which of its arguments change between the `defer` and the return. The Go Specification, *Defer statements*, says the function value and parameters are evaluated when the statement executes.
- **Exempt:** a value captured on purpose at that point, such as the start time itself.
- **Correct:** wrap the call in a closure, `defer func() { log.Printf("took %v", time.Since(start)) }()`, so the arguments are evaluated at return.

### GO-2 A lock held across a blocking call

- **State:** a `sync.Mutex` or `RWMutex` held while the goroutine does network or disk I/O, sends or receives on a channel, or calls out to code it does not control, so every other caller of the lock waits on the slowest call.
- **Detect:** read every `Lock` the change adds or extends and list what runs before its `Unlock`. A call that takes a `context.Context` is a call that can block.
- **Exempt:** a critical section whose blocking call is the thing the lock serialises on purpose — a single writer to a file.
- **Correct:** copy what the critical section needs, unlock, then do the blocking work; or move the shared state behind a goroutine that owns it.

### GO-3 A select loop that spins

- **State:** a `for { select { … default: … } }` whose `default` branch performs no blocking operation — no channel send or receive, no lock, no sleep, no call that takes a context — so the loop polls instead of blocking and burns a CPU core while it waits. `staticcheck`'s `SA5004` reports the empty `default`; a reader reads the non-empty one against that list.
- **Detect:** read every `select` with a `default` inside a loop.
- **Exempt:** a non-blocking send or receive attempted once, outside a loop.
- **Correct:** remove the `default` so the `select` blocks, and add `case <-ctx.Done():` so it can still stop.

### GO-4 A sub-slice retained inside the package

- **State:** a sub-slice (`buf[i:j]`) stored in a struct or a map while the original keeps being appended to or reused, so the stored slice changes under it; or a small sub-slice of a large buffer retained, which keeps the whole buffer alive. Condition 5 of `rules/api-surface.md` holds the same aliasing at the exported surface; this is the case inside one package.
- **Detect:** read where a slice expression's result outlives the statement, and whether its source is appended to, reused or large.
- **Exempt:** a sub-slice of an array that is never written again.
- **Correct:** copy it — `slices.Clone(buf[i:j])` — or cap it with a full slice expression, `buf[i:j:j]`, so a later append reallocates.

### GO-5 A zero value used where a constructor was required

- **State:** a struct declared with `var x T` or `T{}` and used, where `T`'s methods assume fields a constructor sets — a nil map inside it (which `rules/nil-safety.md` condition 1 then holds), a nil function, a zero timeout that means "wait forever", a zero `time.Time` passed where a real time was assumed.
- **Detect:** read the type's documentation and constructor. A type whose zero value is not useful says so, or returns an error from methods called on it.
- **Exempt:** a type designed to work at its zero value — `sync.Mutex`, `bytes.Buffer`, `strings.Builder` — which Effective Go, *Allocation with new*, calls the property to aim for.
- **Correct:** call the constructor; or make the zero value valid by initialising lazily in the methods.

### GO-6 A pattern imported from another language against Go's grain

- **State:** a construct whose premise belongs to another language and that Go expresses differently: an interface declared beside its only implementation and named `IStore` or `StoreInterface`; a constructor that returns an interface "for testability"; a getter named `GetName` (Effective Go, *Getters*: "it's neither idiomatic nor necessary to put Get into the getter's name"); a class hierarchy rebuilt from embedded structs and overridden methods; an error raised as a `panic` and caught with `recover` as an exception; a dependency-injection container or reflection-based wiring in place of constructors called from `main`.
- **Detect:** read each new type, interface and constructor against `docs/project-layout.md`, section *SOLID and inversion of control, in Go's form*. Several of these are also conditions elsewhere — the producer-side interface is `rules/api-surface.md` condition 3, the panic-as-exception is `rules/errors.md` condition 5 — and a finding cites that rule when it applies.
- **Exempt:** a name or shape a dependency imposes, such as a method required by a third-party interface.
- **Correct:** the Go form the project-layout doc names: a concrete type, an interface declared by its consumer, a constructor taking its dependencies as parameters, an error value.
