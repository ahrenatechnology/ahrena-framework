---
name: reviewing-typescript
description: Use when a change under review edits TypeScript or JavaScript (.ts, .tsx, .js, .jsx and their module variants) and the question is what a TypeScript reader would catch - an any or a cast that reopens a hole the compiler would have closed, a floating or unhandled promise, an import cycle or a deep import, untyped input given a type by assertion, a unit with no test beside it, a whole object or upstream error written to a log or a response, a pattern from another language against TypeScript's grain, == where === was meant, a widened public type. Runs this plugin's hooks, reads the routed files against its rules and the conditions below; every finding names the rule condition or the TS condition.
type: skill
clade: engineering
subclade: quality
references:
  - rules/typing.md
  - rules/promises.md
  - rules/module-boundaries.md
  - rules/runtime-validation.md
  - rules/colocated-tests.md
  - docs/design.md
  - docs/sensitive-data.md
  - docs/error-handling.md
  - docs/async.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing TypeScript

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold in any language. This skill reads what needs a TypeScript reader. It works in two passes: the five rules of this plugin first, decided where a script can decide them; then the conditions in `references/`, which are what is left for a reader.

A finding cites a rule condition (`rules/typing.md`, condition 4) or a checklist identifier (`TS-12`). A checklist condition that a rule already decides says so and points at it, and is reported under the rule. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

`<plugin>` below is the directory where `ahrena-engineering-typescript` is installed; in this framework's repository it is `engineering/typescript`.

## 1. Take the route, and read the repository first

The router fired the `typescript` route on the changed `.ts`, `.tsx`, `.js` and `.jsx` files (and the `.mts`/`.cts`/`.mjs`/`.cjs` variants). Those are the files this skill reads.

Read the project's `tsconfig.json` and its lint configuration first. They decide which conditions a tool has already settled: under typed linting with `recommendedTypeChecked`, condition 3 of `rules/typing.md` and condition 1 of `rules/promises.md` are decided by the pipeline, and a green lint is the answer; without it, those conditions are read by hand on the changed lines. What a green `tsc` and a green lint decided is not reported again.

## 2. Run the rules' hooks over the change

Run the hooks over the changed files, and `check-boundaries.py` over the package that holds them, because a cycle is a property of the graph and not of one file:

```sh
python3 <plugin>/hooks/check-typing.py <changed files>
python3 <plugin>/hooks/check-promises.py <changed files>
python3 <plugin>/hooks/check-untyped-input.py <changed files>
python3 <plugin>/hooks/check-tests.py <changed files>
python3 <plugin>/hooks/check-boundaries.py <package-dir>
```

Compare with the same run at the base revision. A finding the change adds is reported, under the rule and condition the hook names; a finding already on the base is not this change's, unless the change touched that line.

## 3. Read the rules' judgment conditions

The hooks decide most of the rules, not all. Read the changed lines against what is left: condition 1 of `rules/runtime-validation.md` (every boundary the change adds parses what enters it), its condition 3 (the type derived from the schema) and its condition 4 (a failed parse is a failure the caller sees); and, where the project has no typed linting, condition 3 of `rules/typing.md` and condition 1 of `rules/promises.md`.

## 4. Open the checklists the change calls for

| What the change touches | Reference |
|---|---|
| a type, an interface, a cast, a generic, a signature | `references/types.md` |
| a promise, `async`/`await`, an event handler, equality, a number, a `catch` | `references/correctness-and-async.md` |
| an export, a barrel, a public declaration, a `.d.ts` | `references/modules-and-surface.md` |
| a log, a response, an error message, a trace, a serializer, a type that holds a secret; a class, a port, a constructor | `references/exposure-and-design.md` |

A change to a component's internals that adds no type and no async opens `correctness-and-async.md` alone. Every change that writes to a log, a response or an error opens `exposure-and-design.md` as well.

## 5. Read beyond the hunk

Follow each changed symbol to its callers and to the types it flows into. A cast is judged by what the value actually is at runtime, which the surrounding code shows, not by the hunk. An exported type is judged by who imports it.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 6. Apply the routed conditions

Work condition by condition. Give the scenario in TypeScript terms: the value at runtime, the type the compiler believed, and where they part. A condition whose answer is a project convention the repository does not state is a `question`.

Read each condition's `Exempt` line. A cast at a true boundary and an `any` on genuinely dynamic data with its reason written are correct, and reporting them teaches the author to skim.

## 7. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the rule condition or the TS identifier, and a correction that is an instruction.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`; run standalone, outside `reviewing-diffs`, return it to the caller. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Length, nesting, duplication, a premature abstraction: those are `reviewing-diffs` and the fundamentals rules.

**The experience of a React or browser UI.** Accessibility, component and state architecture, rendering performance and design-system use are the frontend clade's, in `ahrena-engineering-frontend`. This skill stays inside the type system, async, the module graph and the data that enters the program.

**Security of the change.** XSS through `dangerouslySetInnerHTML`, a URL built from input, a secret in a bundle: that is the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`), whose conditions carry those sinks. `rules/runtime-validation.md` asks that untrusted input be parsed; what an attacker can make a sink do is theirs.

**Another language.** A `.py`, `.go` or `.rs` file in the same change is read by that language's skill.
