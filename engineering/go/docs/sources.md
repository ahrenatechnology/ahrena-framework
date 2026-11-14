---
id: sources
type: doc
clade: engineering
subclade: go
title: Where this plugin's Go claims come from, and in what order
summary: The order of authority every rule and doc here follows — the Go Specification and memory model, accepted proposals, the standard library's documentation, then the community's guidance — and every place the plugin departs from that guidance, with the reason.
references:
  - docs/toolchain.md
  - docs/project-layout.md
  - docs/testing.md
---

# Where this plugin's Go claims come from, and in what order

Every claim in this plugin that a tool does not decide names its source. This page says which sources outrank which, why, and where the plugin chose differently from the community's guidance. It exists because Go has an unusually clear hierarchy of texts, and a rule that cites a style guide where the specification already decides the question is weaker than it needs to be.

## The order of authority

1. **The Go Specification** (`go.dev/ref/spec`) — the language: what a program means, what is a compile error, what panics at run time. Cited by section name, which is also its anchor: *Import declarations*, *Map types*, *Defer statements*, *Comparison operators*. On 2026-11-14 it is the version for Go 1.27.
2. **The Go memory model** (`go.dev/ref/mem`) — what a concurrent program may observe, and the definition of a data race.
3. **Accepted proposals** in `golang/go`, cited by issue number — the record of why a feature exists and what it was meant to do: #29934 (error wrapping, Go 1.13), #53435 (`errors.Join`, Go 1.20), #51945 (`errors.AsType`, Go 1.26), #60078 (per-iteration loop variables, Go 1.22), #40221 (`context.WithoutCancel`, Go 1.21), #56345 (`log/slog`, Go 1.21), #45713 (workspaces, Go 1.18), #63796 (`WaitGroup.Go`, Go 1.25), #74609 (the goroutine leak profile, Go 1.26 and 1.27), #62026 (the `uuid` package, Go 1.27).
4. **The documentation of the standard library and the `go` command** — normative for what each package and subcommand does, where the specification is silent because the subject is a library or a tool: `context`, `sync`, `errors`, `net/http`, `database/sql`; *Internal packages*, *Test packages*, *Build constraints* in `cmd/go`; the module reference, `go.dev/ref/mod`.
5. **The community's guidance**, used to choose among options the texts above leave open: Go Code Review Comments (`go.dev/wiki/CodeReviewComments`), Effective Go, the Go blog, and the Google and Uber Go style guides. The plugin follows Code Review Comments and Effective Go as the Go project's own guidance, and the two company guides where they agree with those.
6. **The documentation of the tools** — `staticcheck`, `golangci-lint`, `revive`, `errcheck`, `govulncheck` — cited for what a check reports, never for what is correct.

A lower source never overrides a higher one. Where the specification decides a question, the rule cites it and a style guide is at most a second citation.

## Effective Go is cited as history

Effective Go says of itself that it "was written for Go's release in 2009 and is not actively updated". It predates modules, generics, error wrapping and `context`. The plugin cites it for what has not changed — formatting, `panic` and `recover`, zero values, "share memory by communicating" — and never for a question a later text settles.

## Where the plugin departs from the community's guidance

Each departure is deliberate and is stated where it applies.

| Guidance | What the plugin does instead | Why |
|---|---|---|
| The Uber guide recommends `go.uber.org/atomic` over `sync/atomic` | The standard library's typed atomics (`atomic.Int64`, `atomic.Bool`, `atomic.Pointer[T]`) | Go 1.19 added them, which removes the reason the Uber section gives; the guide predates them. See [`docs/concurrency.md`](concurrency.md). |
| `errorlint`'s `errorf` check and `wrapcheck` treat `%w` as the default | `%w` only where the cause is part of the API; translate or `%v` otherwise | The Go blog's *Working with Errors in Go 1.13* treats wrapping as an API commitment, and accepted proposal #29934 is the text both rest on. Condition 3 of [`rules/errors.md`](../rules/errors.md). |
| Go Code Review Comments and the blog *Contexts and structs* each allow one exception for a context in a struct | The hook allows neither; the project excludes the path and writes why | A hook that guessed which exception applies would be a hook that guesses. [`rules/context.md`](../rules/context.md). |
| The Go repository groups tests by feature (`serve_test.go`) | Every file with behaviour has its own `foo_test.go` beside it | The owner's directive for every language plugin of this framework: a reader who opens a file finds its test without a search. Measured against the Go source, the departure is 62% of files. [`rules/test-placement.md`](../rules/test-placement.md). |
| `golang-standards/project-layout` is widely copied | The official *Organizing a Go module* page | The repository says of itself that it is "NOT an official standard"; the official page is a primary source. [`docs/project-layout.md`](project-layout.md). |
| Code Review Comments' *Useful Test Failures* allows a project's own assertion helpers if they produce useful messages | `got`/`want` with `cmp.Diff`, and `testify` only where a project already has it | The Go FAQ and the Google guide argue against assertion libraries, and they outrank a permission. [`docs/testing.md`](testing.md). |

## How a claim is checked

Every source above was read in its current text on 2026-11-14 — not recalled — and every quotation in this plugin is from that reading. A page that changes after that date can make a citation wrong; the first person to notice updates the artifact that cites it and the date here.

## Where this stops

**Thresholds are not sourced here.** A number in this plugin is either zero — a condition with no tolerance — or one taken from the fundamentals plugin, which carries its own measurements. The Go plugin adds none.

**The specification is not paraphrased.** A rule cites a section and quotes at most a sentence of it. The specification is the place to read the rest.

**Security guidance is not ranked here.** The security plugin's disciplines have their own sources, including the Go vulnerability database that `govulncheck` reads. Where a Go rule serves one of them — [`rules/exposure.md`](../rules/exposure.md) serves the rule from #294 that nothing sensitive leaves its layer — the security rule outranks this plugin, and the Go rule says only how the language holds it.
