---
id: toolchain
type: doc
clade: engineering
subclade: go
title: The Go toolchain, and what each part decides
summary: Which tools a Go project runs — gofmt, go vet, staticcheck, golangci-lint and which of its linters, the race detector, govulncheck, module hygiene — what each decides for this plugin's rules, why the set stops where it does, and the commands CI runs.
references:
  - rules/errors.md
  - rules/concurrency.md
  - rules/context.md
  - rules/resources.md
  - rules/nil-safety.md
  - rules/api-surface.md
---

# The Go toolchain, and what each part decides

Go ships more of its toolchain than most languages do: the formatter, the vetter, the test runner, the race detector, the coverage tool, the fuzzer and the module system are all one download. This document says which of them, and which of the tools outside the distribution, this plugin's rules depend on, and why each one is there. It is the companion of all six rules: wherever a rule says a condition is "decided by" a tool, this is where that tool is placed in the pipeline.

It configures nothing. There is no `.golangci.yml` here, for the same reason the Python plugin ships no `pyproject.toml`: a configuration file is true for one project at one version, and a framework that ships one is shipping a thing people copy without reading. What is here is the argument a project needs to write its own file and defend every line of it.

## The version a project builds with

Go supports each major release "until there are two newer major releases" (the Go release history, `go.dev/doc/devel/release`). On 2026-11-14 that is Go 1.27, released in August 2026, and Go 1.26, released in February 2026. A module whose `go` directive names a release older than 1.26 builds on a toolchain that no longer receives security fixes.

The `go` directive in `go.mod` is not decoration: it decides language semantics. A module that declares `go 1.21` keeps the shared loop variable that Go 1.22 removed (condition 8 of [`rules/concurrency.md`](../rules/concurrency.md)), and the [`context`](../rules/context.md) hook reads the same directive to decide whether `context.WithoutCancel` exists. The `toolchain` directive suggests a newer toolchain without raising the minimum, and the default `GOTOOLCHAIN=auto` downloads it when the local one is older; a CI that wants to build with exactly the toolchain it installed sets `GOTOOLCHAIN=local`, so a stale CI image fails loudly instead of quietly switching.

## gofmt: settled, never discussed

`gofmt` is in the distribution and its output is the style. Effective Go puts the position plainly: "let the machine take care of most formatting issues", and if its output seems wrong, "rearrange your program (or file a bug about `gofmt`), don't work around it." `goimports`, from `golang.org/x/tools/cmd/goimports`, is `gofmt` plus import management and is what most editors run.

CI runs `gofmt -l .` and fails when it prints a file. No rule in this plugin has a formatting condition, because none is needed: a formatter that is run decides formatting completely, and a review comment about formatting is a sign the formatter was not.

## go vet: the default set, all of it

`go vet` runs every analyzer it has by default — the `cmd/vet` documentation says so in one sentence, "By default, all checks are performed" — and setting any one flag restricts it to the flags set. So CI runs `go vet ./...` with no flags, and gets every analyzer the installed toolchain knows, including the ones a later release adds.

Five of its analyzers decide conditions in this plugin's rules:

| Analyzer | Decides | Rule |
|---|---|---|
| `copylocks` | a `sync` value copied after first use | [`concurrency.md`](../rules/concurrency.md) condition 3 |
| `waitgroup` (Go 1.25) | `WaitGroup.Add` inside the goroutine it counts | [`concurrency.md`](../rules/concurrency.md) condition 4 |
| `lostcancel` | a `CancelFunc` not called on every path | [`concurrency.md`](../rules/concurrency.md) condition 5 |
| `loopclosure` | a loop variable captured, on modules below Go 1.22 | [`concurrency.md`](../rules/concurrency.md) condition 8 |
| `httpresponse` | a response used before its error is checked | [`resources.md`](../rules/resources.md) condition 2 |

`go test` runs a small subset of vet on its own — `atomic`, `bools`, `buildtag`, `directive`, `errorsas`, `ifaceassert`, `nilfunc`, `printf`, `stdversion`, `stringintconv` and `tests`, per the `go` command's documentation — which is why a project that only runs tests still catches a misused `errors.As`. It does not catch `copylocks` or `lostcancel`, so `go vet` is a separate step.

