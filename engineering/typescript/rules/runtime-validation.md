---
id: runtime-validation
type: rule
clade: engineering
subclade: typescript
title: Data that enters untyped is parsed before it is typed
statement: Data entering untyped (a body, JSON.parse, an env var, a message) is parsed by a schema before it is typed, and is never given a type by assertion.
enforcement: judgment
references:
  - docs/libraries.md
  - docs/error-handling.md
---

# Data that enters untyped is parsed before it is typed

TypeScript's types are erased before the program runs. Inside the program they are true because the compiler checked every assignment; at the edge, where bytes become values, nothing checked anything, and a type there is a claim about data nobody has looked at. This rule puts a parse at every such edge, so that the type on the inner side is a consequence of a check that ran, not an assumption.

Condition 2 is decided by `hooks/check-untyped-input.py`. Conditions 1, 3 and 4 need a reader, because what counts as a boundary depends on the program. [`docs/libraries.md`](../docs/libraries.md) names the schema library and argues the choice; [`docs/error-handling.md`](../docs/error-handling.md) says what a failed parse becomes.

## What a boundary is

A boundary is any point where a value enters the program without a type the compiler checked: an HTTP request body, query or header; a response from another service; `JSON.parse`; `process.env`; a queue or stream message; a row from a database whose driver returns untyped rows; `localStorage`, `sessionStorage`, a cookie or a URL parameter in a browser; a `postMessage` event; a file read from disk; a webhook payload. The standard library marks several of them itself. `JSON.parse` builds whatever value the text describes (ECMA-262 §25.5.2), so TypeScript's `lib.es5.d.ts` declares it to return `any`; `Body.json()` returns `Promise<any>` in `lib.dom.d.ts`; and `process.env` is a record of `string | undefined` in `@types/node`.

## Conditions

1. **A value that crosses a boundary is parsed by a schema before code reads it as a typed value.** Decided by review. The parse returns either the typed value or a failure, and the code on the inner side only ever sees the first. A schema is a runtime object — Zod, Valibot, a JSON Schema compiled by Ajv, a framework's own validator such as Fastify's — never an interface, because an interface does not exist at runtime. Where the platform already validates, the condition is met there: a Fastify route with a request schema parses before the handler runs, and the handler need not parse again.

2. **A value that enters untyped is not given a type by assertion.** Decided by `hooks/check-untyped-input.py`, on `JSON.parse(…) as T`, `<T>JSON.parse(…)`, a `.json()` body asserted to a type or to a typed promise, and `process.env.NAME as T`, through any parentheses between the call and the `as`. Asserting to `unknown` is allowed, because it is the honest first step: it makes the compiler require a narrowing before use. The same flows written as an assignment — `const order: Order = JSON.parse(raw)` — are an `any` assigned to a typed binding, and condition 3 of [`typing.md`](typing.md) decides them through typescript-eslint's `no-unsafe-assignment`.

3. **The type of a parsed value is derived from its schema, or checked against it.** Decided by review. `type Order = z.infer<typeof Order>`, `v.InferOutput<typeof Order>`, or a hand-written type the schema is checked against with `satisfies`, so the two cannot drift; never an interface and a schema written side by side and trusted to agree. Types generated from an OpenAPI or GraphQL document are a contract, not a parse: they describe what the other side promised, and the response is still parsed against a schema derived from the same document before it is trusted.

4. **A failed parse is a failure the caller sees, not a default.** Decided by review. A request whose body does not parse is answered with a 400 that says which field; a configuration that does not parse stops the process at startup with every missing variable named; a message that does not parse goes to a dead-letter queue. Catching the parse error and continuing with a fallback value is the empty handler of condition 3 of [`promises.md`](promises.md) with a type on it.

## Where this stops

**A first-party value is not a boundary.** Data produced by this program's own typed code, read back in the same process, was checked when it was produced. A call between two modules of one service is not a boundary; a call between two services is one, even when both are this team's, because they deploy apart and the types of one say nothing about the version of the other that is running. An end-to-end typed RPC whose server parses its input (tRPC, Hono's typed client) has its boundary at the server, and its client output is typed by inference from a server it is deployed with; the condition then asks whether they really are deployed together.

**Condition 2 reads three entries and the assertion written directly after them.** `const raw = JSON.parse(text); return raw as Order;` is condition 3 of [`typing.md`](typing.md) through `no-unsafe-return`, or a finding at review. `ky`'s `.json<T>()` and other generic fetch helpers that type the body by a type argument are the same assertion in a different syntax and are not read, because the hook cannot tell them from a helper that validates. `foo(JSON.parse(x)) as T` is reported though the assertion applies to `foo`'s result; it occurred once in the measured corpus, below, and is the hook's one known false positive.

**Measured on four public codebases** — about 580,000 lines, at the commits [`docs/toolchain.md`](../docs/toolchain.md) records — condition 2 reported sixteen assertions, each read in full. Eight were in build, benchmark and maintenance scripts, one in a test, three in sample extensions and one in an internal lint plugin. Two were in shipped code: hono asserts the body of a JSON Web Key Set response before reading keys from it, and the typescript-eslint website asserts state it reads back from the URL hash — both boundaries in exactly this rule's sense. The sixteenth, in zod's tests, is the `foo(JSON.parse(x)) as T` case.

**Nothing here chooses the library.** The rule says a schema parses at every boundary, and [`docs/libraries.md`](../docs/libraries.md) argues which. A codebase standardised on another runtime validator meets this rule with it unchanged.

**This rule does not reach the frontend clade's own boundaries in full.** A form's fields, a component's props and a store's state are typed by the frontend clade's artifacts in `ahrena-engineering-frontend`; a value read from `localStorage` or a URL parameter is a boundary under this rule wherever it is read.

## Sources

- ECMA-262, 17th edition (ES2026), §25.5.2 JSON.parse: <https://262.ecma-international.org/17.0/>.
- TypeScript's declarations, read from the 6.0.3 package: `lib.es5.d.ts` line 1161 (`JSON.parse … : any`) and `lib.dom.d.ts` line 5127 (`json(): Promise<any>`); `@types/node` 26.6.6, `process.d.ts` (`ProcessEnv extends Dict<string>`).
- Zod, `z.infer` and `safeParse`: <https://zod.dev/basics>; Standard Schema: <https://standardschema.dev/schema>.
- Fastify, validation and serialization: <https://fastify.dev/docs/latest/Reference/Validation-and-Serialization/>.
- typescript-eslint `no-unsafe-assignment`: <https://typescript-eslint.io/rules/no-unsafe-assignment/>.
