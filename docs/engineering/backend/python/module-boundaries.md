---
type: doc
title: Python module boundaries
scope: engineering/backend/python
---

# Doc: Python module boundaries

> **Type:** Reference manual · **Scope:** Engineering — Backend: Python packaging, namespaces, and breaking import cycles

## Overview

The rule states the constraints. This manual shows the layout that satisfies them, explains why the distributions are split, and gives the three ways to break a cycle. Read it when setting up a new context, or when `import-linter` fails and the fix is not obvious.

## Context

- **Domain:** Python package structure in a multi-context repository
- **Audience:** backend engineers and agents implementing Python
- **Update:** on a change to the layer layout, the namespace strategy, or the enforcement tooling

## Content

### The layout

```
components/                        # PEP 420 namespace root, no __init__.py
├── commons/                       # shared kernel, depends on no context
│   ├── domain/
│   ├── application/
│   ├── infra/
│   └── pyproject.toml
└── {context}/
    ├── domain/                    # entities, value objects, domain services
    ├── application/               # use cases; ports.py declares the contracts
    ├── infra/                     # adapters: db, http, queue, sdk
    └── pyproject.toml
```

### Why the distributions are split

The reason is dependency inheritance, and it is concrete rather than architectural.

A shared kernel that ships domain, infrastructure and agent code as one distribution forces every consumer to install everything. A service that needs only the entity definitions pulls in the database driver, the cloud SDK, the telemetry client and the model runtime. The install grows, the container grows, the vulnerability surface grows, and the dependency resolver gains conflicts that have nothing to do with the code being written.

Split into `commons-domain`, `commons-infra` and `commons`, each consumer installs the set it uses. The domain kernel stays small enough that depending on it is not a decision.

The split also makes the dependency direction enforceable by the packaging system rather than by convention: `commons-domain` cannot import from `commons-infra`, because `commons-domain` does not depend on it and the import fails at install time, not at review time.

### PEP 420 namespaces

Namespace levels carry no `__init__.py`. With `components/` as the namespace root, the import path `commons.infra.agents` resolves to `components/commons/infra/agents`, and separate distributions contribute into the same namespace without colliding.

The build configuration makes the root explicit:

```toml
[tool.hatch.build.targets.wheel]
sources = ["../.."]      # components/ becomes the namespace root
```

Adding an `__init__.py` at a namespace level breaks this: the level stops being a namespace and the first distribution to claim it shadows the rest.

### Declaring the direction where it is read

Record the direction beside the dependency that needs explaining:

```toml
dependencies = [
    # OTel token-usage telemetry emitted by the agent runtime. commons-infra is
    # foundational infra, not a bounded context, so the kernel may depend on it;
    # the dependency is acyclic: commons-infra -> commons-domain, never back.
    "commons-infra",
]
```

A constraint recorded only in an architecture document is invisible at the moment someone adds a dependency. Recorded here, it is in front of the person and the tool that touch it.

### Breaking a cycle

A cycle means a responsibility sits on the wrong side of a boundary. There are three fixes, in order of preference.

**1. Introduce a port.** The most common case: `application` needs something `infra` has. Declare the contract in `application/services/ports.py`, implement it in `infra`, and wire at composition time. The dependency reverses and the cycle disappears.

**2. Extract the shared concept.** When two modules genuinely need each other, they usually share a third concept neither owns. Extract it — often into `domain` or the shared kernel — and have both depend on it.

**3. Merge the modules.** When two modules change together every time, the boundary between them is imaginary. Merge them and stop paying for the separation.

**What is not a fix:** moving the import inside a function. The import graph stops reporting the cycle and the coupling remains. The defect survives and the detector no longer sees it, which is strictly worse than the cycle it replaced. The same applies to `TYPE_CHECKING` guards used to silence a real runtime dependency — legitimate for annotations only.

### Enforcement

```ini
# .importlinter
[importlinter]
root_packages = commons, financial, registration

[importlinter:contract:layers]
name = Layers point inward
type = layers
layers =
    infra
    application
    domain
containers =
    commons
    financial
    registration

[importlinter:contract:no-cycles]
name = No cycles between top-level packages
type = independence
modules = financial, registration
```

`import-linter` runs in CI and fails the build. `ruff` handles the per-file checks at pre-commit: `F401` for unused imports, `TID252` to ban relative imports that cross a package boundary.

## Restrictions

- No `__init__.py` at a namespace level
- No deferred import used to resolve a cycle
- No layer sharing a distribution with another layer
- No `pyproject.toml` whose cross-package dependencies carry no direction statement

## Glossary

| Term | Meaning |
|---|---|
| Namespace package | PEP 420 package without `__init__.py`, contributed to by several distributions |
| Distribution | An installable unit with its own `pyproject.toml` and dependency set |
| Port | A Protocol declared by an inner layer stating what it needs |
| Container | In `import-linter`, the package whose subpackages the layer contract orders |

## References

- [`module-boundaries`](../../../../rules/engineering/backend/python/module-boundaries.md) — the enforceable constraints
- [`solid`](../../quality/solid.md) — condition 5, of which this is the Python instance
- PEP 420 — implicit namespace packages