The `nilness` analyzer is the exception worth knowing: it lives in `golang.org/x/tools`, `gopls` runs it in the editor by default, and `go vet` does not. Condition 4 of [`rules/nil-safety.md`](../rules/nil-safety.md) names it, and a project that wants it in CI enables it through `golangci-lint`'s `govet` settings.

## staticcheck, through golangci-lint

`staticcheck` decides four conditions here — `SA5000` (assignment to a nil map), `SA4023` (an impossible comparison of an interface with nil), `SA1012` (a nil context), `SA9001` and `SA5003` (defers in loops that do not run when expected) — and every one of them is in its default configuration, which turns on all checks except a handful of style checks (`ST1000`, `ST1003`, `ST1016`, `ST1020` to `ST1023`) and `SA9003`. Since `golangci-lint` v2, `gosimple` and `stylecheck` are merged into its `staticcheck` linter, so one entry carries all three.

The plugin runs `staticcheck` inside `golangci-lint` rather than beside it, because the rules need `golangci-lint` anyway and two runners over one tree is two configurations to keep in step.

## golangci-lint: the default five, and the linters the rules ask for

`golangci-lint` v2's default set is five linters: `errcheck`, `govet`, `ineffassign`, `staticcheck` and `unused`. That set is the floor, and it already decides [`rules/errors.md`](../rules/errors.md) condition 1 (`errcheck`) and every `go vet` and `staticcheck` condition above.

The rules then ask a project to enable these, each because a condition does not exist without it:

| Linter | Decides | Rule |
|---|---|---|
| `errorlint` (`comparison`, `asserts`) | an error compared with `==` or asserted instead of `errors.Is` / `errors.As` | [`errors.md`](../rules/errors.md) condition 2 |
| `revive` with `deep-exit` | `os.Exit` or `log.Fatal` outside `main` and `init` | [`errors.md`](../rules/errors.md) condition 5 |
| `bodyclose` | an HTTP response body not closed | [`resources.md`](../rules/resources.md) condition 1 |
| `sqlclosecheck` | `sql.Rows` or `sql.Stmt` not closed | [`resources.md`](../rules/resources.md) condition 1 |
| `rowserrcheck` | `rows.Err()` not checked after iteration | [`resources.md`](../rules/resources.md) condition 4 |
| `forcetypeassert` | a single-result type assertion | [`nil-safety.md`](../rules/nil-safety.md) condition 3 |
| `revive` with `unexported-return` | an exported function returning an unexported type | [`api-surface.md`](../rules/api-surface.md) condition 1 |
| `revive` with `exported` | an exported name without a doc comment | [`api-surface.md`](../rules/api-surface.md) condition 4 |

Two more are worth enabling beside the [`context`](../rules/context.md) hook, because they read with types where the hook reads spelling: `containedctx`, which reports a context field the hook's spelling misses, and `contextcheck`, which follows a non-inherited context through a call. Neither is required; the hook decides the rule's conditions without them.

**Refused, with the reason.**

- **`enable-all`.** It turns on linters whose positions contradict each other and this plugin's rules — `wrapcheck` requires every foreign error to be wrapped, which [`errors.md`](../rules/errors.md) condition 3 argues against — and a new `golangci-lint` release adds linters to it silently. A list the project wrote is a list it can defend.
- **`wrapcheck`, and `errorlint`'s `errorf` check as a gate.** Both treat `%w` as the default. The Go blog treats wrapping as a commitment that "makes that error part of your API". A project may run them as prompts; neither decides a condition.
- **`gosec` inside this set.** Security is the security plugin's subject, with its own disciplines; enabling `gosec` here would put a security posture into a language document.
- **Style linters with no defect behind them** — `goconst`, `intrange`, `usestdlibvars`, `paralleltest` and the like. They produce findings nobody needs to read in review. A project that likes them adds them.

**How it is installed.** `golangci-lint`'s own documentation recommends the binary install and says installs through `go install`, the tools pattern or the `tool` directive "aren't guaranteed to work"; it says plainly it does not recommend `go tool`. So CI installs a pinned binary release, and the pin lives in the CI configuration, where it is one line to bump.

