---
name: writing-go
description: Use when Go code is to be written or changed to implement a behaviour - a handler, a use case, a store, a worker, a CLI command, a library function. Implements it test-first against this plugin's Go rules and docs - the package it belongs in and the direction it may import, constructor-injected dependencies behind consumer-declared interfaces, functions and files within the single-responsibility limits, a test file beside each file - and leaves the change passing gofmt, go vet, the race detector and the plugin's hooks. Read before writing the first line of Go, not after.
type: skill
clade: engineering
subclade: go
references:
  - rules/errors.md
  - rules/concurrency.md
  - rules/context.md
  - rules/resources.md
  - rules/nil-safety.md
  - rules/api-surface.md
  - rules/package-boundaries.md
  - rules/test-placement.md
  - docs/project-layout.md
  - docs/testing.md
  - docs/libraries.md
  - docs/toolchain.md
  - docs/error-handling.md
  - docs/concurrency.md
  - docs/logging-and-observability.md
  - skills/reviewing-go/SKILL.md
  - ahrena-engineering-fundamentals:rules/clean-code.md
  - ahrena-engineering-fundamentals:rules/kiss.md
  - ahrena-engineering-fundamentals:rules/solid.md
  - ahrena-engineering-fundamentals:rules/yagni.md
---

# Writing Go

This is what test-first looks like when the language is Go. The loop itself — the behaviour named first, the test red for the right reason, the smallest code to green, the refactor under green — is the backend plugin's `driving-with-tdd` skill, and a caller who runs that skill runs this one at its writing steps. On its own, this skill is the whole loop for a Go change.

Every limit below is held from the first line written, not left for the review to find.

## 1. Read the module before writing in it

Open `go.mod` and note the `go` directive: it decides which language and library features exist — per-iteration loop variables from 1.22, `context.WithoutCancel` from 1.21, `WaitGroup.Go` from 1.25, `errors.AsType` from 1.26, the `uuid` package from 1.27. Do not use a feature newer than the directive, and do not raise the directive as a side effect. Note whether a `go.work` lists several modules.

Then read what the project already decided: its CI workflow and `.golangci.yml` for which tools run, its `AGENTS.md`, and its component map for the folder and the vocabulary this change belongs in. Where the project is silent on layout, `docs/project-layout.md` is the default. Output: the Go version, the tools the pipeline runs, and the modules in play.

## 2. Place the change: package, layer, direction

Decide which package the change lives in before writing it, and hold the choice to `rules/package-boundaries.md`: a package named for what it provides, under `internal/` unless the module promises it to outside importers, in the layer its responsibility belongs to — `domain`, `application` or `infra` — importing only downward. A new variant of an existing behaviour is a new package that satisfies the interface or function type the base accepts, not a new branch in the base (condition 5 there, and the open/closed condition of `ahrena-engineering-fundamentals:rules/solid.md`).

Write down what the change exports, and hold it to `rules/api-surface.md`: concrete types out of constructors, an interface only in the package that consumes it, a doc comment on every exported name, nothing from `internal/` on a public signature.

A dependency — storage, a clock, another service — enters through the constructor, as a parameter typed by a small interface the consuming package declares with only the methods it calls. That constructor call in `main` is the whole of inversion of control; `docs/project-layout.md` argues it and lists the patterns from other languages that go against Go's grain. Do not add the interface until a second real consumer or a test that exists today needs the seam, which is `ahrena-engineering-fundamentals:rules/yagni.md`.

A function that does I/O or waits takes `ctx context.Context` as its first parameter (`rules/context.md`).

## 3. Write the test red, beside the file

For each file the change creates or edits, the test goes in the `_test.go` file named for it, in the same directory — `orders.go`, `orders_test.go` — which `rules/test-placement.md` holds. Follow `docs/testing.md`: a table of cases with `t.Run` when they differ only in data, failure messages with got before want, `cmp.Diff` for structures, a hand-written fake for each interface from step 2, `t.Context()` for the context under Go 1.24 or later. A store is tested against the real database with migrations applied; that integration test is named for the behaviour it exercises.

