---
id: libraries
type: doc
clade: engineering
subclade: python
title: The library for each problem, and when it is the wrong one
summary: For each problem a Python service meets — HTTP, validation, settings, outbound calls, retries, persistence, migrations, logs, traces, CLIs, tests and their doubles, type checking, linting, audit — the one library this framework recommends, why, and the case where it is the wrong choice.
references:
  - rules/typing.md
  - rules/security.md
  - docs/toolchain.md
  - docs/web-services.md
  - docs/persistence.md
  - docs/testing.md
  - docs/logging-and-observability.md
---

# The library for each problem, and when it is the wrong one

The predecessor named a stack — FastAPI, Pydantic, SQLAlchemy with asyncpg and Alembic, Loguru, OpenTelemetry, pytest with pytest-asyncio and Hypothesis, testcontainers, Ruff, mypy, pip-audit — and scattered it across seven documents, each naming its own corner and none saying why or when not. This page collects it, keeps what it can argue, replaces one choice it cannot, and adds the problems the predecessor's specialists met without naming a library for.

Every entry has the same three parts, because a recommendation without the third is a preference. **Use** names one library. **Why** is the property that decides it, stated so a reader can check it against their own situation. **Not when** is the case where the recommendation is wrong, and it is written first-hand rather than as a hedge: if the case applies, do the other thing.

No entry carries a version. A floor is true the day it is typed and wrong on a schedule after that; [`toolchain.md`](toolchain.md) argues that at length, and the lock file is where a project records what it chose.

**A project's own choice wins.** The fundamentals plugin's ubiquitous-language rule says the framework default applies only where the project is silent, and that is the status of every entry here. A repository already on Django, on `requests`, on pyright, is not asked to migrate by this page; it is told what the framework would pick for a new service, and why, so the difference is a decision rather than an accident.

## The service edge

### HTTP service

**Use** FastAPI.

**Why.** The function signature is the contract. A route declares its parameters and its body as typed values, and FastAPI derives the validation, the error response and the OpenAPI document from those types, so the three cannot drift from each other or from the code. `Depends` gives each request a composition root, which is where a port meets its adapter, and `app.dependency_overrides` swaps an adapter in a test without patching anything — the property [`rules/testing.md`](../rules/testing.md) needs. It runs on ASGI, so an endpoint that waits on a database does not hold a thread.

**Not when.** The service renders pages, needs an admin, and is mostly forms over a relational model: Django gives all three and FastAPI gives none. And when the process is not an HTTP server at all — a queue consumer, a scheduled job — no web framework belongs in it; the handler is a function, and the AWS Lambda entry below or the CLI entry covers it.

### Validation and serialisation at the boundary

**Use** Pydantic.

**Why.** A model is a type the checker understands and a parser the runtime enforces, in one declaration, so what `mypy --strict` believes about a request body is what actually arrived. Strict mode refuses coercions — `"5"` for an `int` — that would otherwise let a malformed payload through looking valid. `model_dump_json` writes the same shape back out, so the response is described by the same type that validated the request. This is the half of INP-8 in the security plugin a library can do: a body parsed into a model that names its fields cannot set one the form never offered.

**Not when.** Inside the domain. The fundamentals domain-model rule keeps frameworks out of `domain/`, and a domain value is a frozen dataclass that [`rules/immutability.md`](../rules/immutability.md) holds; the adapter maps between the two. And on a measured hot path where serialising large payloads dominates the profile, a dedicated encoder such as orjson or msgspec is faster — measured, not assumed.

### Settings

**Use** pydantic-settings.

**Why.** Configuration is outside input like any other, and it fails the same way: a missing variable, a string where a number was meant, a URL with a typo. Declaring settings as a model validates all of them once, at start-up, and names every one that is wrong in one error — instead of the first `os.environ["X"]` that raises on the first request that reaches it. A secret field typed `SecretStr` does not print itself into a log, which is DAT-1's concern handled by a type.

**Not when.** A script or a hook with two variables and no dependencies: `os.environ.get` with an explicit default or an explicit error is the whole solution, and a library for it is the abstraction condition 1 of the fundamentals YAGNI rule refuses.

### Outbound HTTP

**Use** httpx.

**Why.** One API for synchronous and asynchronous code, so an adapter does not change libraries when its caller becomes async. A timeout is on by default — five seconds — where `requests` waits forever unless told otherwise, and a call with no timeout is the reliability plugin's first finding. `httpx.MockTransport` replaces the network inside the client with a function, so a test doubles the outbound edge at the adapter without patching a module, which is what [`docs/testing.md`](testing.md) asks for.

**Not when.** A codebase already built on `requests` with no async in sight: the migration buys an import line. And a service that also needs a websocket client and server in one library may be better served by aiohttp.

### Retries

**Use** tenacity.

**Why.** The fundamentals cross-cutting-concerns rule makes a retry written inline — a loop with a handler and a sleep — a defect, and asks for the policy to be declared once at a boundary. Tenacity is that declaration: a decorator or a context manager that states what to retry on, how long to wait, and when to stop, in one place a reader can find. It retries on a predicate, so a retry can be limited to the failures that are worth repeating — a timeout, a 503 — rather than every exception.

