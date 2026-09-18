---
type: rule
title: KISS
scope: engineering/quality
enforcement: review-block
---

# Rule: KISS

> **Type:** Unbreakable guardrail · **Scope:** Engineering — every change to application code

## Law

> **The shape of a solution MUST match the shape of the problem. Every threshold below is a detectable state with a number attached; crossing one is a review block. Where an abstraction is the proposed remedy, the abstraction trigger in [`yagni`](yagni.md) decides whether it is allowed.**

"Keep it simple" is unenforceable and this rule does not state it. What follows are the measurable conditions that simplicity resolves to.

## Coverage

- **Applies to:** application code in every language the framework covers
- **Out of scope:** generated code, vendored dependencies, and tests, where explicitness outranks concision
- **Exceptions:** none. A threshold crossed with a stated reason is answered in review, not exempted — and the answer belongs in the code as a `WHY:` comment

## Rules

### 1. Thresholds

| Condition | Threshold |
|---|---:|
| Cyclomatic complexity, per function | ≤ 10 |
| Nesting depth | ≤ 3 |
| Function parameters | ≤ 4 |
| Return points in a function over 20 lines | ≤ 4 |

The parameter cap is shared with the input-DTO rule, which owns what to do once it is crossed: the parameters become an object.

These numbers are review triggers, not proofs. A function at complexity 11 is not broken; it is a function whose author now owes the reviewer a sentence. A function at complexity 30 is a defect.

### 2. Indirection earns its place

A layer of indirection MUST have a reader who benefits from it.

A wrapper that forwards every call unchanged, a service that only calls a repository, a factory that constructs one type with no parameters — each adds a hop to every reader and returns nothing. Where the remedy is a new abstraction rather than deletion, the abstraction trigger in [`yagni`](yagni.md) applies.

### 3. Clever code is a defect

An expression MUST be readable by someone who did not write it, without running it.

Concretely: no nested ternaries, no comprehension with more than two clauses, no arithmetic that depends on operator precedence a reader has to look up, no reliance on truthiness of a non-boolean where the check is about emptiness.

The measure is not personal taste. If explaining the line in review takes longer than rewriting it, rewrite it.

### 4. Non-obvious decisions are recorded, not commented away

Where a simple solution was rejected for a real reason — a measured performance constraint, a platform behavior, a specification requirement — the reason MUST appear as a `WHY:` comment naming the constraint.

This is the one place where added complexity is settled rather than argued. A `WHY:` comment that states a constraint is documentation. A comment that restates the code is noise, and the clean-code rule removes it.

## Examples

### Correct

```python
# WHY: integer arithmetic on cents avoids the float rounding error
# that produced the 1-cent reconciliation drift in #318.
fee_cents = amount_cents * 15 // 1000
```

```python
def settle(invoice: Invoice) -> Receipt:
    if invoice.is_paid:
        return invoice.receipt
    payment = charge(invoice)
    return record(invoice, payment)
```

### Incorrect

```python
# Nested ternary: unreadable without tracing it.
status = "paid" if p else ("late" if d < today else "open" if a else "void")
```

```python
# Indirection with no reader: every method forwards unchanged.
class InvoiceService:
    def __init__(self, repo: InvoiceRepository) -> None:
        self._repo = repo
    def save(self, invoice): return self._repo.save(invoice)
    def get(self, invoice_id): return self._repo.get(invoice_id)
```

```python
# Six parameters, four nesting levels, no reason recorded.
def process(a, b, c, d, e, f):
    if a:
        for x in b:
            if x in c:
                while d:
                    ...
```

## Automated validation

- **Tool:** `ruff` (C901 complexity, PLR0913 parameter count) and `radon` for Python; `oxlint` complexity and depth rules for TypeScript; SonarQube cognitive complexity across languages
- **When:** pre-commit for the threshold checks; pull-request review for conditions 2 and 3, which need a reader rather than a parser
- **Metric:** zero functions above the thresholds without a `WHY:` comment naming the constraint
