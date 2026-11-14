---
id: architecture
type: doc
clade: engineering
subclade: python
title: Composing Python by packages and layers
summary: The premises every choice is argued from, SOLID and inversion of control in Python's own form, extension by a new package rather than an edit, and the inside of the three layers module-boundaries declares — values and rules in the domain, use cases and their ports in application, adapters and the composition root in infra — why a port is a Protocol, where async belongs, how a failure crosses the layers, and when not to abstract at all.
references:
  - docs/module-boundaries.md
  - rules/module-boundaries.md
  - rules/immutability.md
  - rules/error-handling.md
  - docs/web-services.md
  - docs/persistence.md
---

# Composing Python by packages and layers

[`module-boundaries.md`](module-boundaries.md) decides the outside of a context: three layers, `domain`, `application` and `infra`, each its own distribution under `components/{context}/`, importing only downward, with an import graph a script proves acyclic. It says nothing about what goes inside each layer, and on purpose: a script cannot count concepts. This page is the inside. It is the predecessor's architecture manual, rewritten against the layout this plugin already enforces, and it keeps that manual's best section — when not to abstract — nearly whole.

## What the specification says

- **A port is a structural protocol**: PEP 544, *Protocols: Structural subtyping*; a class satisfies one by having the methods, with no inheritance, and a checker verifies it where the object is used.
- **Coroutines and `await`**: PEP 492 and Language Reference §8.9, *Coroutines*; an `async` function can be awaited only from another coroutine, which is why async spreads from the I/O outward.
- **Exception chaining across a layer**: Language Reference §7.8 and PEP 3134.
- **A package is a distribution with its own metadata**, and a namespace can be shared by several: PEP 621 and PEP 420. Entry points let one distribution advertise an implementation another discovers at run time: the PyPA *Entry points specification*, read through `importlib.metadata.entry_points` (Library Reference).

The community's own guidance is followed and cited where it applies: PEP 8 for names and imports, and the typing documentation's *Protocols* and *Reference* pages for how a port is declared. Where this page departs from them it says so.

## The premises every choice here is argued from

A choice between two ways of building something is decided on three premises, stated so a reader can check the argument rather than trust it:

- **Maintainability**: the next change touches as few files as possible, and a reader finds what a change needs in the place its name says.
- **Lower cyclomatic complexity**: fewer independent paths through a unit. The measured limits are the fundamentals plugin's — at most 30 statements in a function body ([`clean-code.md`](../../fundamentals/rules/clean-code.md)), nesting at most 3 deep and no boolean parameter ([`kiss.md`](../../fundamentals/rules/kiss.md)), at most 4 parameters ([`value-semantics.md`](../../fundamentals/rules/value-semantics.md)), one cohesive class ([`solid.md`](../../fundamentals/rules/solid.md), condition 1) — and this plugin adds no number of its own. In Python the unit those limits apply to is a function or a method, the file is a module that solves one problem, and `ahrena-engineering-fundamentals`'s `hooks/check-structure.py` is the tool that reports a unit past a limit.
- **No circular reference**: an import graph with no cycle, between modules and between distributions. [`rules/module-boundaries.md`](../rules/module-boundaries.md) is the rule and `hooks/check-boundaries.py` the detector.

Each section below names the premise that decides it.

## The three layers, from the inside

**`domain/` holds the rules and nothing that does I/O.** Values, entities, aggregates, domain services and the exceptions that name a broken invariant. A value is a frozen dataclass, which condition 1 of [`rules/immutability.md`](../rules/immutability.md) holds; an entity whose state moves on purpose says so on its decorator. The fundamentals domain-model rule keeps every framework, driver and transport out of the layer, and the test-first skill in the backend plugin draws the consequence: the domain is tested with no doubles at all, because there is nothing in it to double. A domain function returns a new value rather than changing the one it was handed, which is condition 2 of the same rule.

**`application/` holds the use cases and the ports they need.** A use case is one business operation: it loads what it needs through a port, asks the domain to decide, and saves or publishes the result through a port. `application/ports.py` declares those ports, which is where `module-boundaries.md`'s layout puts them. The predecessor put repository ports under the domain instead. They belong here because a port is shaped by what a use case needs — `get`, `save`, `publish` are verbs of an operation, not of a rule — and keeping them out of the domain keeps the domain's vocabulary the business's.

