---
id: testing
type: doc
clade: engineering
subclade: go
title: Testing Go with the standard toolchain
summary: How a Go test suite is shaped — table tests and subtests, failure messages with got before want, fakes over mocks, golden files, fuzzing, integration tests against real dependencies, concurrency under -race and synctest — and which flags CI passes.
references:
  - docs/toolchain.md
  - docs/libraries.md
  - docs/concurrency.md
  - rules/concurrency.md
---

# Testing Go with the standard toolchain

Go's test runner, fuzzer, race detector, coverage tool and benchmark harness are all `go test`. This document is how a suite uses them. It is Go's half of the testing discipline: test-first as a procedure is the backend plugin's `driving-with-tdd` skill, and this page is what that procedure looks like when the language is Go.

## A test fails with a message a stranger can act on

Go Code Review Comments, *Useful Test Failures*: "Tests should fail with helpful messages saying what was wrong, with what inputs, what was actually got, and what was expected." Its model is one line:

```go
if got != tt.want {
	t.Errorf("Foo(%q) = %d; want %d", tt.in, got, tt.want)
}
```

The order is deliberate — actual, then expected — and the same page notes that "some test frameworks encourage writing these backwards … Go does not." The Google Go style guide, decisions, repeats it as *Got before want*. `t.Errorf` records the failure and continues, so one run reports every broken case; `t.Fatalf` is for when the test cannot meaningfully go on.

The Go FAQ, *Where is my favorite helper function for testing?*, explains why `testing` has no assertion functions, and the Google guide says not to write assertion libraries. A comparison of two structs uses `cmp.Diff` from `github.com/google/go-cmp/cmp`, which prints what differs; [`docs/libraries.md`](libraries.md) says why that module and when `testify` stays.

A helper that fails a test calls `t.Helper()` first, so the failure is reported at the caller's line.

## Table tests and subtests

The Go wiki's *TableDrivenTests*: "Each table entry is a complete test case with inputs and expected results, and sometimes with additional information such as a test name to make the test output easily readable." The Go blog's *Using Subtests and Sub-benchmarks* adds `t.Run(tt.name, …)`, which gives each row its own name in the output, lets `-run 'TestParse/empty'` run one row, and lets a row call `t.Fatal` without stopping the others.

A table fits when the cases differ only in data. When rows start carrying flags that switch the test's logic — `wantErr`, `skipSetup`, `mockReturns` — the table is hiding several tests, and they read better as separate functions.

From Go 1.22 each loop iteration has its own variable, so a parallel subtest no longer needs `tt := tt`. On a module below 1.22 it still does, and `go vet`'s `loopclosure` reports its absence.

## Fakes over mocks

A unit under test that depends on storage or another service receives an interface its own package declares — [`docs/project-layout.md`](project-layout.md) argues why — with the two or three methods it calls. The test passes a fake: a struct that implements those methods over a map or a slice, and that can be told to fail. A fake describes behaviour, so a test written against it survives a refactor that changes which methods are called in which order; a generated mock asserts the calls, and does not. `go.uber.org/mock` is for the case [`docs/libraries.md`](libraries.md) names, a large interface someone else owns.

## Golden files

When the output is large and textual — a rendered template, a generated file, a formatted report — the expected value lives in a file under `testdata/`, which the `go` tool ignores, and the test compares against it. Go's own repository shows the convention in `go/printer`'s tests: a flag, `var update = flag.Bool("update", false, "update golden files")`, that rewrites the golden files instead of comparing. `go test ./... -update` regenerates them, and the diff of the golden files is reviewed like code. A golden file nobody reads when it changes is a test that always passes.

## Fuzzing

Go has fuzzing in the standard toolchain since Go 1.18 (`go.dev/doc/security/fuzz`). A `FuzzXxx(f *testing.F)` function seeds a corpus with `f.Add` and runs a property over generated inputs with `f.Fuzz`. It earns its place on code that parses untrusted input — a decoder, a URL or header parser, a protocol message — where the property is "does not panic" or "round-trips". A failing input is written to `testdata/fuzz/FuzzXxx/`, becomes part of the seed corpus, and runs on every plain `go test` from then on, so a crash found once is a regression test forever.

`go test -fuzz` runs one fuzz target in one package until stopped; CI runs the seed corpus as ordinary tests and leaves open-ended fuzzing to a scheduled job.

## Integration tests against the real thing

A store is tested against the database it runs on, with the migrations applied: an in-memory imitation agrees with the real engine about everything except the constraint, the isolation level or the type coercion that the test was supposed to catch. `github.com/testcontainers/testcontainers-go` starts the database in a container from `TestMain` and removes it afterwards. HTTP handlers are tested through `net/http/httptest`, which serves a handler on a real listener or records a response without one.

Integration tests are separated by build tag or by `testing.Short()`, so `go test -short ./...` runs the fast suite locally and CI runs both.

## Concurrency under test

Three tools, each covering what the others do not, which [`docs/concurrency.md`](concurrency.md) explains. In a suite they sit as follows. CI always passes `-race`, so every test that runs two goroutines is also a race test; condition 2 of [`rules/concurrency.md`](../rules/concurrency.md) requires it to report nothing. A test of code that waits on timers wraps its body in `synctest.Test`, from `testing/synctest`, generally available since Go 1.25, and the fake clock advances when every goroutine in the bubble is blocked. A package whose code starts goroutines calls `goleak.VerifyTestMain(m)` in `TestMain`, so a test that leaves one running fails.

## What the testing package added recently

Several additions remove helpers that suites used to write by hand. `t.Context()`, from Go 1.24, returns a context cancelled just before the test's cleanups run, which is the context a test passes to the code under test instead of `context.Background()`. `b.Loop()`, also Go 1.24, is the benchmark loop that keeps the compiler from optimising the measured work away. `t.Chdir`, Go 1.24, changes directory and restores it. `t.Output` and `t.Attr`, Go 1.25, write to the test's own output stream and attach key-value attributes to it.

## What CI runs

`go test -race -shuffle=on ./...`. `-shuffle=on` randomises the order of tests and reports the seed, so a test that only passes after another has run fails visibly and reproducibly. `-count=1` is the documented way to bypass the test cache when a run must not reuse a cached result, such as a nightly job against a changing dependency. Coverage is collected with `-cover` and `-coverpkg`, and [`docs/toolchain.md`](toolchain.md) places the step in the pipeline.

## Where this stops

**No coverage threshold.** Nothing measured in this framework supports a number, and a number nobody measured is the threshold the framework refuses everywhere else. Coverage is a report a reviewer reads to find untested branches, not a gate.

**Test-first as a procedure is not here.** The red-green-refactor loop, and what a test at each layer of a service exercises, are the backend plugin's `driving-with-tdd` and `specifying-with-bdd`. This page is the Go mechanics they run on.

**End-to-end and contract tests across services are not covered.** They are the quality and backend plugins' subject.

**Benchmarks are mentioned, not argued.** `go test -bench` and `b.Loop` measure; deciding what is worth measuring is a performance question this page does not take on.
