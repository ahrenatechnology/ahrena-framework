---
id: libraries
type: doc
clade: engineering
subclade: typescript
title: The library for each problem, and when it is the wrong one
summary: For each problem a TypeScript service or library meets - validation, HTTP serving and calling, persistence and migrations, serialization, configuration, CLI, retries, logging, tracing, time, errors, tests, test doubles, property tests, workspaces - one recommended library, the reason, and the case where it is the wrong choice.
references:
  - rules/runtime-validation.md
---

# The library for each problem, and when it is the wrong one

A recommendation that cannot say when it is wrong is a preference. Each entry below names one library, the reason it is the default, and the case where a project should pick something else; an entry whose answer is "no library" says that too, because the platform now covers more than it did. Versions are those on npm on 2026-11-14, given so a reader can tell when the advice was written. The frontend clade's own choices — component frameworks, state, styling — are `ahrena-engineering-frontend`'s and are not here.

What makes a library the default here, in order: it is typed from its source rather than through hand-written declarations; it does one job; it runs on the Node LTS lines and, where the problem exists there, in a browser; and its own documentation states what it is for. Popularity breaks ties and never decides alone.

## Validation at a boundary

**Zod** (4.6). [`rules/runtime-validation.md`](../rules/runtime-validation.md) requires a schema at every boundary and the type derived from it, and Zod is that in one object: `z.infer<typeof Schema>` gives the type, `safeParse` returns a discriminated union of success with the data or failure with the error, and `z.toJSONSchema()` publishes the same schema to other languages. It implements Standard Schema, the common interface Valibot and ArkType also implement, so a framework that accepts one accepts all three.

*Wrong when* the code ships to a browser where bundle size is measured: **Valibot** is built from tree-shakeable functions, and its documentation gives its size as "starting at less than 700 bytes". *Also wrong* inside a Fastify route, where the framework already validates the request against a JSON Schema before the handler runs; a second parse there checks the same thing twice.

## Serving HTTP from Node

**Fastify** (5.12). It validates requests and serializes responses from JSON Schema declared on the route, so the boundary of [`rules/runtime-validation.md`](../rules/runtime-validation.md) is the route definition itself, and it describes itself as "fast, low-overhead". Its plugin system scopes dependencies, which keeps the composition root of [`project-layout.md`](project-layout.md) explicit.

*Wrong when* the code must also run outside Node — Cloudflare Workers, Deno, Bun, a Lambda behind a function URL: **Hono** runs on all of them with one API and is built on the web-standard `Request` and `Response`. *Also wrong* inside a framework that owns its routing, such as Next.js route handlers; adding a server there is a second router.

## Calling HTTP

**No library: the built-in `fetch`.** It is global in Node since v18, no longer experimental since v21, and is built on undici. Two facts about it are where the bugs live, and [`async.md`](async.md) and [`error-handling.md`](error-handling.md) carry them: it does not reject on a 4xx or 5xx response, only on a network failure, so `response.ok` is checked every time; and it has no timeout, so every call carries `signal: AbortSignal.timeout(ms)`.

*Wrong when* one upstream is called at a volume where connection pooling matters: undici's own `Pool` exposes what `fetch` hides. *Also wrong* when the provider publishes an SDK generated from its OpenAPI document; the SDK is the typed boundary, and its responses still pass through a schema when the provider is not this team.

## Persistence

**Kysely** (0.29). A type-safe SQL query builder: the query in the source reads as the SQL it runs, the result type follows from the table types, and there is no runtime engine between the code and the driver. Code review reads SQL, which is the language the database's own documentation, its query plans and its DBA speak.

*Wrong when* the team wants the schema declared in TypeScript and migrations generated from that declaration: **Drizzle** with drizzle-kit does that, and its 0.45 line is the stable one while 1.0 is still in beta. *Also wrong* for a document store, which has its own typed driver.

## Migrations

**Kysely's `Migrator`**, with migrations as ordered TypeScript files read by its `FileMigrationProvider`. One tool for queries and schema changes; each migration is a reviewed file with `up` and `down`.

*Wrong when* the schema is shared with services in other languages: the migrations belong to the database, not to one TypeScript service, and a language-neutral tool that runs plain SQL files keeps them there. The backend clade's data and persistence artifacts own the destructive-migration discipline either way.

## Serialization

**No library: JSON, through the schema.** `JSON.stringify` on the way out, a schema parse on the way in. The values JSON cannot carry are decided in the schema: dates travel as ISO-8601 strings and are parsed back, and an integer beyond `Number.MAX_SAFE_INTEGER` travels as a string, as TS-12 of `reviewing-typescript` says.

*Wrong when* messages cross languages at volume, or need a schema evolution story: **`@bufbuild/protobuf`** (2.17) implements Protocol Buffers and describes itself as "fully compliant with the Protobuf conformance tests".

## Configuration

**No library: the validation library, run on `process.env` once, at startup.** A schema of every variable the process needs, parsed before anything else runs, with every failure named in one error. That is condition 4 of [`rules/runtime-validation.md`](../rules/runtime-validation.md) applied to the first boundary a process has, and it gives the rest of the code a typed, frozen configuration object instead of `process.env` reads scattered through it.

