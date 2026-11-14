---
id: context
type: rule
clade: engineering
subclade: go
title: A context that travels with the call
statement: A context.Context is the first parameter, is never stored in a struct, and is passed down, never swapped for a new root context mid-call.
enforcement: hook
enforced-by: hooks/check-context.py
references:
  - docs/concurrency.md
---

# A context that travels with the call

A `context.Context` carries a deadline, a cancellation signal and request-scoped values from the caller to everything the call does. It does that only while it is passed from frame to frame. Stored in a struct, it outlives the call it belonged to and every method on the struct inherits a cancellation that is not its own. Moved to the second parameter, it stops being where every reader and every tool looks for it. Replaced by `context.Background()` halfway down, it silently cuts the deadline: the caller gives up, and the work it asked for keeps running.

The three conditions are taken from the `context` package's own documentation: "Do not store Contexts inside a struct type; instead, pass a Context explicitly to each function that needs it. The Context should be the first parameter, typically named ctx." The Go blog, *Contexts and structs*, argues the first at length, and the Google Go style guide, decisions, *Contexts*, states both. The third follows from the second and from Go 1.21, which added `context.WithoutCancel` for the one legitimate reason to start over: a task that must outlive the request but should keep its values. [`docs/concurrency.md`](../docs/concurrency.md) works the cancellation model these conditions protect.

## Conditions

Each of these is decided by [`hooks/check-context.py`](../hooks/check-context.py), which reads Go source with the Python standard library and needs nothing installed, Go included.

1. **No struct field has the type `context.Context`, named or embedded.** The hook reads every `struct { … }` in a file that imports `context`, and reports a field whose whole type is the package's `Context`, under whatever name the file imports it as.
   - **Exempt:** nothing in the hook. The two sources each allow one exception, and they are different: the blog allows a struct kept for backward compatibility with an API that predates contexts, `http.Request` being its example; Go Code Review Comments, *Contexts*, allows methods whose signature must match an interface in the standard library or a third-party library. Either is a path the project leaves out of the hook's arguments, with the reason written where the path is.

2. **A parameter of type `context.Context` is the first parameter.** Read in every function declaration, method declaration and function literal. A method's receiver is not a parameter; type parameters are not parameters; a grouped list (`parent, child context.Context`) puts the context first.
   - **Exempt:** a `*testing.T`, `*testing.B`, `*testing.F` or `testing.TB` before it, which is the convention for a test helper and the one `revive`'s `context-as-argument` rule allows through its `allow-types-before` option.

3. **A function that has a `context.Context` parameter does not call `context.Background()` or `context.TODO()` in its body.** The body includes the function literals inside it, so a goroutine started by a request handler is held. The fix is to pass the parameter down, or, for work that must outlive the call, `context.WithoutCancel(ctx)`.
   - **Exempt:** a module whose `go.mod` declares a version below 1.21, where `WithoutCancel` does not exist. The hook reads the nearest `go.mod` and does not decide this condition there; conditions 1 and 2 still hold.

## Where this stops

**The hook does not type-check, and that is the price of needing nothing installed.** A context is recognised by its spelling: the identifier the file imports `"context"` under, a dot, `Context`. A named type defined as `type Ctx = context.Context`, a context reached through a dot-import, and a struct field holding an interface that happens to be satisfied by a context are all invisible to it. `containedctx` and `contextcheck` in `golangci-lint` read with types and see some of these; a project that runs them gets the rest.

**Condition 1 does not read a field whose type contains a context.** A `map[string]context.Context`, a `[]context.Context` and a `func() context.Context` are all fields that only mention one, and the hook leaves them alone. The first two store contexts as surely as a plain field does and are rare enough to leave to a reviewer; the third is a factory, which is how a struct legitimately reaches for a context it does not own.

**Condition 3 does not follow a context through a call.** A function that receives `ctx` and calls a helper that calls `context.Background()` passes; the helper has no context parameter, so the hook has nothing to hold it to. That interprocedural case is what `contextcheck` exists for, and it needs the type checker the hook refuses to depend on.

**Condition 3 says nothing about `main`, `init` or a test.** They have no context to propagate, so `context.Background()` is where the tree starts, and since Go 1.24 a test should start from `t.Context()`, which [`docs/testing.md`](../docs/testing.md) covers.

**Generated code is not held.** A file whose header matches the convention `go generate` documents — a line `// Code generated … DO NOT EDIT.` — is skipped, as are `vendor/`, `testdata/` and directories the `go` tool ignores by their leading `.` or `_`.

**The hook has not been measured against a public corpus.** It was written and tested against the fixtures in [`hooks/test-check-context.py`](../hooks/test-check-context.py), without a Go standard library on hand to run it over. Its false-positive rate on real code is unknown, and the first project to run it will be the first measurement; the rule carries no threshold that depends on it, because each condition's threshold is zero.

**Two context defects live in the concurrency rule, not here.** A `CancelFunc` that is not called on every path, which `go vet`'s `lostcancel` analyzer decides, and a `nil` passed where a context is expected, which `staticcheck`'s `SA1012` decides, are conditions of [`concurrency.md`](concurrency.md), because both are about what a goroutine is left holding rather than about how a context is passed.