Run only that test and read the failure. It must fail because the behaviour is missing — an assertion about the result — not because the code does not compile or a fixture is wrong.

```sh
go test ./internal/orders/ -run 'TestCancel' -count=1
```

## 4. Write the smallest code that turns it green, inside the limits

Each function and method is small enough to test on its own and stays within the fundamentals' limits as it is written: at most 30 statements in its body (`ahrena-engineering-fundamentals:rules/clean-code.md` condition 1), control flow at most 3 deep, and no boolean parameter that steers its own branching (`ahrena-engineering-fundamentals:rules/kiss.md` conditions 1 and 2). A type whose methods share no field and call nothing in common is two types (`ahrena-engineering-fundamentals:rules/solid.md` condition 1). A file solves one problem; a second problem is a second file, with its own test. In Go the tool that reports a breach is `revive` with `function-length`, `max-control-nesting` and `flag-parameter`, set to those limits as `docs/toolchain.md` shows.

Open the rule for each construct as you reach for it — not after:

| Reaching for | Hold it to |
|---|---|
| a returned `error`, `fmt.Errorf`, a sentinel, `panic` | `rules/errors.md`, with `docs/error-handling.md` for the wrap-or-translate decision |
| a `go` statement, a channel, a mutex, `errgroup` | `rules/concurrency.md`, with `docs/concurrency.md` for which primitive |
| a context | `rules/context.md` |
| a file, response body, `sql.Rows`, transaction | `rules/resources.md` |
| a map, an interface-typed result, a type assertion | `rules/nil-safety.md` |
| a log line, a span, a metric | `docs/logging-and-observability.md` |

Prefer a synchronous function; start a goroutine only when the behaviour needs one, and give it an owner in the same change.

## 5. Add a dependency only from the recommendations

When the standard library does not cover what the code needs, look the problem up in `docs/libraries.md` and use the module it names, unless its "not when" case is this one. A problem the page does not list is a decision for the person who owns the project: stop and name the candidate and the gap in your output rather than adding it. Add with `go get`, then `go mod tidy`.

## 6. Run the gate the pipeline will run

Run what `docs/toolchain.md` lists, in its order, over the changed packages: `golangci-lint` only if the project runs it, and this plugin's four hooks always, since they need nothing but Python. The hook paths below are the ones in the framework's own checkout.

```sh
gofmt -l .
go vet ./...
go test -race -shuffle=on ./...
golangci-lint run ./...
python3 engineering/go/hooks/check-context.py .
python3 engineering/go/hooks/check-surface.py .
python3 engineering/go/hooks/check-packages.py .
python3 engineering/go/hooks/check-test-placement.py .
```

A failure is fixed in the code, not silenced: no `//nolint` without the linter's name and a reason, no `_` on an error the documentation does not say is always nil.

## 7. Refactor under green, then read the diff as a reviewer would

With the tests green, remove duplication and rename until the code says what the behaviour is, running the tests after each step. Then read your own diff against `skills/reviewing-go/SKILL.md`, its rules and its `GO-` conditions, and correct what it finds before anyone else reads it. Output: the red run from step 3, the green run from step 6, and the diff.

## When this skill does not apply

**Finding why existing Go misbehaves.** Diagnosing a defect is `debugging-go`; this skill takes over once the cause is known and a failing test pins it.

**Reviewing someone else's Go.** That is `reviewing-go`, which hands back findings and edits nothing.

**Deciding the architecture.** Which bounded contexts a service has and what each layer may know is the backend plugin's; this skill writes Go inside a structure already decided, in Go's own packages and layers.

**Generated code.** A file under `// Code generated … DO NOT EDIT.` is changed by changing its generator's input and regenerating, never by hand.