**`infra/` holds the adapters and the composition root.** The HTTP routes, the repositories behind the ports, the outbound clients, the event publishers, the settings, and the one place where a concrete adapter is handed to a use case. Everything that names a vendor, a protocol or a driver lives here, and nothing below imports it, which condition 2 of `rules/module-boundaries.md` decides.

## SOLID and inversion of control, the way Python expresses them

The conditions are the fundamentals plugin's [`solid.md`](../../fundamentals/rules/solid.md), and they are not restated here; neither is its arbitration, the abstraction trigger of [`yagni.md`](../../fundamentals/rules/yagni.md) that gates every condition adding structure. What this section says is how Python writes them, and where the language stops them.

- **A component depends on an abstraction it owns.** The abstraction is a `Protocol` declared by the consumer — the use case's `application/ports.py` — and never an import of the concrete adapter (PEP 544). Premise: no circular reference, since the adapter imports the port and the port imports nothing.
- **The dependency is handed in, not looked up.** Constructor injection for a use case held by the composition root; a parameter for a function. No service locator, no module-level singleton the code reaches for, no container: the dependency is visible in the signature, and `mypy --strict` checks it there. Premise: maintainability — a reader sees what a unit needs from its signature alone.
- **An interface is small.** A protocol declares the methods its one consumer calls, which is interface segregation without ceremony: two use cases that need different things from a repository declare two protocols, and the one adapter satisfies both structurally.
- **Open for extension through a seam the base declares**, which is the next section.

**Where Python's form differs from the textbook.** The usual SOLID examples are written for languages with nominal interfaces, and porting them literally is against Python's grain: an abstract base class for every port, an interface per class, a factory per object. Python's typing documentation and PEP 544 give the structural form instead, and a pattern imported from another language where the structural one would do is a finding, in the fundamentals pattern-selection rule's sense. **Where the language stops them:** a protocol is checked statically and not at run time, and nothing stops a caller passing something that only quacks; the checker is what holds the contract, which is why `rules/typing.md` requires it.

**The community guidance followed.** PEP 8 for naming, imports and the programming recommendations the error-handling rule cites; the typing documentation (*Protocols*, *Type system reference*) for how a port is written. This plugin departs from PEP 8 in one place, line length, and `docs/toolchain.md` says why.

## Extending a package without modifying it

A package is open to extension and closed to modification. To change what a component does for one product, one client or one integration, a new distribution depends on the base one and extends it through the base's public extension points; the base is not edited. Premises: maintainability, because the base keeps one behaviour and every extension is a separate, removable package; and no circular reference, because the extension imports the base and the base never imports the extension.

Python gives two extension points, and the base chooses which it offers:

- **A protocol the base accepts.** The base declares a port and takes an implementation in its constructor or its factory; the extension package ships a class satisfying the protocol, and the composition root of the product wires it in. This is the default: it is checked statically and needs nothing at run time.
- **An entry point the base reads**, when the extension is discovered at run time rather than wired by hand — a plugin, a codec, a storage backend chosen by configuration. The extension declares it in its `pyproject.toml` under `[project.entry-points."group"]`, and the base reads the group with `importlib.metadata.entry_points(group=...)` (PyPA *Entry points specification*). Discovery costs the static check, so it is used only where the set of implementations is not known when the product is built.

In one repository the base and its extensions are separate distributions, each with its own `pyproject.toml`, composed as members of one workspace; [`libraries.md`](libraries.md) names the workspace tool and argues it. `rules/module-boundaries.md` already holds the layers of a context as distributions under the PEP 420 namespace, and an extension is one more distribution in the same graph, whose direction the boundaries hook checks.

**What an extension may not do** is reach into the base's private names, patch it at import time, or subclass a concrete class to override a method the base never meant to be overridden. Each is a modification wearing an extension's clothes: it breaks when the base changes a private detail, and it puts the dependency on something the base never promised.

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
