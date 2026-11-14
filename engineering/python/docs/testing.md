---
id: testing
type: doc
clade: engineering
subclade: python
title: pytest per layer, and the doubles each layer may use
summary: How a Python suite is laid out by the layer it exercises, what each layer's test may double and why, how fixtures and factory fixtures are scoped, where a property test earns its place, how async tests and a real database are set up, and how to read coverage without making it a gate.
references:
  - rules/testing.md
  - docs/architecture.md
  - docs/libraries.md
  - docs/persistence.md
  - docs/web-services.md
---

# pytest per layer, and the doubles each layer may use

[`rules/testing.md`](../rules/testing.md) decides one thing: no test patches a name under the domain or the use cases. This page is the rest of what a Python writer needs before writing a test — the structure, the doubles each layer may use, the fixtures, the async and database set-up, property tests and coverage. It is the predecessor's testing manual, aligned with the test-first skill in the backend plugin, which already fixes the arc per layer and is not restated: the domain red-first with no doubles, the use cases against doubles for their ports, the persistence layer against a real database, the API from the outside.

[`libraries.md`](libraries.md) names and argues the tools: pytest, pytest-asyncio, Hypothesis, `httpx.MockTransport`, testcontainers.

## Lay the suite out by what it touches

```
tests/
├── unit/           domain and use cases; no I/O, nothing to start
├── integration/    adapters against what they adapt: a database, an HTTP stub
└── acceptance/     the service from its edge, adapters real where it matters
```

The split is by cost, not by taste. A unit test runs in milliseconds with nothing started, so the whole unit tree runs on every save; an integration test starts a database, so it runs before a push and in the pipeline. A directory per kind lets a command select one kind without a marker on every test, and the markers the predecessor configured — `unit`, `integration`, `property` — are redundant with the directory and drift from it. Where a project already colocates tests beside the code, as `module-boundaries.md`'s layout allows with `foo_test.py`, the same split is made by marker or by name, and the cost argument is the same.

The share of each kind is not set here. The predecessor's 70/20/10 was never measured; #34 group Q1 owns the language-agnostic question of a suite's shape.

## What each layer may double

| Layer under test | Doubles | Why |
|---|---|---|
| domain | none | The domain imports no mechanism, so there is nothing to double. A domain test that needs a mock has found I/O in the domain. |
| use case | each port, with a fake | The port is the seam the use case was written against; a fake is a small class implementing the protocol, in the test tree. |
| adapter | what is outside the process | The repository against a real database; the HTTP client against `httpx.MockTransport`; the clock fixed through its port. |
| service edge | the outbound edges only | Routes, use cases and domain run; the outside world is a fake or a container. |

A fake beats a mock at the use-case layer for a reason a reader can check: a fake repository keeps what it was given in a dictionary, so a test asserts on the state after the operation — "the order is saved as paid" — rather than on the calls made — "`save` was called once with this argument". The first survives a refactor that changes how the use case talks to the repository; the second breaks on it and passes when the saved state is wrong.

The rule's one condition is the floor of this table, decided by the hook: a patch into `domain` or `application` is reported, because it replaces the code the test exists to run.

## Fixtures and factories

A fixture is named for what it provides and scoped to how long that thing can be shared without one test seeing another's leftovers:

- **Session scope** for what is expensive and immutable once built: the database container, the engine, the migrated schema.
- **Function scope** for everything a test changes: a session inside a transaction that is rolled back after the test, a fake repository, an application with its dependencies overridden.

Test data comes from **factory fixtures**: a fixture that returns a function building a valid domain value with defaults, so a test overrides only the field it is about and a reader sees which field that is. `make_order(status=Status.PAID)` says what the test depends on; a twenty-line literal says nothing about which of its twenty fields mattered. Plain functions do this; a factory library earns its place only when object graphs with relations make the functions repetitive.

Shared fixtures live in the `conftest.py` of the narrowest directory that shares them. A root `conftest.py` holding everything is a module every test imports and nobody owns.

## Async tests

pytest-asyncio runs a coroutine test on an event loop and lets a fixture be a coroutine or an async generator, so an async session is opened and closed with the same `async with` production uses. Set the plugin's mode once in the project's configuration rather than marking every test; and keep the event loop's scope to the default unless a session-scoped async fixture needs a longer-lived loop, in which case widen both together. A test that calls a coroutine without awaiting it passes without running anything; condition PY-8 of the review skill is where a reader catches that.

## A real database per test session

The persistence layer is tested against the engine it runs on, started once per session from testcontainers, migrated with Alembic to head, and then shared: each test opens a connection, begins a transaction, binds a session to it, and rolls the transaction back after the test. Every test starts from the empty migrated schema and none pays for a new database. [`persistence.md`](persistence.md) says why SQLite is not a substitute.

## Property tests

A property test states an invariant and lets Hypothesis generate the inputs: a fee is never negative and never exceeds the amount, parsing what was serialised returns the value, an aggregate's balance equals the sum of its entries after any sequence of valid operations. It belongs where a rule holds for a whole input space and a handful of examples would sample it badly — the domain, almost always. It complements the examples rather than replacing them: an example names the case a reader cares about, the property finds the one nobody thought of, and Hypothesis shrinks a failure to the smallest input that shows it.

The strategy is part of the test and is written from the domain's constraints — the range an amount may take, the currencies that exist — not from the type alone, or the property is tested against inputs the domain would refuse.

## Coverage is read, not gated

Coverage says which lines no test executed. That is useful for finding a branch nobody tested, and useless as a target: a suite can execute every line and assert nothing. The predecessor recommended 80% as a floor; [`rules/testing.md`](../rules/testing.md) records why no percentage appears here. Read the uncovered lines of a change at review, ask of each whether a behaviour lives there, and write the test if one does.

## Where this stops

**It does not set the suite's shape or its time budget.** The ratio between kinds, the budget per kind and the isolation conditions — random order, parallel runs — are #34 group Q1's, language-agnostic.

**It does not trace tests to criteria.** A test names the acceptance criterion it covers as the contributing plugin's traceability rule says; that is the same in every language.

**It does not cover the API's acceptance tests.** The backend plugin's behaviour-scenario skill owns the outermost layer's tests; [`web-services.md`](web-services.md) says how a FastAPI service is built for them.

**It does not configure pytest.** Which plugins, which options, which paths: the project's `pyproject.toml`, chosen by the project. This page argues the shape those options produce.