*Wrong when* the framework owns its configuration and its build inlines variables, as Next.js does with its public variables; follow the framework there and parse what it hands over.

## Command-line programs

**commander** (15.1, which requires Node 22.12 or later). Subcommands, help text and typed options with a stable API.

*Wrong when* the program is a script with three flags: Node's own `util.parseArgs` covers it with no dependency.

## Retries, timeouts and circuit breakers

**cockatiel** (4.0). One library for retry with backoff, circuit breaker, timeout, bulkhead and fallback, composed into one policy. A retry without a breaker turns an outage into a load test, and having both in one composed policy is the reason.

*Wrong when* one call needs a retry and nothing else: **p-retry** is smaller, and its `AbortError` stops retrying on a failure that will not get better. Neither replaces the idempotency key that makes a retried write safe, which is [`async.md`](async.md)'s subject.

## Logging

**pino** (10.4). Structured JSON, one line per event, "very low overhead"; transports run in a worker thread so formatting and shipping do not block the event loop. Its child loggers carry request context without threading it through every call.

*Wrong when* the program's output is for a person at a terminal — a CLI's messages are `console` output, and a JSON log line there is noise.

## Tracing and metrics

**OpenTelemetry JS** (`@opentelemetry/sdk-node`). The vendor-neutral standard; its traces and metrics are stable, and its logs signal is still in development, which is why pino owns logging above and is bridged to the trace context rather than replaced.

*Wrong when* the platform already instruments the runtime and exports traces itself; a second SDK double-counts spans.

## Dates and times

**date-fns** (4.4) today. Pure functions over the built-in `Date`, tree-shakeable, typed from source.

*Wrong when* the code runs only where `Temporal` exists: it is a Stage 4 proposal shipped in Node 26, Chrome 144 and Firefox 139, and MDN still marks it "Limited availability". A Node 26 service can use `Temporal` and no library; code that reaches Safari cannot yet.

## Errors as values

**No library.** Exceptions for the unexpected, discriminated unions for the failures a caller must handle, as [`error-handling.md`](error-handling.md) argues. A union is a type the compiler already narrows; it needs nothing installed.

*Wrong when* a codebase has decided that every fallible function returns a result and wants the combinators to chain them: **neverthrow** ("Type-Safe Errors for JS & TypeScript") is the library for that decision. Effect is a different decision — a runtime and a programming model — and is adopted as a framework, not reached for as a library.

## Tests

**Vitest** (5.1, which requires Node 22.12 or later). TypeScript and ESM run without configuration, the API is Jest's, it tests types as well as values (`expectTypeOf`, `--typecheck`), and its default coverage provider is V8's. [`testing.md`](testing.md) argues how tests are written with it.

*Wrong when* a dependency-free library wants a dependency-free test suite: Node's built-in `node:test` is stable since v20 and picks up `*.test.ts` files through type stripping.

## Test doubles for the network

**MSW** (3.0). It intercepts requests at the network layer in the browser and in Node, so the code under test runs its real `fetch`, its real error handling and its real parse, and only the far side is fake.

*Wrong when* the collaborator is injected and not a network call: a hand-written fake implementing the port is shorter, typed by the port itself, and needs no library. A mocking library that patches modules is wrong in both cases, as [`testing.md`](testing.md) argues.

## Property-based tests

**fast-check** (4.10). Generators for every built-in type and for a schema's shape, shrinking to the smallest failing input, and a seed printed on failure so the case is reproducible.

*Wrong when* the input domain is small enough to enumerate: a table of examples says the same thing and reads faster.

## Workspaces

**pnpm workspaces.** Its `workspace:` protocol makes pnpm "refuse to resolve to anything other than a local workspace package", so a workspace dependency cannot silently resolve to a published version; its strict `node_modules` layout refuses an import of a package the importer did not declare.

*Wrong when* the repository holds one package: npm is already installed and enough.

## Keeping the tree honest

**knip** finds unused files, exports and dependencies. **dependency-cruiser** reports import cycles through path aliases, which [`rules/module-boundaries.md`](../rules/module-boundaries.md)'s hook does not resolve, and holds architectural rules beyond the package boundary. Both are optional: a project without aliases needs neither for this plugin's conditions to hold.

## Where this stops

**Every recommendation here is a default, not a rule.** No rule in this plugin names a library except where a condition does not exist without a tool — the type checker and the type-aware linter of [`toolchain.md`](toolchain.md). A codebase standardised on another validator, another test runner or another server meets every rule here unchanged.

**The versions will age.** Each one is the npm `latest` on 2026-11-14. A recommendation whose library stops being maintained is wrong from that day, the way tsup's entry was replaced by tsdown's in [`toolchain.md`](toolchain.md).

**Security and supply chain are not judged here.** Whether a dependency is pinned, vetted and free of known vulnerabilities is the security disciplines' `reviewing-supply-chain`, applied to whatever this document recommends.
