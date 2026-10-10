# Go errors

Opened by step 2 of `SKILL.md` when the change touches a returned error, a panic, or a deferred close. Each condition gives the state, how it is detected, what exempts it, and the correction.

### GO-1 An error ignored

- **State:** a returned error assigned to `_` or dropped, where the call can fail meaningfully — `_ = f.Close()` on a writable file, `_, _ = w.Write(...)`, a bare call to a function whose last return is `error`.
- **Detect:** every call that returns an error and is not checked. `errcheck` flags most; a review catches the ones in a `defer` and the deliberate `_` that should not be.
- **Exempt:** a close on a read-only handle, or a write to an in-memory buffer that cannot fail, with the `_` making the choice visible.
- **Correct:** check it and return or handle it. On a deferred close whose error matters (a writable file, a flush), capture it into the named return.

### GO-2 An error wrapped so callers can no longer match it, or double-wrapped

- **State:** an error returned bare where the caller needs context (`return err` with no `%w`), or wrapped with `fmt.Errorf("...: %v", err)` which flattens it so `errors.Is`/`errors.As` can no longer see the cause; or a sentinel exposed that the package did not mean to promise.
- **Detect:** read how the error is built and how callers inspect it. `%v` breaks the chain; `%w` keeps it.
- **Exempt:** deliberately hiding an internal cause at a package boundary so it is not part of the API, with a comment.
- **Correct:** `fmt.Errorf("doing x: %w", err)` to wrap with context and keep matchable; add context at each layer, not at every line.

### GO-3 A sentinel compared with `==` instead of `errors.Is`

- **State:** `if err == io.EOF` or `err == ErrNotFound` where the error may be wrapped, so the comparison fails even though the cause is that sentinel; or a type assertion `err.(*MyError)` instead of `errors.As`.
- **Detect:** each direct comparison or assertion against an error the change adds.
- **Exempt:** comparing against an error the same function just returned unwrapped (e.g. `io.EOF` straight from a `Read` the stdlib documents as unwrapped).
- **Correct:** `errors.Is(err, ErrNotFound)`; `errors.As(err, &target)`.

### GO-4 A panic used for an ordinary error

- **State:** `panic` on an input or state that is a normal failure (a missing key, a bad request, a parse error), especially in a library, where it crashes the caller's program; or a `recover` that swallows a panic and continues in an unknown state.
- **Detect:** read what triggers the panic. If a caller could cause it with ordinary input, it is an error value, not a panic.
- **Exempt:** a truly unrecoverable programmer error (an impossible switch default, a failed invariant at init), or `recover` at a goroutine or request boundary that logs and fails that unit cleanly.
- **Correct:** return an `error`; reserve panic for impossible states.

### GO-5 A deferred call whose placement or evaluation is wrong

- **State:** a `defer` inside a loop that piles up until the function returns (file handles, locks held for the whole function); a `defer` whose arguments are evaluated at the `defer`, not at the call, capturing a stale value; a `defer` placed before the error check that would skip the resource's creation.
- **Detect:** read each `defer` the change adds, its loop context, and when its arguments are taken.
- **Exempt:** a `defer` in a function called once per iteration (extract the loop body), or one whose captured value is intended.
- **Correct:** move the per-iteration work into its own function so the defer runs each iteration; evaluate volatile values inside a closure; place the defer right after a successful acquire.

### GO-6 An error logged and also returned, or neither

- **State:** an error both logged and returned, so it is reported twice up the stack; or an error neither logged nor returned at a boundary where it vanishes.
- **Detect:** follow one error up. It should be handled once — logged at the top, or returned, not both at every layer.
- **Exempt:** a top-level handler that logs and converts to a response, which is the one place it is handled.
- **Correct:** return with context on the way up; log once, where it is finally handled.
