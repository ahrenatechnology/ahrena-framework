---
id: error-handling
type: doc
clade: engineering
subclade: go
title: Error handling in Go, from the value to the boundary
summary: The decisions rules/errors.md leaves to the author — sentinels against error types, when to wrap with %w and when with %v, what an error message says, where an error is logged, the deferred-close error, panic and recover — each argued from its primary source.
references:
  - rules/errors.md
  - rules/nil-safety.md
  - rules/resources.md
  - docs/logging-and-observability.md
---

# Error handling in Go, from the value to the boundary

This is the companion of [`rules/errors.md`](../rules/errors.md). The rule states five conditions an error's journey must meet; this document is how an author makes the decisions the conditions leave open, in the order an error meets them: how it is made, how it travels, how it is inspected, where it stops.

## Make it: a sentinel, a type, or neither

Most errors need no identity. `fmt.Errorf("parsing %q: %w", name, err)` or `errors.New("empty order")` is enough when no caller will ever branch on which failure it was. An error gets an identity only when a caller is expected to act differently on it, and then it takes one of two forms.

**A sentinel** is a package-level variable — `var ErrNotFound = errors.New("orders: not found")` — compared with `errors.Is`. It fits when the failure carries no data beyond its kind. `io.EOF` and `sql.ErrNoRows` are the models.

**An error type** is a struct implementing `error`, matched with `errors.As` or, from Go 1.26, `errors.AsType`, which the `errors` package documents as type-safe, faster and preferred for most uses. It fits when the caller needs data from the failure — which field was invalid, which status the server returned. `*os.PathError` is the model.

Either one is a promise. Exporting `ErrNotFound` means every future version must still return something that `errors.Is` matches against it. The Go blog's *Working with Errors in Go 1.13* puts it in one line: wrapping an error "makes that error part of your API". So the question before exporting one is whether the package is prepared to keep returning it.

Naming follows a convention `staticcheck` checks by default (`ST1012`): a sentinel is `ErrSomething`, a type is `SomethingError`. The message follows Go Code Review Comments, *Error Strings*: not capitalised unless it begins with a proper noun or acronym, and no trailing punctuation, because it will be embedded in another message (`ST1005` checks it). Effective Go adds that an error string should "identify their origin, such as by having a prefix naming the operation or package that generated the error."

## Carry it: wrap with context, and choose the verb

Each frame an error passes through adds what that frame knows and the next one does not: the operation, the identifier. `fmt.Errorf("loading order %s: %w", id, err)` reads, at the top, as a path from what the program was doing to what failed. Two conventions keep that path readable. The Google Go style guide, best practices, says to prefer `%w` at the end of the string, so the chain reads outer to inner. The Uber Go style guide, *Error Wrapping*, says to keep the context succinct by "avoiding phrases like "failed to"", which every frame would otherwise repeat.

The verb is the decision. `%w` keeps the cause reachable by `errors.Is` and `errors.As`; `%v` keeps only its text. The Go 1.13 blog is explicit that this is an API choice: "Wrap an error to expose it to callers. Do not wrap an error when doing so would expose implementation details." Its own example is a database lookup — wrapping the `sql.ErrNoRows` from a store would let callers depend on the store being SQL. The Google guide's best practices, *Adding information to errors*, says the same at system boundaries — RPC, IPC, storage — where the right move is often to translate the error into the package's own vocabulary rather than wrap the foreign one.

So a store translates: `if errors.Is(err, sql.ErrNoRows) { return Order{}, ErrNotFound }`, and wraps everything else with `%v` or `%w` according to whether the caller may inspect it. Condition 3 of [`rules/errors.md`](../rules/errors.md) asks a reviewer to check exactly that, by following each documented sentinel from where it is made to where it is inspected.

Since Go 1.20, `errors.Join` and a `fmt.Errorf` with more than one `%w` build an error that wraps several causes, and `errors.Is` matches any of them. That is the shape for validation, which reports every violation at once, and for a cleanup that fails after the main operation already failed.

