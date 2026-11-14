---
id: libraries
type: doc
clade: engineering
subclade: go
title: Libraries, by problem, standard library first
summary: For each problem a Go service meets — routing, persistence, migrations, configuration, logging, tracing and metrics, CLI, validation, retries, rate limiting, identifiers, test assertions, doubles and containers — the standard library or one recommended module, what the standard library lacks, and when the recommendation is wrong.
references:
  - docs/toolchain.md
  - docs/testing.md
  - docs/logging-and-observability.md
  - docs/concurrency.md
---

# Libraries, by problem, standard library first

Go's standard library is large on purpose, and the first answer to "which library?" is usually none. Every entry below starts there and names a module only where the standard library leaves a real gap, says what the gap is, and says when even that module is the wrong choice. One module per problem: a list of three alternatives is a choice not made, and the point of a recommendation is that a project can stop deliberating.

The state of each module was checked on 2026-11-14 — latest release, whether the repository is archived, whether it is still maintained — against the module proxy and the project's own repository. No version is pinned here, for the reason [`docs/toolchain.md`](toolchain.md) gives: a pin is true until the next release. The module path carries the major version, because that is part of the import path and changing it is a migration.

## How to read an entry

- **Use** — the standard library package, or the module path.
- **Why** — what the standard library lacks for this problem. Where it lacks nothing, the entry says so and recommends the standard library.
- **Not when** — the case where this choice is wrong.

## HTTP

### Routing

- **Use** `net/http`'s `ServeMux`.
- **Why** since Go 1.22 it matches methods and wildcards in patterns — "method matching and wildcards", in the Go blog's *Routing Enhancements for Go 1.22* — which was the reason most services reached for a router. A pattern like `GET /orders/{id}` and `r.PathValue("id")` cover a typical REST surface.
- **Not when** the service has many route groups that share middleware. `ServeMux` has no groups and no middleware chain; middleware is a function wrapping an `http.Handler`, composed by hand. When that composition becomes the bulk of the routing file, use `github.com/go-chi/chi/v5`, which is built on the same `http.Handler` and adds `Group`, `Route` and a middleware stack without a framework's request type. Not a framework with its own context type (`gin`, `echo`, `fiber`): handlers written against it cannot be reused with anything else, and `fiber` is not built on `net/http` at all.

### HTTP client

- **Use** `net/http`'s `Client`, one per configuration, with a `Timeout` or a context deadline on every request.
- **Why** the standard client lacks nothing a service needs; its zero-value `http.DefaultClient` has no timeout, which is the defect, not the package.
- **Not when** never as `http.DefaultClient` for an outbound call to another service — set a timeout. Retries are a separate problem, below.

## Persistence

### PostgreSQL access

- **Use** `github.com/jackc/pgx/v5`, through `pgxpool` for a pool.
- **Why** `database/sql` is a lowest-common-denominator interface: it has no `LISTEN`/`NOTIFY`, no `COPY`, and maps PostgreSQL types through `driver.Value`. pgx's own README describes it as "a low-level, high performance interface that exposes PostgreSQL-specific features such as LISTEN / NOTIFY and COPY", and it also ships a `database/sql` adapter (`pgx/v5/stdlib`).
- **Not when** the code must run against more than one database engine, or a library the project depends on takes a `*sql.DB`. Then use `database/sql` with pgx as its driver through the adapter, and accept the lowest common denominator on purpose. For any other engine, `database/sql` with that engine's maintained driver is the answer; the connection pool's limits are set through `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxIdleTime` and `SetConnMaxLifetime`, documented in *Managing connections* on `go.dev`.

### Queries

- **Use** `github.com/sqlc-dev/sqlc`, a code generator: SQL in `.sql` files, typed Go functions out.
- **Why** neither `database/sql` nor pgx checks a query against the schema. A typo in a column name is a run-time error. sqlc reads the schema and the queries at generation time and fails there, and the generated code is plain Go with no runtime dependency on sqlc.
- **Not when** queries are assembled dynamically — a search endpoint with a dozen optional filters — which a static generator cannot express. Write those by hand with parameterised arguments, beside the generated ones. Not an ORM in either case: an ORM's query is built at run time from method calls, which reintroduces the run-time failure sqlc removes and hides the SQL a reviewer needs to read.

### Migrations