**Not when.** The client underneath already retries: botocore retries AWS calls itself, and a second retry layer around it multiplies the attempts and the latency. And never around an operation that is not idempotent and carries no idempotency key: condition 4 of the cross-cutting-concerns rule is what makes a retry safe, and without it a retry is a second charge.

### Serverless handlers on AWS Lambda

**Use** Powertools for AWS Lambda (Python).

**Why.** The predecessor's job specialist built every handler on it, and the reasons hold: idempotency backed by a store and keyed by the event's own key, batch processing that reports partial failures so one bad message does not redeliver the whole batch, and a logger, tracer and metrics client that already speak Lambda's context. Each of those is a cross-cutting concern the fundamentals rule wants declared once, and Powertools declares it.

**Not when.** The code does not run on Lambda. On a container or a VM the same concerns are tenacity, a database-backed idempotency table and OpenTelemetry, and importing Powertools there buys a dependency on a runtime that is not present.

## Persistence

### Relational database access

**Use** SQLAlchemy, in its 2.0 style, with `Mapped` annotations.

**Why.** It is the one library that does both halves: Core composes SQL as typed expressions, so a parameter is always bound and never interpolated (INP-1), and the ORM maps rows to classes where that pays. The 2.0 style is typed end to end — `select(Order).where(...)` returns rows the checker knows the type of — which is what lets `rules/typing.md` hold over the persistence layer at all. Its async extension runs the same statements on an event loop. [`docs/persistence.md`](persistence.md) argues where the session lives and why the repository maps to domain values.

**Not when.** A service with a handful of fixed queries and no object graph: psycopg used directly, with its own parameter binding, is less to learn and less to load. And analytical work over large tables belongs to the data plugin and its tools, not to an ORM, which materialises objects a scan never needed.

### PostgreSQL driver

**Use** asyncpg under async SQLAlchemy; psycopg 3 everywhere else.

**Why.** asyncpg is the driver SQLAlchemy's async extension is built and tested against for PostgreSQL, and it speaks the binary protocol without a C client library. psycopg 3 is the driver for synchronous code, for code that needs both modes, and for anything that talks to PostgreSQL without an ORM.

**Not when.** This is one recommendation split by mode, and it is wrong only when the mode is: a service that is synchronous end to end has no use for asyncpg.

### Migrations

**Use** Alembic.

**Why.** It reads the same metadata the models declare, so a migration can be drafted from the difference between the models and the database, and it records a revision graph a deployment can move forward and back along. A drafted migration is a draft: `persistence.md` says what to read in it before it runs.

**Not when.** The schema is owned by another tool or another team — a data platform that manages tables with its own migrations, a Django project with its own. Two migration histories over one schema is a race nobody wins.

## Diagnosis

### Logs

**Use** the standard library's `logging` as the interface, with structlog rendering structured records.

**Why.** Every library a service depends on — SQLAlchemy, httpx, uvicorn, botocore — already writes to the standard library's logger tree, so that tree is where the service's own records belong too: one configuration decides levels and output for all of them. structlog adds what the standard library lacks: context bound once — a request id, a tenant, an operation — carried through `contextvars` into every record the request writes, and a JSON renderer that turns each record into fields a query can filter on. Condition 5 of `rules/typing.md` already recognises `logger.exception` and its siblings as leaving a trace, so code written this way satisfies the hook without a second vocabulary.

**This replaces the predecessor's choice.** The predecessor used Loguru and a rule that no function body may call the logger, only a decorator that records entry, exit and error. Both are set aside. Loguru replaces the standard logger tree rather than joining it, so every dependency's records reach it only through an interception handler the project has to write and remember. The decorator-only rule collides with the observability plugin, which owns this concern: its OBS-1 asks for a failure to be logged where it is handled, with the identifiers of what it was acting on, and a decorator wrapped around the function cannot see an identifier the function found halfway through. Where the predecessor and the owning plugin disagree, the owning plugin wins. [`docs/logging-and-observability.md`](logging-and-observability.md) carries the rest.

**Not when.** A small command-line tool that writes to a terminal for a person: `logging` alone, with its default formatter, is the right amount.

### Traces and metrics

**Use** the OpenTelemetry SDK, with the instrumentation packages for the libraries above.

**Why.** It is the one interface every tracing and metrics backend reads, so the code names no vendor and the backend is a deployment decision. The instrumentation packages for FastAPI, SQLAlchemy, asyncpg, httpx and `logging` produce a span per request, per query and per outbound call, and put the trace id on every log record, without a line in the application — which is OBS-4's correlation id, provided by the framework rather than threaded by hand.

**Not when.** The platform already runs a vendor agent that instruments the process — a Datadog or New Relic agent attached at start-up. Adding OpenTelemetry beside it produces two traces of everything; use the agent, or move the platform to OTLP, but not both.

## The command line

