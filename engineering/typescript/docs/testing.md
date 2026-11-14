---
id: testing
type: doc
clade: engineering
subclade: typescript
title: Testing TypeScript
summary: What a TypeScript test suite holds and how it is run - Vitest by default and node:test where it is enough, unit tests beside the module, fakes through ports instead of module mocks, the network faked at the network, property tests for the parsers, type tests for a published surface, and type checking as a separate step.
references:
  - rules/typing.md
  - rules/runtime-validation.md
---

# Testing TypeScript

What is specific to testing in TypeScript: which runner, where tests live, how a collaborator is replaced, and the two kinds of test the language adds — tests of types, and the type check itself. Test-first as a discipline, and what a good test asserts, are language-agnostic and live in the backend clade's `driving-with-tdd` and `specifying-with-bdd`; this page gives them their TypeScript specifics.

## The runner

**Vitest by default**, for the reasons [`libraries.md`](libraries.md) gives: TypeScript and ESM without configuration, Jest's API, and type tests built in. **`node:test` for a library with no dependencies**, which keeps its test suite dependency-free too: stable since Node 20, and it matches `*.test.ts` files through type stripping "unless `--no-strip-types` is supplied" (Node's test-runner documentation).

**A test run does not type-check.** Vitest and Node both strip types and run what is left, so a test file with a type error passes. `tsc --noEmit` over the source and the tests is a separate step in the pipeline, and it is condition 1 of [`rules/typing.md`](../rules/typing.md); a suite is green only when both are.

## Where tests live, and what kinds there are

**Unit tests beside the module** they test: `order.ts`, `order.test.ts`. [`rules/colocated-tests.md`](../rules/colocated-tests.md) requires it and its hook reports a unit with no test beside it. They run in milliseconds, touch no network and no disk, and are most of the suite. A unit is tested in isolation by calling it with fakes for the ports it receives as parameters or constructor arguments ([`design.md`](design.md)).

**Integration tests under the package's `test/`**, run as a separate command because they need something running: a database in a container, a broker. They test an adapter against the real thing it adapts, which is the only test that can tell whether the SQL is right.

**Acceptance tests trace to an issue's criteria.** A test that covers a criterion names it with the `#<issue>/AC-<n>` token the contributing plugin's traceability rule reads. That is the language-agnostic convention, and it holds in a `.test.ts` file as in any other.

## Replacing a collaborator

**Through a port, with a fake.** A use case that needs to save an order receives an `OrderRepository` interface, and the test passes an in-memory implementation of it. The fake is typed by the port, so when the port changes the fake stops compiling, and the test still exercises the use case's real logic.

**Not by patching the module system.** `vi.mock("../db")` replaces a module for every importer in the test file, couples the test to the file layout, and makes a refactor that moves a file break tests that test nothing about files. It is the tool for a dependency that offers no seam — a third-party module with a top-level side effect — and a sign that a seam is missing everywhere else.

**The network, at the network.** For code whose collaborator is an HTTP API, MSW intercepts the request, so the code under test runs its real `fetch`, its real `response.ok` check and its real schema parse. A fake that replaces the client function skips exactly the lines [`async.md`](async.md) says are where the bugs live.

## Property tests for the parsers

A schema at a boundary ([`rules/runtime-validation.md`](../rules/runtime-validation.md)) and a serializer paired with it are where property tests pay most: "for any valid order, parsing what we serialized gives back the order", and "for any input, the parser either returns a valid order or a failure, and never throws". fast-check generates the inputs, shrinks a failure to its smallest case, and prints the seed that reproduces it.

## Testing types

A published package's types are part of its contract, and a change that widens a return type or loses an inference is a breaking change no runtime test sees. Vitest tests them with `expectTypeOf` and `assertType`, run with `--typecheck`: `expectTypeOf(parse(raw)).toEqualTypeOf<Order>()`. A `@ts-expect-error` line in a type test is the one place a described `@ts-expect-error` is the assertion itself — it fails the test the day the error disappears — and condition 5 of [`rules/typing.md`](../rules/typing.md) still asks for its description.

## Where this stops

**It does not cover browser end-to-end tests.** Driving a real browser through a user's flow is the frontend clade's `testing-frontend`, which names its own tools.

**It does not set a coverage threshold.** Vitest's default coverage provider is V8's, and the number it reports is an input to review; this framework's test-quality artifacts own what a coverage figure is allowed to decide.

**It does not restate test-first.** The red run before the green run, the scenario before the code: `driving-with-tdd` and `specifying-with-bdd`.

## Sources

- Vitest: guide <https://vitest.dev/guide/>; testing types (`expectTypeOf`, `--typecheck`) <https://vitest.dev/guide/testing-types>; coverage (V8 by default) <https://vitest.dev/guide/coverage>.
- Node.js test runner (stability, file patterns under type stripping): <https://nodejs.org/api/test.html>.
- MSW: <https://mswjs.io/docs/>; fast-check: <https://fast-check.dev/>.
- TypeScript, unused `@ts-expect-error` is an error: <https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-9.html>.