Go 1.27's `go vet` adds one more check to `printf`: it reports `fmt.Errorf("…: %w", p)` where `p` is a `*E` whose `E` itself implements `error`, because wrapping the pointer to a value-receiver error makes `errors.As` and type assertions miss it.

## Inspect it: `errors.Is` and `errors.As`, always

Once anyone in the chain may wrap, `err == ErrNotFound` stops matching. Condition 2 of the rule requires `errors.Is` and `errors.As` (or `AsType`) for that reason, and `errorlint` decides it. The one exception the linter already carries is `io.EOF` straight from a `Read`, which the standard library documents as returned unwrapped.

## Stop it: handle once, at the frame that can act

An error is handled when some frame decides what it means for the program: it retries, it returns a 404, it exits. Every frame before that one adds context and returns. Logging in each of them produces one log line per frame for one failure, each without the context the next frame up adds — the Uber guide's *Handle Errors Once* is condition 4 of the rule.

In a service, the frame that handles is almost always the top of the request: the HTTP handler or the RPC method maps the error to a status — a sentinel to a 404, a validation error to a 400, anything else to a 500 — and logs the 500s once, with the request's context. [`docs/logging-and-observability.md`](logging-and-observability.md) covers what that log line carries.

## The deferred close that carries an error

A `defer f.Close()` on a file written to discards the one error that says whether the data reached the disk; the Linux `close(2)` manual notes that a failure from an earlier write may be reported only at close. [`rules/resources.md`](../rules/resources.md) condition 5 holds it, and the pattern is a named result:

```go
func write(path string, data []byte) (err error) {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer func() {
		if cerr := f.Close(); cerr != nil && err == nil {
			err = cerr
		}
	}()
	_, err = f.Write(data)
	return err
}
```

`errors.Join(err, cerr)` is the alternative when both errors matter.

## The nil that is not nil

An interface is nil only when both its type and its value are unset — the Go FAQ, *Why is my nil error value not equal to nil?* So a function that declares `var e *ValidationError` and returns it as `error` on the success path hands back a non-nil error holding a nil pointer, and every caller's `if err != nil` fails. The fix is to return the untyped `nil` on success, and to keep a concrete pointer in a variable of its own type until the moment it is known to be non-nil. [`rules/nil-safety.md`](../rules/nil-safety.md) condition 2 holds it.

## panic and recover

Go Code Review Comments, *Don't Panic*: "Don't use panic for normal error handling. Use error and multiple return values." Effective Go is written for Go's 2009 release and is no longer updated, but its *Panic* section still states the reasoning: "real library functions should avoid `panic`. If the problem can be masked or worked around, it's always better to let things continue to run rather than taking down the whole program." Its exception is initialisation that cannot proceed, which survives as the `Must` convention the Google guide's decisions name — `regexp.MustCompile` at package level, with a constant argument.

`recover` belongs at the boundary of a unit of work. Effective Go's *Recover*: "One application of `recover` is to shut down a failing goroutine inside a server without killing the other executing goroutines." `net/http` does this for each request already. A goroutine a service starts itself has no such guard: a panic in it ends the process, so a long-lived worker that should survive a bad message recovers at the top of its loop, turns the panic into that message's failure, logs it with the stack, and continues.

A `recover` anywhere else hides a broken invariant and keeps running in a state nobody understands.

## Where this stops

**No error library is recommended.** Since Go 1.13 the standard library has wrapping, and since Go 1.20 multiple wrapping; the third-party packages that added stack traces to errors predate both. A stack belongs in the log line at the frame that handles the error, which `slog` and a panic's own output carry; [`docs/libraries.md`](libraries.md) lists no error module for that reason.

**The mapping from errors to HTTP or gRPC statuses is not specified.** It is a contract decision for each API, and the backend plugin's contract-first rule owns it. This page says only that it happens once, at the top.

**Retrying on an error is not here.** Which errors are transient and how to back off is the reliability plugin's subject, and [`docs/libraries.md`](libraries.md) names the module.
