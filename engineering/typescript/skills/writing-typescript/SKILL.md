---
name: writing-typescript
description: Use before writing or changing TypeScript (.ts, .tsx, .mts, .cts) - a feature, a fix, a layer of a build - so the code is written test-first against this plugin's rules and docs rather than corrected by review afterwards. Reads the project's compiler and lint setup, places the change in the package and layer it belongs to, extending through a new package rather than editing a base, writes the unit's test red beside it, writes the code to the typing, promises, boundary, validation and single-responsibility limits with nothing sensitive leaving it, and runs the same gate review will run.
type: skill
clade: engineering
subclade: typescript
references:
  - rules/typing.md
  - rules/promises.md
  - rules/module-boundaries.md
  - rules/runtime-validation.md
  - rules/colocated-tests.md
  - docs/design.md
  - docs/sensitive-data.md
  - docs/toolchain.md
  - docs/project-layout.md
  - docs/libraries.md
  - docs/error-handling.md
  - docs/async.md
  - docs/testing.md
  - skills/reviewing-typescript/SKILL.md
---

# Writing TypeScript

The discipline of writing test-first is language-agnostic and belongs to `ahrena-engineering-backend:driving-with-tdd`. This skill gives it the TypeScript specifics: which of the five rules the project's own tools already decide, where the change goes, how its test replaces a collaborator, and how the code is written so that `reviewing-typescript` has nothing to report.

`<plugin>` below is the directory where `ahrena-engineering-typescript` is installed; in this framework's repository it is `engineering/typescript`.

## 1. Read what the project already decides

Open the project's `tsconfig*.json`, its ESLint or Oxlint configuration and its `package.json` scripts. Record four facts: whether `strict` and `noUncheckedIndexedAccess` are written (condition 2 of `rules/typing.md`); whether typed linting is on, with which shared configuration; which command type-checks; and which runner runs the tests. Then run the five hooks over the package directory you are about to change, so that findings already on trunk are known before you add any; record too whether the lint configuration sets `max-statements`, `max-depth` and `max-params` to the fundamentals' numbers (step 4):

```sh
python3 <plugin>/hooks/check-typing.py <package-dir>
python3 <plugin>/hooks/check-promises.py <package-dir>
python3 <plugin>/hooks/check-boundaries.py <package-dir>
python3 <plugin>/hooks/check-untyped-input.py <package-dir>
python3 <plugin>/hooks/check-tests.py <package-dir>
```

Output: the four facts and the baseline findings. A hook that exits non-zero on the baseline is not a stop: from here on, compare findings, not exit codes. A finding on trunk is not yours to fix in this change unless the change touches that line; it is a finding to report, not a reason to stop.

The failure that recurs here is writing to a stricter or looser setup than the project has. A project without typed linting does not decide condition 3 of `rules/typing.md` or condition 1 of `rules/promises.md`, and you hold those by hand for the code you write.

## 2. Place the change

Choose the path by the premises of `docs/design.md`, in order — no circular reference, lower cyclomatic complexity, maintainability — and write down the one that decided. Then name the package and the layer the change lives in, per `docs/project-layout.md`: which package's `exports` it adds to, if any; which layer of which context (`domain`, `application`, `infrastructure`); and every import it adds across a package boundary, which goes through the other package's name and an exported entry (`rules/module-boundaries.md`). If the change adds behaviour to a package it does not own, it goes in a new workspace package that depends on the base and extends it through the base's public extension points (`docs/design.md`); a base with no extension point for it gets one as its own change first. A collaborator the code needs is a port declared beside the code that needs it, as a structural interface, and arrives as a parameter or a constructor argument. If the change adds a boundary — a route, a consumer, a read of `process.env`, a call to another service — name it now, because it needs a schema (`rules/runtime-validation.md`) and the schema comes before the code that trusts it.

Output: the files the change will touch, and its boundaries. A project with a component map names its own folders; read it with `ahrena-engineering-fundamentals:reading-the-component-map` first when it has one.

## 3. Write the test red

