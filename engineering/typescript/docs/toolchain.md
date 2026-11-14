---
id: toolchain
type: doc
clade: engineering
subclade: typescript
title: The TypeScript toolchain, argued
summary: Which compiler, which flags beyond the two typing.md requires, which linter and how it runs beside TypeScript 7, how TypeScript is run and built, and the measurement behind every number in this plugin's rules.
references:
  - rules/typing.md
  - rules/promises.md
---

# The TypeScript toolchain, argued

This is the companion to [`rules/typing.md`](../rules/typing.md) and [`rules/promises.md`](../rules/promises.md). The rules state what must hold; this explains which tool decides each part, why that tool and not its neighbour, and where the numbers came from. It names versions because the toolchain moved under this plugin while it was being written, and a reader needs to know which world each sentence describes. The state described is November 2026: TypeScript 7.0.2, TypeScript 6.0.3, typescript-eslint 8.72, Node.js 26 with 24 and 22 still in LTS.

It is not a configuration file, and it does not paste one. A `tsconfig.json` copied from a document is a set of opinions nobody can trace; every flag below is argued, and the project writes its own file.

## The compiler: 7 to build, 6 for tools

TypeScript 7 is the native port of the compiler, and its announcement measures "speedups between 8x and 12x on full builds". It is the `tsc` this plugin assumes, and condition 1 of `typing.md` is the same command under 7 as under 6.

**7.0 ships no API.** Its announcement says so directly, and expects a new and different one in 7.1. Everything that imports `typescript` as a library — typescript-eslint above all, but also Volar-based editors for Vue, Astro and Svelte — still needs 6. The TypeScript team publishes `@typescript/typescript6` for this: the 6.0 API under its own name, with an executable called `tsc6`, installed beside 7 through an npm alias so that a tool asking for `typescript` receives 6 while the build runs 7. The arrangement is a stopgap with an end date, and this plugin's rules are written so that nothing in them changes when it ends.

**6.0 is the version that moved the defaults**, and it is why condition 2 of `typing.md` asks for `strict` to be written. Its release notes list `strict` defaulting to `true`, `module` to `esnext`, `target` to the current year's edition, `noUncheckedSideEffectImports` to `true` and `types` to `[]`. They deprecate `baseUrl`, `moduleResolution: node10`, `target: es5`, and turning `esModuleInterop` off; they remove `moduleResolution: classic` and `outFile`. 7.0 turns every 6.0 deprecation into an error, which this plugin observed directly: `alwaysStrict: false` is error TS5107 under 6.0.3 and TS5108 under 7.0.2.

## The flags, one by one

`typing.md` requires two and argues them there: `strict`, written, and `noUncheckedIndexedAccess`. The rest are a project's choice, and this is the argument for each.

| Flag | Recommendation | Why |
|---|---|---|
| `verbatimModuleSyntax` | on | What is written is what runs: an import without `type` is kept, one with `type` is dropped. It is what makes a type-only import visible in the source, which `module-boundaries.md` relies on, and Node's type stripping behaves the same way. |
| `erasableSyntaxOnly` | on, for code Node runs directly | Added in 5.8. It refuses `enum`, namespaces with runtime code, parameter properties and `<T>` assertions — the syntax Node's type stripping cannot erase. A project that never runs through Node's stripping may leave it off; nothing else is lost by turning it on. |
| `isolatedDeclarations` | on, for a published library | It makes `tsc` refuse an export whose type must be inferred, so declaration files can be generated without the checker. It needs `declaration` or `composite` (error TS5069 otherwise), so it does not belong in an application. |
| `exactOptionalPropertyTypes` | on in new code, not retrofitted | `x?: string` stops accepting an explicit `undefined`. It catches real bugs where absence and `undefined` mean different things, and it fights libraries whose types were written without it; retrofitting it onto a large codebase is a project of its own. |
| `noImplicitOverride` | on | A method that overrides must say `override`, so renaming the base method breaks the build instead of silently orphaning the subclass. |
| `noFallthroughCasesInSwitch`, `noImplicitReturns` | on | Each closes one control-flow mistake at no cost to correct code. |
| `noPropertyAccessFromIndexSignature` | off | It forces `obj["key"]` over `obj.key` for index signatures. That is a spelling rule, and `noUncheckedIndexedAccess` already makes the access honest. |