- **Use** `github.com/pressly/goose/v3`.
- **Why** the standard library has no migration runner. goose runs SQL files and, when a migration needs logic, Go functions — its README says it "Supports Go migrations written as plain functions" — and it reads migrations from an `embed.FS`, so the binary carries its schema.
- **Not when** every migration is plain SQL and the team already runs `github.com/golang-migrate/migrate/v4`, which is maintained, reads from an `io/fs` and therefore from `embed.FS`, but has no Go-function migrations. Switching runners mid-project costs a migration-history conversion that buys nothing.

## Configuration

- **Use** `os.Getenv` / `os.LookupEnv` and the `flag` package, with a single function that reads everything into a typed struct at start-up and fails on a missing required value.
- **Why** the standard library lacks only the struct-tag binding, and a service with fifteen settings writes that function in fifteen lines that are easy to read and need no dependency.
- **Not when** the settings run to dozens, with nested prefixes and slices. Then use `github.com/caarlos0/env/v11`, a dependency-free module that parses environment variables into a struct by tag and is maintained. Not `github.com/kelseyhightower/envconfig`: it is not archived, but its last release was in 2019. Not a configuration framework that merges files, flags, environment and remote stores (`viper`): the precedence order becomes a thing to debug, and twelve-factor configuration needs only the environment.

## Logging

- **Use** `log/slog`.
- **Why** since Go 1.21 structured logging is in the standard library — accepted proposal golang/go#56345 and the Go blog's *Structured Logging with slog* — with a JSON and a text handler, a `Handler` interface third parties implement, `DiscardHandler` since Go 1.24 and `NewMultiHandler` since Go 1.26. [`docs/logging-and-observability.md`](logging-and-observability.md) argues how to use it.
- **Not when** a profile shows the logger on the hot path of a latency-critical service. Even then, keep `slog` as the API and swap the handler for a faster one behind it, so the call sites never change.

## Tracing and metrics

- **Use** `go.opentelemetry.io/otel` for traces and metrics, with the OTLP exporters.
- **Why** the standard library has `runtime/trace` and `expvar`, which describe one process; it has nothing that propagates a trace across services or exports to a collector. OpenTelemetry's Go documentation lists traces and metrics as stable; logs are a release candidate there, which is a reason to keep logs on `slog` and bridge them, not to log through the OpenTelemetry API.
- **Not when** the platform scrapes Prometheus and nothing else, and the service has no traces. Then `github.com/prometheus/client_golang` exposes metrics directly, without a collector in between. Adopting OpenTelemetry later costs re-instrumenting, so a service that will need traces starts with OpenTelemetry.

## Command-line programs

- **Use** the `flag` package.
- **Why** a program with one command and a dozen options needs nothing else, and `flag.FlagSet` is, in the package's own words, how to "implement subcommands in a command-line interface".
- **Not when** the program is a tree of subcommands with shared persistent flags, generated help and shell completion — the shape of `kubectl` or `gh`. Then use `github.com/spf13/cobra`, which is maintained and is the convention most Go CLIs of that shape follow, so its users know the help layout already.

## Validation

- **Use** plain Go: a `Validate() error` method on the request type, returning every violation joined with `errors.Join`.
- **Why** validation rules are domain rules, and a function states them in the language the reviewer already reads. The standard library lacks a tag-driven validator, and a service with a handful of request types does not need one.
- **Not when** the service has dozens of request types whose rules are mostly field-level formats — required, length, email, range. Then `github.com/go-playground/validator/v10` validates by struct tag and is maintained. Keep cross-field and domain rules in methods even then: a rule spread across tags and code is a rule nobody reads whole.

## Retries and backoff

- **Use** `github.com/cenkalti/backoff/v7`.
- **Why** the standard library has no retry helper, and a hand-written loop gets the details wrong in the same three ways: no jitter, so every client retries in step; no cap, so the delay grows past any useful deadline; and no context, so a cancelled request keeps retrying. The module takes a context and implements exponential backoff with jitter. Its major version moved from v4 to v7 in two years; read the changelog before raising it.
- **Not when** the call is not idempotent — a payment, an order — and the server offers no idempotency key: retrying it creates a second one. And not when the client library already retries (the AWS and Google Cloud SDKs do): retrying a retrier multiplies attempts. The reliability plugin's review reads both cases.

## Rate limiting

- **Use** `golang.org/x/time/rate`.
- **Why** the standard library has no rate limiter; `x/time/rate` is a token bucket maintained by the Go team, outside the compatibility promise but under the same project.
- **Not when** the limit must hold across replicas. A process-local bucket limits one process; a fleet-wide limit needs a shared store, and that is an infrastructure decision, not a library.