Write the test for the behaviour before the code, with the project's runner, per `docs/testing.md`: `foo.test.ts` beside `foo.ts`, as `rules/colocated-tests.md` requires; collaborators replaced through their port with a typed fake, never with `vi.mock` on a module that has a seam; an HTTP collaborator faked at the network with MSW; a parser covered by a property test with fast-check. A test that covers an acceptance criterion carries its `#<issue>/AC-<n>` token. Run it and confirm it fails for the missing behaviour, not for a type error or a missing import: for a function that does not exist yet, export a stub with the final signature that returns a wrong value or throws, so the test runs and fails on its assertion.

Output: the red run, its command and the failing test names.

## 4. Write the code to the rules

Write the smallest code that turns the test green, and write it to the five rules as you go rather than after:

- **Types** (`rules/typing.md`). No `any`: `unknown` and a narrowing where the shape is not known yet. An exported function declares its return type. No `@ts-ignore`; a `@ts-expect-error` says which error. No `as unknown as`; when the compiler refuses a single `as` with TS2352, the types disagree and the code is wrong more often than the compiler.
- **Boundaries** (`rules/runtime-validation.md`). Every value from step 2's boundaries is parsed by a schema, its type is derived from the schema (`z.infer`, `v.InferOutput`, or checked against it with `satisfies`), and a failed parse is a failure the caller sees — a 400, a stopped process, a dead letter.
- **Size** (`docs/design.md`). Each function and method stays inside the fundamentals' limits from its first line: at most 30 statements (`ahrena-engineering-fundamentals:rules/clean-code.md`, condition 1), control flow nested at most 3 deep (`rules/kiss.md`, condition 1), at most 4 parameters (`rules/value-semantics.md`, condition 1), no branch on a boolean parameter (`rules/kiss.md`, condition 2), and a class whose methods share its state (`rules/solid.md`, condition 1). Each file solves one problem and exports what that problem needs. In TypeScript ESLint's `max-statements`, `max-depth` and typescript-eslint's `max-params` report a breach when the project sets them to those numbers; where it does not, count by hand, and say so in step 5.
- **Exposure** (`docs/sensitive-data.md`, issue #294). What the code emits — a response, a log line, a trace attribute, an error message — is a list of named fields, never a whole object, configuration, error or upstream response; a value that carries a secret is wrapped in a type whose `toJSON` and inspect method redact it; an upstream error is translated at the adapter, with the original in `cause`, before it crosses a boundary; and a secret is never read in a module the client bundle imports.
- **Async** (`rules/promises.md`, `docs/async.md`). `await` by default; `Promise.all` or `allSettled` chosen by what the tasks are; a `fetch` carries `AbortSignal.timeout` and its `response.ok` is checked; no async callback to `forEach`; a fire-and-forget is `void` with its own `.catch`.
- **Failures** (`docs/error-handling.md`). A failure the caller must decide is returned as a discriminated union; one nobody can handle here is thrown as an `Error` with `cause`; a `catch` narrows `unknown` before reading it and is never empty without a comment that says why.
- **Modules** (`rules/module-boundaries.md`). Relative imports inside the package, the package's name across; `import type` for a name used only as a type; no work at a module's top level.
- **Libraries** (`docs/libraries.md`). Before adding a dependency, check the entry for the problem; a dependency the doc says is not needed is not added.

Then refactor under green. Output: the green run, its command and the counts.

## 5. Run the gate review will run

Run the project's type check, its lint and its tests, then the five hooks of step 1 over the paths you changed, and compare with the baseline. Every new finding is fixed before the change is handed on, or carries the reason the rule asks for.

Output: each command with its result, and the hook findings the change added (none, or each with its reason).

## 6. Read your own diff as a reviewer

Invoke `ahrena-engineering-typescript:reviewing-typescript` with the Skill tool and read the diff against its conditions, correct what it finds, and run step 5 again. This is the check, not the review: the review of the change is still somebody else's.

Output: a diff that meets the conditions, still green.

## When this skill does not apply

**Diagnosing a defect in existing TypeScript.** Finding why something fails is `debugging-typescript`; this skill starts once the cause is known and the fix is being written.

**Reviewing someone else's change.** That is `reviewing-typescript`, from the review route.

**The frontend clade's own layers.** Components, state, the wireframe and the contract of a user-facing feature are built by `ahrena-engineering-frontend`'s agents and skills; they write TypeScript and load this skill for the language, not for the design.

**JavaScript with no TypeScript.** A `.js` file in a project that does not type-check it gets the async, boundary and module conditions and nothing from `rules/typing.md`.