`module` and `moduleResolution` are chosen by what the code is, and [`project-layout.md`](project-layout.md) carries that choice, quoting TypeScript's own guide.

## The linter: typescript-eslint, typed

Conditions 3 of `typing.md` and 1 of `promises.md` need a linter that knows types, and typescript-eslint is the one this plugin names. Its `recommendedTypeChecked` configuration holds every rule those conditions cite, and typed linting is turned on with `parserOptions.projectService: true`, which its documentation calls "our recommended option". The cost is stated by the same page: typed linting incurs "the performance penalty of asking TypeScript to do a build of your project", negligible on a small project and noticeable on a large one, which is why it runs in the pipeline and not on every keystroke.

Its supported range is TypeScript `>=4.8.4 <6.1.0`, and a maintainer wrote on its tracker (typescript-eslint issue #12518, with the work tracked in #10940) that it "isn't compatible with TS 7 at this time, because there is no TS 7 API". Under 7 it runs against `@typescript/typescript6`, as above.

**The alternative, and when to take it.** Oxlint's type-aware linting went stable in July 2026 on tsgolint, "built directly on TypeScript v7", so it needs no second compiler. A project that wants one TypeScript in its tree can use it; its rules carry typescript-eslint's names under a `typescript/` prefix (`typescript/no-floating-promises` in oxlint 1.93's configuration schema), and a rule this plugin cites by its typescript-eslint name is the same condition there. Biome 2 implements type-aware rules without the compiler, and its own announcement measures its `noFloatingPromises` at about 75% of what typescript-eslint catches; that is a fine formatter-and-lint tool and a weaker detector for condition 1 of `promises.md`, so this plugin does not count it as deciding that condition.

**Formatting is not a condition anywhere in this plugin.** Prettier or Biome, run and accepted; a style argued in review is time spent on nothing.

## Running and building

**Node runs TypeScript itself.** Type stripping has been on by default since v23.6 and v22.18, and stable since v25.2 and v24.12. It erases types and does nothing else: it ignores `tsconfig.json`, refuses syntax that needs transforming (enums, namespaces with runtime code, parameter properties), needs `import type` to drop a type import, and does not handle `.tsx`. Node 26 removed `--experimental-transform-types`, so there is no flag that widens it. A service that holds to `erasableSyntaxOnly` can run `node src/main.ts` in development and in production, and type-checks separately with `tsc --noEmit`. Where it cannot — `.tsx` on the server, a path alias, a decorator-heavy framework — tsx runs it instead.

**A library is built by `tsc`, or by tsdown when it must be bundled.** `tsc` emits JavaScript and declarations with nothing in between. When a library ships a bundle or several formats, tsdown is the tool; tsup, which held that place, now says on its own repository that it "is not actively maintained anymore" and points to tsdown. A published package is checked by `publint` and `@arethetypeswrong/cli`, which read the built package the way consumers' tools will.

**An application is built by its framework or its bundler**, which type-strips and does not type-check. That is why `tsc --noEmit` runs beside the build and is condition 1 of `typing.md`: a green bundle is not a typed program.

## Where every number came from

**Inherited.** `noUncheckedIndexedAccess` comes from the predecessor's typing law, which required it with `strict`. The three-character minimum for a `@ts-expect-error` description is typescript-eslint's `ban-ts-comment` default. The list of flags `strict` governs is `tsc --help --all` for 6.0.3 and 7.0.2, read on 2026-11-14.

**Measured.** The four hooks were run on four public codebases, shallow clones read on 2026-11-14:

| Codebase | Commit | Lines of TypeScript |
|---|---|---|
| `colinhacks/zod` | `fef16cb` | 103,558 |
| `honojs/hono` | `f6fbaf0` | 95,158 |
| `typescript-eslint/typescript-eslint` | `2838b49` | about 365,000 |
| `microsoft/vscode-extension-samples` | `65c1c44` | 16,094 |

No hook took more than four seconds on any of them. The findings, by rule and condition:

| Hook | zod | hono | typescript-eslint | samples |
|---|---|---|---|---|
| typing 2 (tsconfig) | 17 | 26 | 115 | 92 |
| typing 4 (`any`, per line) | 1,122 | 386 | 137 | 40 |
| typing 5 (`@ts-` directive) | 155 | 71 | 3 | 0 |
| typing 6 (double assertion) | 107 | 55 | 36 | 0 |
| typing 7 (exported return) | 71 | 37 | 18 | 98 |
| promises 2 / 3 | 0 / 32 | 0 / 21 | 0 / 6 | 2 / 0 |
| boundaries 1 / 3 | 1 / 6 | 4 / 1 | 2 / 16 | 3 / 2 |
| runtime-validation 2 | 6 | 1 | 6 | 3 |

Each condition's findings were sampled and read against the source. Two detector defects were found that way and fixed before the numbers above were taken: a line with three `any` counted three times, and a process listener passed by reference was read as one that swallows. One known false positive remains, described in [`rules/runtime-validation.md`](../rules/runtime-validation.md). The volumes are what they are: these are mature, careful codebases, and the rules would ask each of them to write down a reason a few hundred times. That is the measure of how much of their type safety rests on decisions nobody wrote down, not a sign the threshold is wrong — none of the conditions has a threshold to move.

## Where this stops

**This document names versions, and they will be wrong.** Each one is dated above. When typescript-eslint reads the 7 API, the `@typescript/typescript6` arrangement goes, and nothing in the rules changes, because they cite rules by name and conditions by state.

**It does not choose a framework.** Next.js, Remix, Nest, Angular and Vue each bring a build and a tsconfig of their own; the flags above layer on top of them, and the frontend clade's artifacts in `ahrena-engineering-frontend` own the framework.

**It does not cover editors.** The language service is whatever the editor runs, and under 7 that is the native one, except for the Volar-based frameworks the 7.0 announcement says still need 6.

## Sources

- TypeScript 6.0 announcement: <https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/>.
- TypeScript 7.0 announcement (8x to 12x full builds, no API in 7.0, `@typescript/typescript6` through npm aliases, Volar-based editors): <https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/>.
- tsconfig reference, each flag above: <https://www.typescriptlang.org/tsconfig/>; `erasableSyntaxOnly`, TypeScript 5.8 release notes: <https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-8.html>.
- typescript-eslint: supported versions <https://typescript-eslint.io/users/dependency-versions/>; typed linting and its cost <https://typescript-eslint.io/getting-started/typed-linting/>; issue #12518 <https://github.com/typescript-eslint/typescript-eslint/issues/12518> and #10940 <https://github.com/typescript-eslint/typescript-eslint/issues/10940>.
- Oxlint, type-aware linting stable on tsgolint: <https://oxc.rs/blog/2026-07-22-type-aware-linting-stable>; rule names read from oxlint 1.93's `configuration_schema.json`.
- Biome 2 announcement (`noFloatingPromises` about 75%): <https://biomejs.dev/blog/biome-v2/>.
- Node.js, type stripping (history, limits, removal of `--experimental-transform-types` in v26): <https://nodejs.org/api/typescript.html>.
- tsup, "not actively maintained anymore": <https://github.com/egoist/tsup>; tsdown: <https://tsdown.dev/guide/>; publint: <https://publint.dev/docs/>; Are the Types Wrong: <https://github.com/arethetypeswrong/arethetypeswrong.github.io>.
- The four measured codebases, at the commits in the table: <https://github.com/colinhacks/zod>, <https://github.com/honojs/hono>, <https://github.com/typescript-eslint/typescript-eslint>, <https://github.com/microsoft/vscode-extension-samples>.
