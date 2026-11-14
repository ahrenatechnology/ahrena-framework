---
id: architecture
type: doc
clade: engineering
subclade: python
title: What goes in each layer, and how the layers meet
summary: The inside of the three layers module-boundaries declares — values and rules in the domain, use cases and their ports in application, adapters and the composition root in infra — why a port is a Protocol, where async belongs, how a failure crosses the layers, and when not to abstract at all.
references:
  - docs/module-boundaries.md
  - rules/module-boundaries.md
  - rules/immutability.md
  - rules/error-handling.md
  - docs/web-services.md
  - docs/persistence.md
---

# What goes in each layer, and how the layers meet

[`module-boundaries.md`](module-boundaries.md) decides the outside of a context: three layers, `domain`, `application` and `infra`, each its own distribution under `components/{context}/`, importing only downward, with an import graph a script proves acyclic. It says nothing about what goes inside each layer, and on purpose: a script cannot count concepts. This page is the inside. It is the predecessor's architecture manual, rewritten against the layout this plugin already enforces, and it keeps that manual's best section — when not to abstract — nearly whole.

## The three layers, from the inside

**`domain/` holds the rules and nothing that does I/O.** Values, entities, aggregates, domain services and the exceptions that name a broken invariant. A value is a frozen dataclass, which condition 1 of [`rules/immutability.md`](../rules/immutability.md) holds; an entity whose state moves on purpose says so on its decorator. The fundamentals domain-model rule keeps every framework, driver and transport out of the layer, and the test-first skill in the backend plugin draws the consequence: the domain is tested with no doubles at all, because there is nothing in it to double. A domain function returns a new value rather than changing the one it was handed, which is condition 2 of the same rule.

**`application/` holds the use cases and the ports they need.** A use case is one business operation: it loads what it needs through a port, asks the domain to decide, and saves or publishes the result through a port. `application/ports.py` declares those ports, which is where `module-boundaries.md`'s layout puts them. The predecessor put repository ports under the domain instead. They belong here because a port is shaped by what a use case needs — `get`, `save`, `publish` are verbs of an operation, not of a rule — and keeping them out of the domain keeps the domain's vocabulary the business's.

**`infra/` holds the adapters and the composition root.** The HTTP routes, the repositories behind the ports, the outbound clients, the event publishers, the settings, and the one place where a concrete adapter is handed to a use case. Everything that names a vendor, a protocol or a driver lives here, and nothing below imports it, which condition 2 of `rules/module-boundaries.md` decides.

## A port is a `Protocol`

A port is declared with `typing.Protocol`, not an abstract base class. The difference is who has to know about whom. An adapter that subclasses an ABC imports the port and inherits from it; an adapter that satisfies a protocol only has the right methods, and mypy checks that it does at the line where the adapter is passed to something expecting the port. That costs nothing in a codebase that already passes `mypy --strict`, and it buys the test tree a great deal: a fake repository is a ten-line class with a dictionary inside, written in the test file, with no import from the code it stands in for and no base class to satisfy.

What the protocol does not buy is a runtime check. `isinstance(adapter, Port)` works only on a protocol marked `@runtime_checkable`, and even then checks method names, not signatures. Nothing in this architecture asks that question at runtime, and a design that needs to is looking for a registry, which is a different pattern.

## A use case is a function until it is not

The predecessor made every use case a class with its ports in the constructor and one `execute` method. That shape is right when a use case is constructed once and called many times — wired at the composition root, held by a route — and when several of its ports travel together. It is ceremony when the operation is three lines called from one place. A function that takes its ports as parameters is a use case too, the composition root binds them with `functools.partial` or a `Depends` factory, and the fundamentals value-semantics rule's parameter ceiling is the point at which the ports want to become an object.

## The composition root

Wiring happens in one place per process: the FastAPI application factory and its `Depends` factories for a service, the handler module's top level for a Lambda, the command's entry point for a CLI. [`web-services.md`](web-services.md) shows the FastAPI form. There is no dependency-injection container. `Depends` already resolves a graph per request with the lifetimes HTTP needs, constructor injection already makes every dependency visible in a signature, and a container is a second wiring language whose errors surface at start-up as a missing key instead of at type-checking as a missing argument.

## Where async belongs

`async` is a property of I/O, so it lives where the I/O does: in the adapters, and in the use cases that await them. The domain has no I/O and therefore no `await`, and a domain function marked `async` is a sign that I/O leaked into it. Keeping the domain synchronous also keeps it callable from anywhere — a test, a script, a synchronous job — without an event loop.

The cost lands on the use case, which is async because its ports are. That is the right place for it: the use case is the layer that sequences I/O, and making that sequence explicit with `await` is what lets a reader see where a request waits.

## How a failure crosses the layers

The domain raises an exception named for the invariant it refused — `InsufficientFunds`, not `ValueError("insufficient funds")` and never `Exception`, which condition 2 of [`rules/error-handling.md`](../rules/error-handling.md) decides. The use case lets it through, or catches it to decide something; it does not translate it into HTTP, because it does not know it is being called over HTTP. The adapter at the edge translates: an exception handler maps each domain exception to a status and a stable error body, logs what it did not expect, and never lets a stack trace or a query reach the caller. `web-services.md` carries the pattern. The persistence adapter is the other edge, and [`persistence.md`](persistence.md) says how a driver's error becomes something the use case can name.

## When not to abstract

The predecessor's manual ended with four sentences, and they are the most useful thing in it. Restated, and tied to what now decides each one:

- **No port for something with one implementation and no test that needs the seam.** That is condition 1 of the fundamentals YAGNI rule in substance — a second real consumer, or a test that requires the seam — and the port entry of its patterns catalogue, which names moving the code as the cheaper inversion. A use case that calls the clock does not need a `Clock` protocol until a test needs a fixed time; then it does.
- **No use case for an operation with no rule in it.** A route that reads a row and returns it has nothing for a use case to orchestrate. Let the route call the repository through its port, and add the use case the day a rule appears.
- **No layer for a future that has not arrived.** The three layers are this plugin's convention and `module-boundaries.md` enforces them; the abstractions inside them are not, and each one is added when the second consumer is.
- **Three similar lines are cheaper than the wrong abstraction.** The fundamentals duplication rule counts the third occurrence, inside one bounded context, before it calls them a duplicate, and that is the arbitration this plugin uses.

## Where this stops

**It does not choose the bounded contexts.** Which context a concept belongs to is a modelling decision; the fundamentals plugin's bounded-contexts and aggregates documents carry it, and no layout can check it.

**It does not cover jobs and agents as separate architectures.** The predecessor had a specialist each for HTTP services, jobs and LLM agents. In this layout they are three kinds of adapter at the same edge: a route, a handler, a tool. The use cases and the domain behind them are the same, and that sameness is the point of the layering. What differs at each edge — idempotency for a consumer, partial batch failure for a queue, the model-use conditions for an agent — is in [`libraries.md`](libraries.md), in the reliability plugin and in the security plugin's `reviewing-model-use`.

**It does not decide event design.** Publishing a domain event through a port is shown; the shape of the event and its contract are the contract-first rule's, in the fundamentals plugin.

**The layout is a convention.** A project that lays its code out differently keeps its layout, as the fundamentals ubiquitous-language rule says, and reads this page for the reasoning rather than the directory names.