## The race detector

`go test -race` instruments memory accesses and reports every data race that happens while the tests run. It has no false positives, which is why condition 2 of [`rules/concurrency.md`](../rules/concurrency.md) sets its threshold at zero reports. It also sees only what runs: the race detector article states that it finds races on executed code paths, and that its cost is five to ten times the memory and two to twenty times the run time. That cost is why it runs in CI over the test suite rather than in production, and why the rule pairs it with a reviewer for state no test exercises concurrently.

It needs cgo and runs on a fixed list of platforms (Linux, macOS, FreeBSD, NetBSD and Windows on the common architectures); a CI image without a C toolchain cannot run it, which is a fact about the image to fix rather than a reason to drop the flag.

## govulncheck

`govulncheck`, from `golang.org/x/vuln`, reports known vulnerabilities in the module's dependencies and the standard library, and in source mode reports only those "based on which functions in your code are transitively calling vulnerable functions". That is the property that makes it a gate rather than a dashboard: a finding is a vulnerable function the program can reach. It exits non-zero when it finds one, and zero regardless when asked for JSON, SARIF or OpenVEX output, so the gate runs it in its default text mode.

No rule in this plugin names it, because a vulnerable dependency is a supply-chain question, which belongs to the security plugin's `reviewing-supply-chain` discipline. It is here because a Go pipeline without it is missing the one tool built for Go's call graph.

## Module hygiene

`go mod tidy` makes `go.mod` and `go.sum` match the source: it adds what is imported and missing and removes what nothing imports. CI runs `go mod tidy -diff`, which prints the change and exits non-zero when one is needed, so a pull request cannot land with a `go.mod` that disagrees with its imports. `go mod verify` checks that the modules in the local cache have not been modified since they were downloaded, against the hashes in `go.sum`.

Since Go 1.24 the `tool` directive records a tool a module runs — `go get -tool` adds it, `go tool` runs it — and pins it in `go.mod` with the rest of the dependencies. That is the right home for `staticcheck`, `govulncheck` and `goimports` when a project runs them directly; it is not the home for `golangci-lint`, for the reason its documentation gives above.

## go fix

Since Go 1.26 `go fix` is "the home of Go's modernizers", built on the same analysis framework as `go vet`. It rewrites code to newer idioms — a loop that `slices.Contains` replaces, a `WaitGroup` pattern that `WaitGroup.Go` replaces — and Go 1.27 adds more. It is a tool a person runs and reviews the diff of, not a gate: a modernizer's suggestion is a style change, and none of this plugin's conditions depends on one.

## The commands CI runs

In order, cheapest first, each failing the build on output or non-zero exit:

```
gofmt -l .
go mod tidy -diff
go vet ./...
golangci-lint run ./...
go test -race -shuffle=on ./...
govulncheck ./...
python3 engineering/go/hooks/check-source.py .
```

`-shuffle=on` randomises test order and reports the seed, so a test that only passes after another one has run is found the first time the order changes, and the failure is reproducible from the seed. The last line is this plugin's own hook; it needs Python and nothing else, and decides [`rules/context.md`](../rules/context.md) and condition 2 of [`rules/api-surface.md`](../rules/api-surface.md), the one condition no linter in the catalogue reports.

## Where this stops

**This document chooses linters; it does not configure them.** Each linter named above has options, and the defaults are what the rules assume unless a rule names an option, as [`rules/errors.md`](../rules/errors.md) does for `errcheck`'s `check-blank`. A project that changes a default writes down why, beside the change.

**It pins no version.** Every version in a configuration file is true until the next release, and the release cadence of `golangci-lint` alone would date this page within weeks. The versions above are of Go itself, because they decide semantics the rules depend on.

**It does not cover the editor.** `gopls` runs much of the same analysis interactively, plus `nilness`. An editor is a convenience; the gate is CI.

**Supply chain and security are not here.** `govulncheck` is described because it belongs to a Go pipeline; deciding what a finding means, and what else a supply-chain review reads, is the security plugin's.

**The hook has not been measured on a public corpus**, and [`rules/context.md`](../rules/context.md) says so. The tools above have, by their own projects, over years; the hook has its fixtures.
