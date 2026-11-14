---
name: debugging-go
description: Use when Go code misbehaves and the cause is not yet known - a panic, a test that fails only sometimes, a hang or deadlock, goroutines or memory that grow, an error that arrives as the wrong kind, a value that is wrong. Reproduces it as a failing test, turns the symptom into evidence with the toolchain's own instruments (traces, -race, goroutine dumps, pprof, the goroutine leak profile, Delve, git bisect), names the rule condition the cause breaks, and fixes it test-first.
type: skill
clade: engineering
subclade: go
references:
  - rules/errors.md
  - rules/concurrency.md
  - rules/resources.md
  - rules/nil-safety.md
  - docs/testing.md
  - docs/concurrency.md
  - docs/toolchain.md
  - skills/writing-go/SKILL.md
---

# Debugging Go

A defect is fixed when a test that failed because of it passes, and the reason it failed is understood well enough to say which condition the code broke. This skill gets there in that order: reproduce, observe, explain, fix, and look for the same defect elsewhere.

## 1. Reproduce it as a failing test

Write the smallest test that shows the symptom, in the package where it occurs, following `docs/testing.md`. Run it alone, bypassing the cache, and watch it fail the way the report describes.

```sh
go test ./internal/orders/ -run TestCancelTwice -count=1 -v
```

A symptom that appears only sometimes is reproduced by repetition: `-count=200 -race -shuffle=on`, and the seed `-shuffle` prints is kept. A symptom seen only in a running service is reproduced against that service's profile endpoints in step 2 first, then pinned in a test once the cause is known.

If it cannot be reproduced after that, stop and report what was tried; a fix for a defect nobody reproduced is a guess.

## 2. Turn the symptom into evidence

Open `references/symptoms.md` at the symptom's section — panic, intermittent test, hang, growth, slowness, wrong value, wrong error — and run the instrument it names. Each section also names the rule condition that cause usually breaks.

Read the evidence before forming a theory. A panic's trace names the line; a race report names both accesses; a goroutine dump names where every goroutine is parked. Most Go defects are explained by reading the instrument's output carefully, and guessing first is how a fix lands on the symptom.

## 3. Name the cause, and the condition it breaks

State the cause in one sentence that a reader can check against a line: "the handler returns `*ValidationError` typed nil as `error` on success, so `if err != nil` is true" — not "a nil issue". Then name the rule and condition it violates, from `rules/errors.md`, `rules/concurrency.md`, `rules/resources.md` or `rules/nil-safety.md`, or say that no rule holds it.

Confirm the cause by changing only what it names and watching the symptom go away, before writing the real fix. A change that makes the symptom go away without explaining it — a `time.Sleep`, a retry, a bigger buffer — is not a cause.

## 4. Fix it test-first

The test from step 1 is the red test. Make the smallest change that turns it green, inside the rules, by following `skills/writing-go/SKILL.md` from its step 4. Run it with the race detector even when the defect was not a race, because a fix to concurrent code can introduce one.

```sh
go test ./internal/orders/ -race -count=50 -run TestCancelTwice
```

## 5. Look for the same defect, and for why nothing caught it

Search the module for the same shape: the same misuse of the same API, the same pattern in sibling packages. Then ask why the gate did not catch it. `docs/toolchain.md` says which tool decides each condition: if the condition has a detector the project does not run — `bodyclose`, `forcetypeassert`, `errorlint`, the context hook — say so in the output, because enabling it prevents the next one. If it has no detector, say that too.

## 6. Report

Return the reproducing test, the evidence from step 2, the cause and the condition from step 3, the fix with its green run, the other occurrences found, and the detector that would have caught it.

## When this skill does not apply

**The cause is already known.** A defect whose cause is stated and pinned by a failing test is a change to write: `writing-go`.

**Performance without a defect.** Making correct code faster, with no requirement it fails, is profiling work, not debugging; `references/symptoms.md` names the profilers but this skill does not tune.

**An incident in progress.** Restoring a production service — rolling back, scaling, failing over — comes before diagnosis and is not a Go task. This skill runs once the service is stable, on what the incident left behind.

**A defect in another language.** The skill's instruments are Go's own.
