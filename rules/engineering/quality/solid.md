---
type: rule
title: SOLID
scope: engineering/quality
enforcement: review-block
---

# Rule: SOLID

> **Type:** Unbreakable guardrail · **Scope:** Engineering — application code in any language the framework covers

## Law

> **Every module MUST satisfy the five conditions stated in this rule. Each condition is written as a detectable state with a threshold, not as a principle to interpret. An abstraction introduced to satisfy any of them MUST first pass the abstraction trigger defined in [`yagni`](yagni.md) — a principle is never sufficient justification on its own.**

What each condition prevents and where it stops paying: [the doc companion](../../../docs/engineering/quality/solid.md).

## Coverage

- **Applies to:** application code in Python, TypeScript, C#, Swift, Kotlin and Dart
- **Out of scope:** tests and fixtures (independence outranks structure), generated code, framework-mandated shapes the language forces
- **Exceptions:** none. The conditions below already carry their own thresholds; a case under the threshold is not a violation, not an exception

## Rules

### 1. One module, one actor

A module MUST NOT contain behavior that changes for two different actors.

"Actor" means the role that requests the change — finance, operations, the compliance team — not the subsystem. Two persistence methods requested by the same actor are one responsibility. A business rule and a report format requested by two different actors are two, even inside a class of ten lines.

**Detectable:** methods that split into disjoint clusters by the fields they touch. `LCOM4 > 1` marks the module as a split candidate; the actor test decides.

**Violation:** a module mixing two layers — a domain entity that also serializes itself to the database is always a violation, because the schema and the business rule never answer to the same actor.

### 2. A case enumeration appears once

When a new case is added to an existing behavior, the change MUST NOT require editing a conditional that enumerates the same discriminator in more than one place.

**Detectable:** the same `switch`, `match` or `if/elif` chain over the same type discriminator, in three or more locations. The third occurrence is the trigger — the same threshold the duplication rule uses, for the same reason.

**Under the threshold, leave it alone.** Two conditionals are cheaper to read than a polymorphic hierarchy. This condition fires on the third.

### 3. A subtype never narrows its base

A subtype MUST NOT strengthen a precondition, weaken a postcondition, raise an exception its base does not declare, or leave an inherited member unimplemented.

**Detectable, by grep:**
- `raise NotImplementedError` / `throw new NotImplementedException` in a concrete subtype
- an override whose body is empty or returns a constant where the base returns computed state
- an override that validates an argument the base accepts

Each of these is the same failure: the subtype does not honor the contract callers were promised.

### 4. No implementation leaves a member empty

An interface, protocol or abstract base MUST NOT declare a member that any implementation leaves empty, stubbed, or raising.

**Detectable:** the same signal as condition 3, read from the other end. An empty implementation is the interface telling you it carries a member that does not belong to every implementer. Split the interface at that member.

### 5. Dependencies point inward

A module in an inner layer MUST NOT import from an outer layer. The order is domain, then application, then infrastructure — imports travel toward the domain and never away from it.

**Detectable:** the import graph. A cycle between modules is a violation regardless of direction. Language-specific enforcement lives in the module-boundary rule for that language; for Python it is [`module-boundaries`](../backend/python/module-boundaries.md).

## Arbitration with simplicity

These five conditions push toward structure. [`kiss`](kiss.md) and [`yagni`](yagni.md) push against it. The conflict is real and this rule does not win it by default.

**The abstraction trigger in [`yagni`](yagni.md) is the arbiter.** An abstraction introduced to satisfy a condition here is justified by a second real consumer or a required test seam. An anticipated consumer is not a consumer. Where the trigger fails, the condition does not fire — and an over-abstracted module is a violation of `kiss`, not a success of this rule.

Conditions 1, 3 and 4 describe states a module is already in, so they cost nothing to satisfy and the trigger rarely applies. Conditions 2 and 5 introduce structure, so the trigger always applies.

## Examples

### Correct

```python
# One actor per module. The entity answers to the business;
# the mapper answers to the schema owner.
@dataclass(frozen=True)
class Invoice:
    invoice_id: UUID
    amount_cents: int

    def is_overdue(self, on: date) -> bool:
        return self.due_date < on


class InvoiceMapper:              # separate module, outer layer
    def to_row(self, invoice: Invoice) -> dict: ...
```

```python
# Condition 4: every implementation fills every member.
class Clock(Protocol):
    def now(self) -> datetime: ...

class SystemClock:
    def now(self) -> datetime: return datetime.now(UTC)

class FrozenClock:
    def __init__(self, at: datetime) -> None: self._at = at
    def now(self) -> datetime: return self._at
```

### Incorrect

```python
# Condition 1: two actors in one module.
@dataclass
class Invoice:
    def is_overdue(self, on: date) -> bool: ...   # business
    def save(self) -> None:                        # schema owner
        db.execute("INSERT INTO invoices ...")
```

```python
# Condition 3 and 4: the subtype does not honor the contract.
class ReadOnlyRepository(Repository):
    def save(self, entity: Entity) -> None:
        raise NotImplementedError("read-only")
```

```python
# Condition 5: the domain reaches outward.
# file: domain/invoice.py
from infra.postgres import connection      # forbidden
```

## Automated validation

| Condition | Check | Tool |
|---|---|---|
| 1 | `LCOM4 > 1` marks a split candidate for review | SonarQube; `radon` for Python |
| 2 | Third occurrence of the same discriminator chain | `jscpd` for TS/JS; `pylint R0801` for Python; review |
| 3, 4 | `NotImplementedError` / empty override in a concrete type | `ruff`, `oxlint`, custom AST check |
| 5 | Import cycles and inward-only direction | `import-linter` for Python; `dependency-cruiser` for TS |

- **When:** pre-commit for the grep-able conditions; CI on every pull request for the graph and metric conditions
- **Metric:** zero import cycles; zero concrete members left unimplemented; every split candidate raised by the metric either split or answered in review with the actor test
