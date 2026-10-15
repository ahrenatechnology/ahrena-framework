---
id: reconciliation
type: rule
clade: engineering
subclade: data
title: A mart reconciles to its source
statement: No mart ships without a reconciliation tying its figures to the source its contract pinned; a mart that cannot reconcile to its source is defective, not done.
enforcement: judgment
references:
  - docs/reconciliation.md
---

# A mart reconciles to its source

## The source gate

A mart — the data product the gold layer serves — ships only with a reconciliation that ties its figures back to the source the data contract pinned. The reconciliation is a check that reproduces the mart's key measures from the source and asserts they agree within a stated tolerance: a row count, a sum, a distinct-key count, a period total. A mart with no such check is defective the moment a transform drops or double-counts a row, and it looks finished until someone downstream trusts a wrong number.

The subject is agreement, not shape. A mart can pass its contract test — the right columns, the right types, the declared keys — and still contain figures that do not tie to the source, because a schema promise says nothing about whether the values are right. That gap is exactly what reconciliation closes, and nothing a contract test decides reaches it. `docs/reconciliation.md` works through why the two checks are different and why the content check cannot be folded into the shape one.

Three terms, used in the same sense throughout.

- **A mart** is a gold-layer product built for a consumer: a table, view or extract whose figures someone reads and acts on. An intermediate silver model consumed only by the next transform is not a mart.
- **Reconciled** means a check recomputes the mart's key measures from the pinned source and asserts agreement within a declared tolerance, and that check is green before the mart ships.
- **The source** is the upstream the data contract pinned for this mart — the bronze landing or the external system of record — not another derived layer, because reconciling a derivation against a derivation proves only that two transforms agree, not that either is right.

## Conditions

1. A reconciliation check exists for the mart and recomputes at least its primary measure and its row or key count from the pinned source. Decided by a reviewer reading the mart's test suite: a mart whose only tests assert schema and nullability has no reconciliation.
2. The reconciliation reads the source the contract pinned, not an intermediate derived layer. Decided by a reviewer reading what the check queries against.
3. The reconciliation is green, within its stated tolerance, before the mart layer opens. Decided by a reviewer: an exact-match tolerance passes only on equality, and a non-zero tolerance states the figure and the reason it is not zero.

## Where this stops

**It is not a data-quality rule.** Freshness, uniqueness and nullability are the expectations layer's subject, and they check a dataset against its own declared invariants. Reconciliation checks a mart against a different dataset — its source — so a mart can pass every quality expectation and still fail to reconcile. The two layers are complementary, not substitutes.

**It does not reach a non-mart.** A silver model consumed only by the next transform, a scratch table, a one-off exploration — none is a product a consumer reads, so none owes a reconciliation. The rule reaches the gold layer's products, and the test of a mart is whether a figure in it is trusted outside the pipeline.

**It does not fix the tolerance.** Exact agreement is the right answer for counts and discrete sums; a documented tolerance is the right answer where rounding, late-arriving data or a sampled source makes exactness a fiction. The rule requires that the tolerance be stated and justified, not that it be zero, and which figure is correct is the mart owner's judgment made once.

**This rule declares judgment rather than a hook, and the reason is not effort.** Which dataset is a mart, which source its contract pinned, how its measures are recomputed and what tolerance is defensible are facts about one project's data that no script in this repository can read. A hook guessing them would be confidently wrong on the first project that arranged its warehouse differently. The rule takes the judgment route, its statement is injected, and a reviewer is the gate.
