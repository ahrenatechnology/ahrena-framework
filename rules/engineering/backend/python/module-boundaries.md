---
type: rule
title: Python module boundaries
scope: engineering/backend/python
enforcement: ci-block
consults:
  - docs/engineering/backend/python/module-boundaries
relates:
  - rules/engineering/quality/solid
---

# Rule: Python module boundaries

> **Type:** Unbreakable guardrail · **Scope:** Engineering — Backend: Python package and import structure

## Law

> **Every architectural layer MUST be a distributable Python package with its own `pyproject.toml` and an explicitly declared dependency direction. Imports MUST travel inward — infrastructure to application to domain — and never outward. A cycle between modules is FORBIDDEN regardless of direction, and CI MUST reject it.**

## Coverage

- **Applies to:** every Python package in a repository that adopts the framework
- **Out of scope:** single-file scripts, notebooks, and `scripts/` tooling that no package imports
- **Exceptions:** none. A dependency that appears to require a cycle is a missing port; introduce the port

## Rules

### 1. A layer is a package, not a folder

Each layer ships as its own distribution with its own `pyproject.toml` and its own dependency set.

```
components/{context}/
├── domain/        # no framework imports at all
├── application/   # ports.py declares the contracts
└── infra/         # adapters implement them
```

The separation is not cosmetic. When `domain` and `infra` share one distribution, every consumer of the domain inherits the infrastructure's dependency tree — the database driver, the cloud SDK, the telemetry client — whether it touches them or not. Splitting the distributions keeps each dependency set off the other's consumers.

### 2. `components/` is a PEP 420 namespace root

Namespace levels carry **no** `__init__.py`. The package path resolves through the namespace root, so `commons/infra/agents` resolves to `components/commons/infra/agents`.

### 3. The dependency direction is declared in package metadata

Each `pyproject.toml` MUST state, in its `description` or in a comment beside the dependency it explains, which direction the dependency runs and that it is acyclic.

This is the rule's load-bearing requirement. A constraint recorded only in a document is invisible at the moment someone adds a dependency. Recorded beside the dependency, it is read by the person and the tool that touch it.

### 4. No cycles

A cycle between modules is a violation whether it crosses layers or not, and whether it is resolved at runtime by a deferred import or not.

A deferred import inside a function is not a fix. It hides the cycle from the import graph while preserving the coupling that made the cycle, which is worse than the cycle: the defect stays and the detector stops seeing it.

### 5. One concept per module

- One module, one concept: `create_entity_service.py`, `ports.py`, `entity.py`
- Modules private to their package are prefixed with `_`: `_lifecycle.py`
- Tests sit beside the module they cover: `create_entity_service.py` and `create_entity_service_test.py`

## Relationship to the neighbouring rules

Rule 1 and the import direction are the Python instance of the fifth condition in [`solid`](../../quality/solid.md) — dependencies point inward. That condition states the principle once; this rule states how Python enforces it. Neither restates the other.

## Examples

### Correct

```toml
# components/commons/pyproject.toml
[project]
name = "commons"
description = """
Shared kernel. Importable by every context's application subtree and by the
deployables; depends on no context. commons/ is the package root, imported as
commons.*; components/ is the namespace root.
"""
dependencies = [
    # The dependency is acyclic: commons-infra -> commons-domain,
    # never back to this kernel.
    "commons-infra",
]

[tool.hatch.build.targets.wheel]
# commons and commons/infra are PEP 420 namespaces (no __init__.py).
# sources = ["../.."] makes components/ the namespace root.
sources = ["../.."]
```

```python
# application/services/ports.py — the contract lives in the inner layer
from typing import Protocol

class InvoiceRepository(Protocol):
    def save(self, invoice: Invoice) -> None: ...

# infra/postgres/invoice_repository.py — the adapter depends inward
from application.services.ports import InvoiceRepository
```

### Incorrect

```python
# domain/invoice.py — the domain reaches outward
from infra.postgres import connection
```

```python
# A deferred import hiding a cycle. The coupling is intact;
# only the detector has been silenced.
def build_report() -> Report:
    from application.services.report_service import ReportService
    return ReportService().run()
```

```toml
# One distribution for every layer: every domain consumer now
# inherits sqlalchemy and boto3.
[project]
name = "financial"
dependencies = ["sqlalchemy", "boto3", "pydantic"]
```

## Automated validation

- **Tool:** `import-linter` with a layered contract per bounded context, plus a `forbidden` contract for the cross-layer imports; `ruff` (TID252 relative-import bans, F401) at pre-commit
- **When:** `import-linter` runs in CI on every pull request and fails the build on any cycle or outward import; `ruff` runs at pre-commit
- **Metric:** zero import cycles; zero outward imports; every `pyproject.toml` carries its direction statement