## Concurrency helpers

- **Use** `sync` and, for a group of goroutines that can fail, `golang.org/x/sync/errgroup`.
- **Why** `sync.WaitGroup` waits but carries no error and cancels nothing; `WaitGroup.Go`, added in Go 1.25 by accepted proposal golang/go#63796, removes the ordering mistake but still carries no error. `errgroup.WithContext` returns the first error and cancels the derived context for the rest, and `SetLimit` bounds how many run at once. [`docs/concurrency.md`](concurrency.md) argues when each fits.
- **Not when** the goroutines cannot fail: then `WaitGroup.Go` is enough and the dependency is not needed.

## Identifiers

- **Use** the `uuid` package, from Go 1.27.
- **Why** Go 1.27 adds, through accepted proposal golang/go#62026, a top-level `uuid` package that generates and parses UUIDs per RFC 9562, with `New`, `NewV4` and `NewV7`. Before 1.27 the standard library had none.
- **Not when** the module's `go` directive is below 1.27. Then `github.com/google/uuid` is the answer until the module raises its version, at which point the dependency is removed.

## Tests

### Assertions and comparison

- **Use** the `testing` package with `if got != want { t.Errorf(…) }`, and `github.com/google/go-cmp/cmp` for comparing structures and printing a diff.
- **Why** the Go FAQ, *Where is my favorite helper function for testing?*, explains why the standard library has no assertion functions, and the Google Go style guide, decisions, says not to create assertion libraries. What the standard library does lack is a readable diff of two nested values; `reflect.DeepEqual` answers yes or no. `cmp.Diff` prints the difference, and its documentation says it is "intended to only be used in tests".
- **Not when** the project already standardised on `github.com/stretchr/testify`. Rewriting a passing suite buys nothing. New code in such a project keeps `got`/`want` messages with `got` first, which `testify`'s argument order inverts. [`docs/testing.md`](testing.md) argues the shape.

### Test doubles

- **Use** a hand-written fake that implements the consumer's small interface.
- **Why** an interface declared by its consumer, as [`rules/api-surface.md`](../rules/api-surface.md) condition 3 asks, has two or three methods, and a fake for it is a struct with a few fields. A fake states behaviour; a generated mock states call sequences, and a test written against call sequences breaks on every refactor.
- **Not when** the interface is large and owned by someone else — a cloud SDK client — and only a few methods matter per test. Then generate with `go.uber.org/mock`, the maintained fork; `github.com/golang/mock` is archived and points there.

### Integration dependencies

- **Use** `github.com/testcontainers/testcontainers-go`.
- **Why** the standard library starts no database. Testcontainers starts a real one in a container per test package and removes it after, so the integration test runs against the engine production runs, not an in-memory imitation.
- **Not when** CI cannot run containers. Then the database is a CI service container and the test reads its address from the environment; the test code stays the same.

### Goroutine leaks and time

- **Use** `testing/synctest`, generally available since Go 1.25, for code that waits on timers; and `go.uber.org/goleak` in `TestMain` to fail a package that leaves goroutines behind.
- **Why** `synctest` runs a test in a bubble with a fake clock, so a five-minute timeout is tested in microseconds without injecting a clock. The standard library has no test-time leak check; the `goroutineleak` profile, generally available in Go 1.27, finds leaks in a running program, not at the end of a test. `goleak` has had no release since 2023 and has not needed one; its repository is still maintained.
- **Not when** for `goleak`, the package under test starts a deliberate background goroutine that outlives the test, such as a connection pool's reaper. Ignore it by name with the option `goleak` provides, rather than dropping the check.

## Where this stops

**This is not a catalogue.** A problem not listed here is one this framework has no opinion on yet, and the absence is not a recommendation of the most popular module.

**It does not choose a web framework, an ORM or a dependency-injection container**, and the omission is the position: each replaces a standard interface with its own, and the entries above prefer modules that sit on `net/http`, `database/sql` and plain constructors.

**The checks are dated.** Maintenance was read on 2026-11-14. A module recommended here that is archived later is no longer recommended, and the first person to notice updates this page.

**Security and supply chain are not here.** Whether a dependency may be added at all — its licence, its maintainers, its install-time behaviour — is the security plugin's `reviewing-supply-chain` discipline.
