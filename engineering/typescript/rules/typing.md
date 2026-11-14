---
id: typing
type: rule
clade: engineering
subclade: typescript
title: Types the compiler holds, and the holes written past it
statement: TypeScript type-checks clean under written strict and noUncheckedIndexedAccess; an any, a @ts- directive or a double assertion carries its reason.
enforcement: judgment
references:
  - docs/toolchain.md
---

# Types the compiler holds, and the holes written past it

Seven conditions. Conditions 1 and 3 are decided by the type checker and the type-aware linter the consuming project runs. The other five are decided by `hooks/check-typing.py`, which scans the source with the standard library and needs nothing installed. [`docs/toolchain.md`](../docs/toolchain.md) argues the choice of each tool, records which version of the compiler changed which default, and gives the measurement behind every number below.

The rule is about one thing: **a place where the code tells the compiler to stop checking**. TypeScript's type system is sound only where it is allowed to run, and the language ships five ways of stopping it: turn a strict flag off, write `any`, receive `any` from an untyped library, silence a line with a `@ts-` directive, or assert a type the value does not have. Each condition below closes one of them, or makes it a written decision instead of a silent one.

## Conditions

1. **`tsc --noEmit` (or the project's `tsc --build`) reports no error.** Decided by `tsc`, run by the consuming project's pipeline. The threshold is zero, because a type error is not a quantity to stay under. This condition is why the rule is `judgment`: a hook rule is replaced by its script, and no script in this plugin can run the type system. Under TypeScript 7 the command is the same `tsc`, from the native compiler.

2. **Every tsconfig `tsc` runs from sets `strict: true` and `noUncheckedIndexedAccess: true`, and turns off no flag `strict` governs.** Decided by `hooks/check-typing.py`, which reads every `tsconfig*.json` no other tsconfig extends, follows `extends` through relative paths and installed packages, and checks the options that result. `strict` has to be written, even though it is the default from 6.0: before 6.0 the default was off, and a tsconfig that relies on the default means two different things across one upgrade. The governed flags are the eight whose default `tsc --help --all` gives as "`true`, unless `strict` is `false`", in 6.0.3 and 7.0.2 alike — `noImplicitAny`, `noImplicitThis`, `strictNullChecks`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `strictBuiltinIteratorReturn`, `useUnknownInCatchVariables` — and `alwaysStrict`, which `strict` governed until 6.0 deprecated turning it off and 7.0 refused to (errors TS5107 and TS5108). `noUncheckedIndexedAccess` is not part of `strict`, and is required here because the predecessor's typing law required it and the argument for it has not changed: without it `rows[0]` is typed as present when the array is empty, which is the most common `undefined` at runtime that a strict program still compiles.

3. **typescript-eslint's type-aware rules `no-unsafe-assignment`, `no-unsafe-member-access`, `no-unsafe-call`, `no-unsafe-return` and `no-unsafe-argument` report nothing.** Decided by typescript-eslint with typed linting on (`parserOptions.projectService`), run by the consuming project's pipeline. These five are in its `recommendedTypeChecked` configuration. They close the hole no annotation shows: an `any` that arrives by inference, from `JSON.parse`, from `Response.json()`, from an untyped dependency, and flows on into typed code. A rule may require the consuming project to adopt a tool when the condition does not exist without one, and this one does not: the compiler accepts every one of those flows by design.

4. **An explicit `any` carries a reason, in a comment on its line or the line above.** Decided by `hooks/check-typing.py`, one finding per line. A comment that is only a tool directive is not a reason, and `// eslint-disable-next-line @typescript-eslint/no-explicit-any` alone does not satisfy this; the same directive with its ` -- ` description does, because that description is what ESLint asks the author to write. `unknown` is the type for a value whose shape is not known yet, and it needs no reason, because the compiler makes the reader narrow it.

5. **No `@ts-ignore` and no `@ts-nocheck`; a `@ts-expect-error` carries a description.** Decided by `hooks/check-typing.py`. `@ts-ignore` hides the error the line has today and every error the line will ever have; `@ts-expect-error` hides one and fails the build the day it is no longer there, which is the only suppression that cleans up after itself. The description must be at least three characters, which is typescript-eslint's `ban-ts-comment` default, taken unchanged.

6. **An assertion through `unknown` or `any` — `x as unknown as T` — carries a reason.** Decided by `hooks/check-typing.py`. A single `as` is checked by the compiler against the two types, and refused when they do not overlap. The double assertion exists to get past that refusal, and nothing else. When it is right, the reason is a fact the compiler cannot see, and that fact is what the comment holds.

7. **An exported function declares its return type.** Decided by `hooks/check-typing.py` for `export function`, `export default function` and an exported `const` bound to an arrow or a function expression; a binding typed as a whole (`export const f: Handler = …`) declares it already. The inferred return of an exported function is a public contract nobody wrote: a change to the body changes what every importer compiles against, and the diff shows no signature change. A package that emits declaration files can turn on `isolatedDeclarations`, which makes `tsc` decide this condition and more of the surface, and needs `declaration` or `composite` beside it.

## Where this stops

**Conditions 1 and 3 are not decided by anything in this plugin.** The hook does not look for an ESLint configuration or a `typecheck` script, because a configuration is not a run. Where the two run is [`docs/toolchain.md`](../docs/toolchain.md)'s subject.

**Condition 3 needs typescript-eslint, and typescript-eslint needs the TypeScript 6 API.** TypeScript 7.0 ships no API, and typescript-eslint supports TypeScript `>=4.8.4 <6.1.0`. A project that compiles with 7 runs the linter against 6 installed beside it, which the TypeScript team publishes for that purpose; [`docs/toolchain.md`](../docs/toolchain.md) gives the arrangement and the alternative. The rule names the condition, not the linter's version: when typescript-eslint reads the 7 API, nothing here changes.

**A non-null assertion is not a condition.** `x!` is a cast to non-null, and it reopens a hole exactly as condition 6 describes. It is left to typescript-eslint's `no-non-null-assertion`, which is in its `strict` configuration rather than its recommended one, and to review (TS-3 of `reviewing-typescript`). A lexical scan cannot tell `x!` from the `!` of JSX text, and a detector that reports prose is worse than none.

**A single assertion is not a condition either.** `value as Order` on a value the compiler typed as a wider `Order | undefined` is a narrowing the author is vouching for. Some of those are wrong, and typescript-eslint's `no-unsafe-type-assertion` reports every one, which is why it is in none of its shared configurations except `all`. The assertions on data that enters the program untyped are decided, by condition 2 of [`runtime-validation.md`](runtime-validation.md); the rest are review.

**Condition 4 sees an `any` written in a type position.** An `any` that arrives by inference is condition 3's. JSX text is code to the scanner, so `<p>Note: any user</p>` in a `.tsx` file is reported; rewording the text or excluding the path is the answer, and neither has happened in the corpus the hook was measured on.

**Condition 4 holds a library's type-level code like any other.** Measured on four public codebases, explicit `any` is the dominant finding, and in a type-level library much of it is a constraint such as `T extends ZodType<any, any, any>`. Most of those are `unknown` waiting to be written; the rest are the reason this condition asks for a comment rather than banning the keyword.

**Condition 7 reads the four shapes of exported function above, and nothing else.** A public method of an exported class, an object of functions, and a function re-exported from a module that does not export it are typescript-eslint's `explicit-module-boundary-types`, or `isolatedDeclarations` for a package that emits declarations. A test fixture that is an exported function with no return type is a finding like any other; exclude the fixture tree by path and write down why.

**This rule does not configure anything beyond the two flags of condition 2.** `exactOptionalPropertyTypes`, `noImplicitOverride`, `noPropertyAccessFromIndexSignature` and `verbatimModuleSyntax` are each argued in [`docs/toolchain.md`](../docs/toolchain.md), and a project adopts them there. A rule that required every useful flag would be a configuration file.

**This rule is TypeScript's and does not generalise.** Conditions 4 to 6 exist because TypeScript's soundness is opt-out, line by line. A language whose compiler cannot be told to stop checking has none of them.
