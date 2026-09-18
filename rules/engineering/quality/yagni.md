---
type: rule
title: YAGNI
scope: engineering/quality
enforcement: review-block
---

# Rule: YAGNI

> **Type:** Unbreakable guardrail · **Scope:** Engineering — every change to application code

## Law

> **A change MUST implement what the accepted requirement needs and nothing beyond it. Introducing an extension point, an interface, a configuration flag, a parameter, or a generalization for a requirement that is not in the current accepted scope is FORBIDDEN. This rule defines the abstraction trigger, which is the single arbiter every other structural rule in the framework defers to.**

## Coverage

- **Applies to:** every change to application code, in every language the framework covers
- **Bound agents:** every agent that writes or reviews code
- **Exceptions:** none. The abstraction trigger below is not an exception mechanism — it is the condition under which the abstraction was never a violation in the first place

## The abstraction trigger

This clause is canonical. [`solid`](solid.md), [`kiss`](kiss.md) and every language-specific structural rule cite it rather than restate it.

> **An abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam. An anticipated consumer is not a consumer. A test you intend to write is not a test.**

Three consequences follow, and they are the whole rule in practice:

1. **An interface with one implementation and no test seam is a violation.** It is indirection with no reader and no caller — the cost is paid now and the benefit is hypothetical.
2. **The second consumer resets the question, the third settles it.** Two call sites may justify a shared function. Three occurrences of the same knowledge trigger extraction outright, which is the same threshold the duplication rule uses, for the same reason: two points do not establish a direction, three do.
3. **"We will need it" is not evidence.** An accepted requirement is evidence, and it carries an issue number. Cite it or drop the abstraction.

## Rules

### 1. No speculative extension points

A change MUST NOT add a parameter, hook, strategy slot, or plugin point that the accepted requirement does not exercise.

**Detectable:** a new public symbol with zero callers inside the same pull request. A parameter whose only argument across the codebase is its default value.

### 2. No dead configuration

A configuration option MUST NOT ship without a caller that sets it to something other than its default.

**Detectable:** a settings key absent from every environment file and every call site. Feature flags are covered: a flag with no rollout plan and no owner is dead configuration wearing a different name.

### 3. No generalization before the second case

A function MUST NOT be generalized over a dimension that has one value.

A parser that takes a `format` argument and supports one format, a repository generic over an entity type with one entity, a factory that builds one thing — each is the same shape. Generalize when the second case arrives.

### 4. Requirements are cited, not remembered

When a change includes structure for a requirement beyond the immediate one, the change MUST cite the accepted requirement by issue number, in the code or in the pull request body.

An uncited future requirement is an assumption. This rule does not forbid building ahead of the current task — it forbids doing so on memory.

## Arbitration with structure

[`solid`](solid.md) pushes toward structure and this rule pushes against it. Written separately and without arbitration, the two produce contradictory review feedback and an agent follows whichever it loaded first.

The resolution is asymmetric and deliberate: **the abstraction trigger gates the structural conditions, not the reverse.** A SOLID condition that would introduce an abstraction fires only after the trigger passes. Conditions that describe a state a module is already in — mixed actors, a subtype that narrows its base, an interface member nobody implements — are not gated, because satisfying them removes structure rather than adding it.

Where this rule and structure genuinely disagree, the cheaper mistake wins. Removing a needed abstraction later is a refactor with tests. Removing an unneeded one that three modules already import is a migration.

## Examples

### Correct

```python
# One format, one function. The second format changes this,
# and that change is cheap.
def parse_statement(raw: str) -> Statement: ...
```

```python
# The seam exists because a test today requires it.
class Clock(Protocol):
    def now(self) -> datetime: ...

def test_expiry_uses_the_clock() -> None:
    assert is_expired(token, clock=FrozenClock(at=CUTOFF))
```

```python
# Structure ahead of the immediate task, with the requirement cited.
# Second payout provider is accepted scope (#412).
class PayoutProvider(Protocol): ...
```

### Incorrect

```python
# One format, a dimension invented for it.
def parse_statement(raw: str, fmt: str = "ofx") -> Statement:
    if fmt == "ofx":
        return _parse_ofx(raw)
    raise ValueError(f"unsupported: {fmt}")
```

```python
# One implementation, no test seam. Indirection with no reader.
class InvoiceRepositoryInterface(Protocol):
    def save(self, invoice: Invoice) -> None: ...

class InvoiceRepository:
    def save(self, invoice: Invoice) -> None: ...
```

```python
# Dead configuration: nothing sets it, nothing plans to.
ENABLE_EXPERIMENTAL_LEDGER = os.getenv("ENABLE_EXPERIMENTAL_LEDGER", "false")
```

## Automated validation

- **Tool:** dead-code and unused-export detection (`ruff` F401/F811 and `vulture` for Python, `oxlint` and `knip` for TypeScript); a check for public symbols added with zero in-repo callers; review against the abstraction trigger
- **When:** pre-commit for dead code; pull-request review for the trigger, which needs judgment a linter cannot supply
- **Metric:** zero interfaces with a single implementation and no test seam; zero configuration keys with no non-default caller; every forward-looking abstraction carries an issue number
