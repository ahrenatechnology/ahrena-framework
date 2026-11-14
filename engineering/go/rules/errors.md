---
id: errors
type: rule
clade: engineering
subclade: go
title: Errors that reach the caller who can act on them
statement: Go code checks every error, inspects errors with errors.Is and errors.As, handles each error once, and panics only for a programmer's broken invariant.
enforcement: judgment
references:
  - docs/error-handling.md
  - docs/toolchain.md
---

# Errors that reach the caller who can act on them

Go reports failure as a value. That design is only as good as the path the value travels: an error dropped on the floor is a failure nobody sees, an error compared with `==` after somebody wrapped it is a failure the caller misreads, an error logged at every layer is one failure reported five times, and a `panic` for a bad input is a failure the caller was never given a chance to handle. The five conditions below are those four paths and the one place a panic is correct.

Two of the five are decided by linters the consuming project runs, and three need a reader. [`docs/error-handling.md`](../docs/error-handling.md) argues each one from its source and works the decisions this rule leaves to the author — when to wrap with `%w` and when with `%v`, where an error is logged, how a sentinel differs from an error type. [`docs/toolchain.md`](../docs/toolchain.md) says how the two linters are configured and why they are required rather than suggested.

## Conditions

1. **No error result is discarded by a call whose error is never read.** A call statement that drops an `error` result is a discarded error. Decided by `errcheck`, which is in `golangci-lint`'s default set; the threshold is zero reports, because an unchecked error is not a quantity to stay under. An assignment to `_` is not decided by `errcheck` unless its `check-blank` option is on, and is read by a reviewer against the exemption below, as is a `defer f.Close()` on a file opened for writing, whose error is the last report of a write that failed. Source: Go Code Review Comments, *Handle Errors* — "Do not discard errors using `_` variables."
   - **Exempt:** a call whose documentation states that the error is always nil — `bytes.Buffer.Write`, `strings.Builder.WriteString`, `hash.Hash.Write` — and `Close` on a handle opened only for reading. The `_` assignment stays, so the choice is visible; the reason is the documentation, and the reviewer checks it is cited or obvious.

2. **An error is inspected with `errors.Is`, `errors.As` or `errors.AsType`, never with `==`, `!=`, a type assertion or a type switch.** Decided by `errorlint`'s `comparison` and `asserts` checks, enabled by the project. A direct comparison stops matching the moment anyone between the source and the check wraps the error, and since Go 1.13 anyone may. Source: the Go blog, *Working with Errors in Go 1.13*; the `errors` package documentation, which adds `AsType` in Go 1.26 and prefers it to `As` for most uses.
   - **Exempt:** `io.EOF` compared directly against the result of a `Read` the standard library documents as returning it unwrapped. `errorlint` carries that allow-list itself, so the exemption costs nothing to configure.

3. **An error a caller is meant to inspect is wrapped with `%w` on every frame between where it is made and where it is inspected; an error that is not part of the package's API is wrapped with `%v` or translated.** Decided by a reviewer, who reads the package's documented sentinels and error types and follows each one to the boundary. `errorlint`'s `errorf` check reports every `%v` applied to an error and cannot tell a deliberate translation from a flattened chain, so it is a prompt for this condition and not its detector. Source: the Go blog, *Working with Errors in Go 1.13*, section *Whether to Wrap* — wrapping "makes that error part of your API"; the Google Go style guide, best practices, *Adding information to errors*.

4. **An error is handled once: returned with context, or logged and acted on, never both.** Decided by a reviewer, who follows one error from where it is made to the frame that ends its journey. A function that logs an error and also returns it produces one log line per frame for one failure. Source: the Uber Go style guide, *Handle Errors Once*.
   - **Exempt:** the top of a request or a goroutine, which logs the error and converts it into a response, a status or an exit code. That is the one place it is handled.

5. **`panic` is raised only for a broken invariant a programmer caused, and `os.Exit` or `log.Fatal` only in `main`.** A failure an input, a file, the network or the database can cause is returned as an `error`. Decided by a reviewer for `panic`, and by `revive`'s `deep-exit` rule, enabled by the project, for an exit outside `main` and `init`. A `recover` sits only at the boundary of a goroutine or a request, turns the panic into that unit's failure, and lets the rest of the program run. Sources: Go Code Review Comments, *Don't Panic*; Effective Go, *Panic* and *Recover*; the Google Go style guide, decisions, *Don't panic* and *Must functions*; the Uber Go style guide, *Exit in Main*.
   - **Exempt:** a `Must` function, named for it, called at package initialisation with a constant argument — `regexp.MustCompile` is the model — and a `switch` default or assertion the code makes impossible, whose panic message says which invariant broke.

## Where this stops

**Condition 1's detector does not see every discard.** `errcheck` reports calls; it does not see an error assigned to a variable that is then overwritten before anyone reads it, which is `ineffassign`'s job and is also in the default set, nor an error stored in a struct field and never looked at. No linter in the default set follows a field, so a reviewer reads it.

**Condition 2 does not ask for errors to be wrapped.** It asks that inspection survive wrapping. A package that never wraps still passes, and condition 3 decides whether it should have.

**Condition 3 has no linter, and the closest one points the wrong way.** `wrapcheck` requires every error from another package to be wrapped, and `errorlint`'s `errorf` requires `%w` wherever an error is formatted. Both treat wrapping as the default. The Go blog treats it as a commitment, and a rule that required `%w` everywhere would make every dependency's error part of every API. A project may still run either linter as a prompt; the condition is decided by reading what the package promises.

**Condition 4 has no opinion on the log level or the message.** Whether a failure is logged at `ERROR` or `WARN`, and with which fields, is [`docs/logging-and-observability.md`](../docs/logging-and-observability.md), not a condition here.

**Condition 5 does not reach `panic` in a test.** `t.Fatal` and a panicking helper in a `_test.go` file stop a test, which is what a test is for.

**Nothing here reaches an error value that is wrong.** An error with the right type, wrapped correctly and handled once, can still describe the wrong failure. That is a defect in the logic, read by the review of the logic.

**A typed nil returned as an `error` is not in this rule.** It is a nil trap, and [`nil-safety.md`](nil-safety.md) holds it with the other two.
