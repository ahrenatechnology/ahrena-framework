---
id: test-placement
type: rule
clade: engineering
subclade: go
title: The test sits beside the file it tests
statement: A Go file that declares a function or method has its own foo_test.go beside it, in the same directory, so the reader who opens one finds the other.
enforcement: hook
enforced-by: hooks/check-test-placement.py
references:
  - docs/testing.md
---

# The test sits beside the file it tests

The `go` command gives tests a fixed place: "'Go test' recompiles each package along with any files with names matching the file pattern "*_test.go"", and a test file in the package's own directory either belongs to the package or, when its package clause carries the `_test` suffix, is "compiled as a separate package" linked into the same test binary (the `go` command documentation, *Test packages*). So the test of a package is always in the package's directory. This rule narrows that to the file: `orders.go` is tested by `orders_test.go`, beside it, so a reader who opens either finds the other without a search, and a file whose behaviour has no test is visible by its missing neighbour.

The narrowing is the owner's directive for every language plugin of this framework, and it departs from what the Go repository itself does: on the Go 1.27.4 source measured below, most files are tested by a test file named for a feature rather than for the file. [`docs/testing.md`](../docs/testing.md) argues why the plugin follows the directive anyway, and where each kind of test lives.

## Conditions

Decided by [`hooks/check-test-placement.py`](../hooks/check-test-placement.py), which reads Go source with the Python standard library and needs nothing installed.

1. **A Go source file that declares a function or a method, other than `main` and `init`, has a test file named for it in the same directory.** `orders.go` is answered by `orders_test.go`. A file whose name ends in a build-constraint suffix the `go` command recognises — `orders_linux.go`, `orders_linux_amd64.go` — is answered by the test of its whole stem or of the stem without that suffix, because the suffix selects a platform rather than naming a subject (the `go` command documentation, *Build constraints*). The test file may declare the package or the package with the `_test` suffix; both are in the directory, which is what the condition reads.
   - **Exempt:** a file that declares only types, constants and variables, which has no behaviour to test on its own; a `main.go` whose only functions are `main` and `init`, which is wiring; a generated file, `testdata/`, `vendor/` and the directories the `go` tool ignores.

## Where this stops

**The condition reads that a test file exists, not what it tests.** An empty `orders_test.go` satisfies it. Whether the test exercises the file's behaviour, and whether a function's branches are covered, is a reviewer's reading and the coverage report [`docs/testing.md`](../docs/testing.md) describes; this framework sets no coverage threshold because none has been measured.

**Tests that cross units live where the language's convention puts them, and are not held here.** An integration test of a store against a real database, an end-to-end test of a binary, and an example test are named for the behaviour they exercise. They still sit in a package directory, because the `go` command finds tests nowhere else, but none of them answers condition 1 for a file it was not named for.

**The Go repository does not follow it, and the measurement says how far.** On the Go 1.27.4 source of `net/http`, `database`, `context` and `cmd/go` — 273 non-test files, of which 255 declare a function or method — the hook reports 158: 62% of the files with behaviour have no test named for them, because the standard library groups tests by feature (`serve_test.go`, `transport_test.go`) across files. That is the size of the departure from common practice this rule takes on purpose, and it is why the rule is the owner's to change, not the hook's to soften.

**A file split for size is held twice.** Splitting `orders.go` into `orders.go` and `orders_cancel.go` asks for `orders_cancel_test.go`. That is the intent: a file that solves its own problem, as single responsibility down to the file asks, has its own test. A split made only to shorten a file, with no problem of its own, is the thing that request is meant to expose.

**Where a unit's test belongs inside the file is not here.** Table tests, subtests, fakes and golden files are [`docs/testing.md`](../docs/testing.md); this rule only places the file.
