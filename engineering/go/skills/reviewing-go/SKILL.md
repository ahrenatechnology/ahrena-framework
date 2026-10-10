---
name: reviewing-go
description: Use when a change under review edits Go (.go) and the question is what a Go reader would catch - an error ignored or wrapped so callers can no longer match it, a goroutine or context that leaks, a nil interface that is not nil, a loop variable captured, a defer that never runs. Reads the routed files against the conditions below; every finding names the condition.
type: skill
clade: engineering
subclade: quality
references:
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Go

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold in any language. This skill reads what needs a Go reader: errors, concurrency, and the handful of traps the compiler and `go vet` do not all catch.

The conditions are checklists in `references/`, identified by a prefix and a number. A finding cites the identifier. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `go` route on the changed `.go` files. Those are the files this skill reads.

Read the project's Go version from `go.mod` first: it decides real conditions — before 1.22 each loop iteration shared one variable, and the error-wrapping verbs and `errors.Join` arrived over several versions. Read `AGENTS.md` and whether the project runs `go vet`, `staticcheck` or `golangci-lint` in CI: a check those already decide — an unchecked error that `errcheck` flags, a lost `Context` that `contextcheck` flags — is settled and not reported again.

## 2. Open the checklists the change calls for

| What the change touches | Reference |
|---|---|
| a returned `error`, an `error` value, a `panic`/`recover`, a deferred close | `references/errors.md` |
| a `go` statement, a channel, a `sync` primitive, a `context.Context`, a shared variable | `references/concurrency.md` |
| an interface, a `nil` comparison, a `defer`, an exported identifier, a slice or map aliased | `references/idioms-and-surface.md` |

A change that only edits a pure function's arithmetic opens none of these; say the Go pass found nothing specific.

## 3. Read beyond the hunk

Follow each changed function to its callers and to what it returns. Whether a returned error is checked is decided at the call site, not the `return`. Whether a goroutine leaks is decided where the function that starts it returns. Read the base revision of a line before calling it wrong.

## 4. Apply the routed conditions

Work condition by condition. Give the scenario in Go terms: the value, the error, the goroutine state, and what it should have been. A condition whose answer depends on the project's intent, unstated, is a `question`.

Read each condition's `Exempt` line. Go has a correct idiom for nearly every one of these — a deliberately ignored error, a goroutine the program is meant to outlive — and reporting those costs the reviewer's credit.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the condition identifier and a correction that is an instruction.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Function length, nesting, duplication, a premature interface with one implementation (that last is `rules/yagni.md` in the fundamentals, which Go makes easy to violate): those are `reviewing-diffs`.

**Security of the change.** Untrusted input reaching `exec.Command`, SQL built by hand, a path from a request: that is the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`).

**Another language.** A `.py`, `.ts` or `.rs` file in the same change is read by that language's skill.
