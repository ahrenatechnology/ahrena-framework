---
id: resources
type: rule
clade: engineering
subclade: go
title: Every resource released on every path
statement: Go code releases every resource it acquires on every path, right after the error check, never in a loop's defer, and checks iteration and close errors.
enforcement: judgment
references:
  - docs/error-handling.md
  - docs/toolchain.md
---

# Every resource released on every path

Go has no destructor. A file, a response body, a result set, a prepared statement, a transaction and a connection stay open until code closes them, and the garbage collector reclaiming the struct does not reclaim the connection pool slot or the file descriptor behind it. The language gives one tool for this — `defer` — and the conditions below are the three ways it is misused and the two errors it hides.

Three are decided by linters the consuming project enables, one by a `go vet` analyzer that runs by default, one by `staticcheck`'s default set, and the rest by a reader. [`docs/error-handling.md`](../docs/error-handling.md) covers the deferred-close error in a named result; [`docs/toolchain.md`](../docs/toolchain.md) says which linters are enabled and why.

## Conditions

1. **A resource acquired by a call that also returns an error is released by a `defer` placed immediately after that error check.** Not before it, where the resource may be nil, and not further down, where an early return skips it. Decided by `bodyclose` for an `http.Response` body, by `sqlclosecheck` for `sql.Rows` and `sql.Stmt`, and by a reviewer for files, transactions, connections, tickers and the rest. Sources: the `net/http` package documentation — "The caller must close the response body when finished with it"; the `database/sql` documentation for `Rows` and `Stmt`.
   - **Exempt:** a resource whose ownership the function hands to its caller, by returning it or storing it in a value the caller closes. The doc comment says the caller closes it.

2. **A response is not used before the error that says whether it is valid has been checked.** Decided by `go vet`'s `httpresponse` analyzer, which reports a `defer resp.Body.Close()` placed before the `err` check, where `resp` may be nil.

3. **No `defer` that releases a per-iteration resource sits directly in a loop body.** A deferred call runs when the function returns, not when the iteration ends, so a loop over a thousand files holds a thousand descriptors. Decided by `staticcheck`'s `SA9001` for a `range` loop and `SA5003` for an infinite one, both on by default, and by `revive`'s `defer` rule with its `loop` check, or `gocritic`'s `deferInLoop`, for the rest. The fix is to move the body into a function, so its defers run each iteration.

4. **After iterating `sql.Rows`, the code checks `rows.Err()`.** `Next` returns false both when the rows are exhausted and when reading them failed, and only `Err` tells the two apart. Decided by `rowserrcheck`. Source: the `database/sql` documentation for `Rows.Next` — "Rows.Err should be consulted to distinguish between the two cases."

5. **The error from closing something written to is checked, not discarded by the `defer`.** A deferred `Close` on a file opened for writing, a `bufio.Writer`'s `Flush`, a `gzip.Writer`'s `Close` and a transaction's `Commit` each report a failure the writes before them did not. The pattern is a named `err` result the deferred function assigns when it is still nil. Decided by a reviewer. Source: the Linux `close(2)` manual, which notes that an error from a previous write may be reported only on the final close, and Go Code Review Comments, *Handle Errors*.
   - **Exempt:** a `Close` on a handle opened only for reading, whose error carries nothing the program can act on.

## Where this stops

**Condition 1's linters know a closed list of types.** `bodyclose` knows a response body, `sqlclosecheck` knows the `database/sql` types and some driver types. A project's own type with a `Close` method, an `os.File`, a `net.Conn`, a `time.Ticker`: a reviewer reads those. A `time.Ticker` that is never stopped is no longer a leak on a module at Go 1.23 or later, where the garbage collector reclaims it, which is why `staticcheck`'s `SA1015` documents itself as a pre-1.23 concern.

**Ownership transfer is not decided by anything.** Whether a function hands a resource to its caller or forgot to close it looks the same to a linter that reads one function. The exemption in condition 1 is the reviewer's to grant, against the doc comment.

**Nothing here bounds how long a resource is held.** A transaction open across a network call or a lock-free file kept open for a request's life is released correctly and still costs throughput. That is a design question the review of the change reads with its scenario.

**Contexts and goroutines are not resources here.** A goroutine that never exits and a `CancelFunc` never called are leaks too; they are [`concurrency.md`](concurrency.md), conditions 1 and 5, because what releases them is cancellation, not `Close`.