### Command-line interface

**Use** Typer.

**Why.** The same idea FastAPI applies to HTTP: the function signature, with its annotations, is the interface, and help, parsing and validation are derived from it. A command written this way is checked by `mypy --strict` like any other function.

**Not when.** The tool must take no dependency, which is the case for every hook in this repository: argparse is in the standard library and does the job with more lines. That is the right trade wherever an install step cannot be assumed.

## Tests

### Test runner

**Use** pytest.

**Why.** A test is a function and an assertion is `assert`, with the failing values printed by assertion rewriting. Fixtures inject what a test needs by naming it, with a scope that says how long it lives, which is how a database engine is built once per session and a transaction once per test. `parametrize` turns one test into a table of cases. [`docs/testing.md`](testing.md) argues the structure.

**Not when.** The code under test must run where nothing can be installed. This repository's own hook suites are that case: each is a script with a small harness, run by `python3`, because a consumer has to be able to run exactly what CI runs.

### Async tests

**Use** pytest-asyncio.

**Why.** It runs a coroutine test on an event loop and lets fixtures be coroutines, so an async repository is set up and torn down with the same `async with` it uses in production.

**Not when.** The project is written against AnyIO or Trio rather than asyncio: AnyIO's own pytest plugin runs the same test on each backend, which is the property such a project chose AnyIO for.

### Property tests

**Use** Hypothesis.

**Why.** An invariant — a fee is never negative, a round trip through the serialiser returns the value — is stated once and checked against hundreds of generated inputs, and a failure is shrunk to the smallest input that breaks it. It finds the edge a hand-picked example did not think of, which is the gap the predecessor's quality epic named in the correctness family of #34.

**Not when.** No property can be stated: a behaviour that is a list of special cases is tested by the list. And a test that touches a real database or the network runs each generated case against it; keep generation to pure code, where a hundred cases cost milliseconds.

### Outbound HTTP doubles

**Use** `httpx.MockTransport`.

**Why.** It is part of httpx, so it costs no dependency, and it doubles the network inside the client the adapter already takes — the test passes a client built on a function that answers requests, and the adapter's own code runs unchanged.

**Not when.** The adapter is built on `requests`: `responses` is the equivalent there. And when a test has dozens of routes to answer, respx gives a routing table over httpx that a hand-written function becomes a poor copy of.

### Real dependencies in integration tests

**Use** testcontainers.

**Why.** The backend plugin's test-first skill drives the persistence layer against a real database with the migrations applied, because the defects that layer owns — a violated constraint, a transaction that does not roll back, a query the planner rejects — do not exist in a double. Testcontainers starts the same engine and version the service runs against, from the test session, and removes it after.

**Not when.** The pipeline already provides the database as a service container, or there is no container runtime where the tests run. Then point the tests at what is there; starting a second database inside the first's pipeline buys nothing.

## The toolchain

### Type checking

**Use** mypy, with `--strict`.

**Why.** This is the one library a rule here requires, and [`rules/typing.md`](../rules/typing.md) carries the argument: an AST sees that an annotation is missing, and only a type checker sees that one is wrong.

**Not when.** The project has standardised on pyright. The typing rule's own boundary section prices that: substitute the checker, write down that you did, keep the other conditions.

### Linting and formatting

**Use** Ruff.

**Why.** One tool for both, fast enough to run on every save, with the rule families [`toolchain.md`](toolchain.md) triaged available behind one switch each.

**Not when.** Nothing in this framework requires it; the hooks hold without any linter. A project already running Black and flake8 with a configuration it understands gains speed by moving and loses nothing by staying.

### Dependency audit

**Use** pip-audit.

**Why.** It reads the resolved dependency set and reports each package with a published advisory against its version, which is SUP-6 of the security plugin decided by a tool. It reads the lock file the project already has.

**Not when.** The forge or the platform already scans the same lock file — GitHub's dependency alerts, a registry's scanner — and fails the pipeline on a finding. Two scanners over one file produce two tickets for one advisory.

## Where this stops

**One library per problem, and the project's choice first.** An entry is the framework's default for a service that has not chosen, not a migration order for one that has.

**No versions, no configuration.** What a project pins and how it configures each tool is the project's, recorded in its lock file and its `pyproject.toml`. This page says why a library is chosen, which is the part that does not change at its next release.

**The problems are a service's.** A data pipeline, a notebook, a machine-learning training job and a desktop application meet different problems, and the data plugin owns the first. Nothing here is a recommendation for them.

**Two of the predecessor's choices are not carried.** Loguru, for the reason in the logs entry. And the predecessor's `result` package, which its observability document used to classify outcomes: the result type it serves was dropped by #34 as an error model rather than a quality condition, and a recommendation for the library would reopen that verdict without a decision record.

**The LLM agent runtime is not here.** The predecessor's agent specialist built on a specific agent SDK and model provider for one client's platform. That choice is a platform decision, and the conditions that keep a model's use safe in any runtime are the security plugin's `reviewing-model-use`, not a library entry.
