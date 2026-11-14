---
name: reviewing-go
description: Use when a change under review edits Go (.go) and the question is what a Go reader would catch - an error ignored or compared so callers can no longer match it, a goroutine with no owner, a context stored or replaced, a resource left open on an error path, a provider's error or a whole struct written to a response or a log, a nil interface that is not nil, an exported function leaking an internal type. Reads the routed files against this plugin's Go rules and the few conditions no rule holds; every finding names the rule and condition.
type: skill
clade: engineering
subclade: quality
references:
  - rules/errors.md
  - rules/concurrency.md
  - rules/context.md
  - rules/resources.md
  - rules/nil-safety.md
  - rules/api-surface.md
  - rules/package-boundaries.md
  - rules/test-placement.md
  - rules/exposure.md
  - docs/toolchain.md
  - docs/project-layout.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Go

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold in any language. This skill reads it against this plugin's Go rules, which state each condition once with what decides it, and against the six conditions in `references/beyond-the-rules.md` that no rule holds.

A finding cites `rules/<rule>.md` and the condition number, or a `GO-` identifier from the reference. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `go` route on the changed `.go` files. Those are the files this skill reads.

Read the module's `go` directive in `go.mod` first: it decides real conditions. Below 1.22 a loop variable is shared (`rules/concurrency.md` condition 8); below 1.21 there is no `context.WithoutCancel` (`rules/context.md` condition 3); `WaitGroup.Go` needs 1.25 and `errors.AsType` 1.26.

Then read what the project's pipeline runs: its CI workflow, its `.golangci.yml`, its `AGENTS.md`. `docs/toolchain.md` lists which tool decides which condition. A condition a check in this pull request's CI already decided — `copylocks` in `go vet`, `errcheck` in `golangci-lint`, `-race` in the tests — is settled and not reported again. A condition whose tool the project does not run is read here, and the finding says which tool would have decided it.

## 2. Run the hooks, then open the rules the change calls for

`rules/context.md`, `rules/test-placement.md`, conditions 1 to 3 of `rules/exposure.md`, condition 2 of `rules/api-surface.md` and conditions 2 and 3 of `rules/package-boundaries.md` are decided by scripts that need only Python. Run this plugin's hooks — the lines below are their paths in the framework's own checkout — the first four over the changed files and the package hook over the module, since a layer is decided by the whole tree, and take each report as a finding of the rule it names.

```sh
python3 engineering/go/hooks/check-context.py <changed .go files>
python3 engineering/go/hooks/check-surface.py <changed .go files>
python3 engineering/go/hooks/check-test-placement.py <changed .go files>
python3 engineering/go/hooks/check-exposure.py <changed .go files>
python3 engineering/go/hooks/check-packages.py .
```

Then open the rules for what the change touches:

| What the change touches | Read |
|---|---|
| a returned `error`, an `errors.Is`/`As`, `fmt.Errorf`, a `panic`, `recover`, `os.Exit` | `rules/errors.md` |
| a `go` statement, a channel, a `sync` or `sync/atomic` value, a `WithCancel`/`WithTimeout`, a shared variable | `rules/concurrency.md` |
| a file, a response body, `sql.Rows`, a transaction, a connection, a `defer` that releases one | `rules/resources.md` |
| a map, a function returning an interface, a type assertion, a pointer returned beside an error | `rules/nil-safety.md` |
| an exported identifier, a new interface, a constructor, a slice or map crossing the package boundary | `rules/api-surface.md` |
| a new package or module, an import across packages, a new variant of an existing behaviour | `rules/package-boundaries.md`, with `docs/project-layout.md` |
| a response, an error returned across a layer, a log or trace call, a `fmt` verb, a type holding a credential | `rules/exposure.md`, the Go form of the security plugin's rule from #294 |
| any `defer`, `Lock`, `select` in a loop, sub-slice stored, struct used at its zero value, or a pattern from another language | `references/beyond-the-rules.md` |

A change that only edits a pure function's arithmetic opens none of these; say the Go pass found nothing specific.

## 3. Read beyond the hunk

Follow each changed function to its callers and to what it returns. Whether an error is inspected correctly is decided at the call site, not the `return`; whether a goroutine has an owner is decided where the function that starts it returns; whether a resource leaks is decided on the error path the diff may not show. Read the base revision of a line before calling it wrong.

## 4. Apply the conditions

Work condition by condition. Give the scenario in Go terms: the value, the error, the goroutine's state, and what it should have been. A condition whose answer depends on the project's intent, unstated, is a `question`.

Read each condition's exemption. Go has a correct idiom for nearly every one of these — a `_` on a write the documentation says cannot fail, a goroutine meant to live as long as `main`, a `Must` function at init — and reporting those costs the reviewer's credit.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`: the file and line, the rule and condition (`rules/errors.md` condition 2) or the `GO-` identifier, the state observed, and a correction that is an instruction.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Function length, nesting, duplication, a premature interface with one implementation (that last is the fundamentals' `rules/yagni.md`, which Go makes easy to violate): those are `reviewing-diffs` and the fundamentals' rules. In Go their detector is `revive`, configured to the fundamentals' limits as `docs/toolchain.md` shows; a finding cites the fundamentals rule, not this plugin.

**Security of the change.** Untrusted input reaching `exec.Command`, SQL built by hand, a path from a request, a secret in a log: those are the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`).

**Writing or fixing the Go.** Implementing a behaviour is `writing-go`; finding the cause of a defect is `debugging-go`. A review hands findings back; it does not edit.

**Another language.** A `.py`, `.ts` or `.rs` file in the same change is read by that language's skill.
