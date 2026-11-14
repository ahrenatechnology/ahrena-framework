---
name: debugging-typescript
description: Use when TypeScript or the Node code built from it misbehaves - a compile error that will not go away, a value that is undefined at runtime though its type says otherwise, a promise that never settles or a rejection that kills the process, a ReferenceError at import, a module Node cannot resolve - and the cause is not yet known. Reproduces it as a failing test, classifies it by where the compiler's belief and the runtime value part, finds the hole on the value's path, and hands the fix to writing-typescript with the test that proves it.
type: skill
clade: engineering
subclade: typescript
references:
  - rules/typing.md
  - rules/promises.md
  - rules/module-boundaries.md
  - rules/runtime-validation.md
  - docs/toolchain.md
  - docs/async.md
  - skills/writing-typescript/SKILL.md
---

# Debugging TypeScript

A TypeScript defect is almost always one of two things: the compiler and the code disagree about what is written, or the compiler and the runtime disagree about what a value is. The first is a compile error, and the compiler says where. The second compiles, and the place it says nothing is exactly where to look: somewhere on the value's path, the code told the compiler to stop checking. This procedure finds that place.

`<plugin>` below is the directory where `ahrena-engineering-typescript` is installed.

## 1. Reproduce it as a failing test

Write the smallest test that shows the defect with the project's runner — the input, the call, the value or the error expected — and run it red. A defect that only happens in production gets its input from the log or the trace, and the test replays it. If it cannot be reproduced, record what was tried and stop here: a fix for a defect nobody reproduced is a guess with a commit.

Output: the red test, its command and its failure.

## 2. Classify it by its symptom

Open `references/symptoms.md` and find the symptom: a compiler error code, a runtime error name or Node error code, or a behaviour (a value `undefined` that the type says cannot be, a promise that never settles, a process that exits on a rejection). Each row names the likely cause and the first check.

Output: the class — compile, type-versus-runtime, async, or module — and the first check to run.

## 3. For a compile error, read the first one and the configuration it came from

Fix the first error `tsc` prints, not the last: later errors are often the first one's consequences. When the error is about a module or a file that should be there, the configuration is the suspect, and `tsc` explains itself:

```sh
tsc --showConfig
tsc --noEmit --traceResolution | grep "<specifier>"
tsc --noEmit --explainFiles
```

`--showConfig` prints the options after every `extends` is applied, which settles an argument about what `strict` is; `--traceResolution` shows each place a specifier was looked for; `--explainFiles` says why each file is in the program. All three exist in 6.0 and 7.0.

Output: the cause, named as an option, a path or a line.

## 4. For a value that is not what its type says, find the hole on its path

Follow the value backwards from where it is wrong to where it entered, and list every point where the compiler was told to stop checking. Two of the plugin's hooks list them mechanically over the files on the path:

```sh
python3 <plugin>/hooks/check-typing.py <files on the path>
python3 <plugin>/hooks/check-untyped-input.py <files on the path>
```

The candidates, in the order they cause this defect: data that entered untyped and was asserted (`rules/runtime-validation.md`); an `any` that flowed in from a library or a parse (`rules/typing.md`, condition 3); an `as` or a `!` that vouched for a shape; an index read that `noUncheckedIndexedAccess` would have typed as possibly `undefined`; a `@ts-ignore` above the line. Where the value entered untyped, log or assert it at the boundary in the test of step 1 and compare it with the type.

Output: the hole, as a file and line, and the value that passed through it.

## 5. For an async defect, find the promise nobody awaited

A step that runs out of order, a result that arrives after the response, an error logged from nowhere or a process that exits on an unhandled rejection: run the type-aware lint's `no-floating-promises` and `no-misused-promises` on the files involved, and `hooks/check-promises.py` where typed linting is not set up. Run the reproduction under Node with `--enable-source-maps` so the stack points at the TypeScript line. A hang is usually a call with no deadline: find the `fetch` or the client call with no `AbortSignal` (`docs/async.md`).

Output: the call that floats or hangs, as a file and line.

## 6. For a module defect, read the graph

`ReferenceError: Cannot access 'x' before initialization` at startup is an import cycle evaluated in an unlucky order; `ERR_PACKAGE_PATH_NOT_EXPORTED` is a deep import past a package's `exports`. Both are what `hooks/check-boundaries.py` reports, with the cycle written as its edges:

```sh
python3 <plugin>/hooks/check-boundaries.py <package-dir>
```

Output: the cycle's edges or the deep import, and the edge to delete.

## 7. Hand the fix over with the test

Write the fix with `writing-typescript`, from its step 4, with the red test of step 1 as its test: the fix is the code that turns it green, and the test stays as the regression test. When the cause was a hole, the fix closes the hole — a schema in place of the assertion, a narrowing in place of the `!` — rather than adjusting the value after it; a fix that patches the symptom leaves the hole for the next value.

Output: the green run, and the hole closed.

## When this skill does not apply

**A defect in another language** of the same change: that language's skill.

**A defect whose cause is already known.** Go straight to `writing-typescript`.

**A performance problem.** A slow build is the compiler's `--extendedDiagnostics` and `--generateTrace`, and moving to TypeScript 7 ([`docs/toolchain.md`](../../docs/toolchain.md)); a slow program is a profiler's question, not a typing one.

**A rendering or state defect in a user interface.** The frontend clade's skills own components and state; this skill still applies to the TypeScript underneath them.
