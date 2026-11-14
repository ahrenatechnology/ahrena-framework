---
id: colocated-tests
type: rule
clade: engineering
subclade: typescript
title: A unit's test sits beside it
statement: A TypeScript file that holds a function or class has its foo.test.ts beside it, and a test beside nothing is deleted or moved with its unit.
enforcement: hook
enforced-by: hooks/check-tests.py
references:
  - docs/testing.md
---

# A unit's test sits beside it

A reader who opens `order.ts` finds `order.test.ts` in the same folder, and the reverse. The test checks that unit's characteristics and behaviour; a test that exercises several units together lives where [`docs/testing.md`](../docs/testing.md) puts it, under the package's `test/` directory, and is not what this rule is about.

Both conditions are decided by `hooks/check-tests.py`, which reads the tree with the standard library. The rule is the owner's directive for every language plugin (item 9 of the directive on #285). TypeScript has no convention of its own to defer to: the test runners find a test anywhere, and Vitest's default `include` and Node's test runner both match `*.test.ts` wherever it sits, so the placement is a choice, and this rule makes it.

## What a unit is

A unit is a TypeScript source file — `.ts`, `.tsx`, `.mts`, `.cts` — whose code, with comments, strings, interfaces and type aliases set aside, still declares a function, an arrow function or a class. A module of types, of constants, or of re-exports holds no behaviour and owes no test. The premise is maintainability: a file that solves one problem (the single-responsibility limit of [`docs/design.md`](../docs/design.md)) has one test file, and the two are read, changed and deleted together.

## Conditions

Each of these is decided by `hooks/check-tests.py`.

1. **A file that holds a unit has a test file beside it**: same directory, same stem, `.test.` or `.spec.` before a TypeScript extension. `order.ts` is tested by `order.test.ts`; `Button.tsx` by `Button.test.tsx` or `Button.spec.tsx`. A test for the same unit in another folder does not count, because a reader who opens the unit does not find it.

2. **A test file in a source directory has its unit beside it.** `order.test.ts` with no `order.ts` beside it tests something that moved or was renamed, or several units under one name; it moves with its unit, takes the unit's name, or moves to `test/` as the multi-unit test it is.

## Where this stops

**Declaration files, configuration files and test support are not units.** `*.d.ts`, `*.config.ts`, and anything under a directory named `test`, `tests`, `__tests__`, `__mocks__`, `__fixtures__`, `fixtures`, `mocks` or `e2e` is skipped. A test under one of those directories is a multi-unit test and is neither required nor checked against a sibling.

**JavaScript files are not read.** A `.js` file in a TypeScript project is usually configuration or a build script; a JavaScript codebase that wants this rule adopts it with the extensions added.

**A composition root is a unit like any other.** `main.ts` declares the function that assembles the program; its test starts the program against fakes and stops it. A project that tests its composition root only end to end leaves it out of the hook's paths and writes down why.

**A generated file is not the project's unit.** Leave the generated directory out of the paths the hook is given, as [`docs/project-layout.md`](../docs/project-layout.md) says.

**The condition reads presence, not quality.** A `foo.test.ts` that asserts nothing passes condition 1. Whether the test checks the unit's behaviour is the review's, and the language-agnostic test-quality artifacts', not this hook's.

**Measured on four public codebases** — zod, hono, typescript-eslint and vscode-extension-samples, at the commits [`docs/toolchain.md`](../docs/toolchain.md) records — the hook reported 980 units with no test beside them and 19 tests beside no unit. None of the four places tests this way: zod and typescript-eslint keep tests in `tests/` directories, and hono names a test for the module it tests through, so `hono-base.ts` is covered by `hono.test.ts`. That is the measure of how far this rule is from common practice, which it departs from on purpose, under the owner's directive: a convention that a hook can hold is one a reader can rely on, and none of the four lets a reader find a unit's test from the unit.

## Sources

- The owner's directive, item 9: issue #285 of this repository, section "Directive from the owner (2026-11-14)".
- Vitest's default test `include` pattern: <https://vitest.dev/config/include>.
- Node's test runner file patterns, including `**/*.test.{cts,mts,ts}` under type stripping: <https://nodejs.org/api/test.html#running-tests-from-the-command-line>.
