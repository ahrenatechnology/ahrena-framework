---
id: reconciliation
type: doc
clade: engineering
subclade: data
title: Why a mart reconciles to its source
summary: Why a schema contract test cannot catch a wrong figure, what reconciliation adds that data-quality expectations do not, why the source must be the pinned one and not a derived layer, and where the gate deliberately does not reach.
references:
  - rules/reconciliation.md
  - ahrena-engineering-fundamentals:docs/contract-first.md
---

# Why a mart reconciles to its source

This is the companion to [`rules/reconciliation.md`](../rules/reconciliation.md). The rule states that no mart ships without a reconciliation tying its figures to its pinned source; this explains why that check is distinct from the two checks that look like they already cover it — the schema contract test and the data-quality expectations — and where the gate stops.

## The figure a contract test cannot see

A data contract is a promise about shape: these columns, these types, these keys, this freshness. A contract test verifies that promise, and [`ahrena-engineering-fundamentals:docs/contract-first.md`](../../fundamentals/docs/contract-first.md) argues why that contract is authored and not generated. All of that is about the shape of the mart, and none of it is about whether the numbers in it are right.

A mart can satisfy its contract perfectly and be wrong. A join that fans out doubles every row; a filter that is one predicate short drops a segment; a late-arriving partition is silently excluded. In each case the columns, the types and the keys are exactly as the contract declares — the test is green — and the revenue total is twice what it should be. The contract test is structurally incapable of catching this, because the defect is in the values and the contract makes no claim about the values.

This is a dependency-direction point, the same one the contract-first argument makes. The contract says what the consumer may rely on about the mart's structure. Reconciliation says the mart's content still ties back to the truth upstream. They answer different questions, and a green contract test is not evidence for the question reconciliation asks.

## What reconciliation adds that quality expectations do not

The expectations layer — freshness, uniqueness, nullability, accepted ranges — is often mistaken for the content check, because it does look at values. But every expectation is a statement about a dataset against its *own* declared invariants: this column is never null, this key is unique, this timestamp is recent. None of them compares the dataset against a different dataset.

Reconciliation is exactly that comparison. It recomputes the mart's key measures from the source and asserts agreement. A mart can pass every expectation — no nulls, unique keys, fresh data — and still fail to reconcile, because a doubled row count violates no single-dataset invariant. The expectations prove the mart is internally well-formed; reconciliation proves it is externally faithful. A pipeline that runs the first and skips the second has checked that its output is tidy without checking that it is true.

## Why the source is the pinned one, not a derived layer

The rule insists the reconciliation reads the source the contract pinned — the bronze landing or the external system of record — and not an intermediate silver model. The reason is that reconciling a derivation against another derivation proves only that two transforms agree with each other, which they will, because the second was built from the first. Two wrong numbers that share an origin reconcile cleanly and tell you nothing.

The value of a reconciliation is the independence of the two sides. The source is the side the pipeline did not compute; recomputing the measure a second way, from that independent side, is what makes agreement meaningful. Pinning the source in the contract is what fixes which dataset is allowed to be that independent truth, so the first layer of the build is where the reconciliation's target is decided, not the last.

## Why the tolerance is stated, not zero

Exact agreement is the honest answer for counts and discrete sums, and the rule's default is equality. But some sources make exactness a fiction: a sampled upstream, a currency conversion that rounds, a late-arriving stream where the mart and the source are read microseconds apart. Forbidding a tolerance there would push teams to either skip the reconciliation or fake the equality, both worse than an honest allowance.

So the rule requires the tolerance to be stated and justified rather than requiring it to be zero. A reconciliation that agrees within 0.01 per cent because of rounding is a real check; one that agrees within 10 per cent is a check that has been widened until it cannot fail, which is the same failure byte-equality avoids on the shape side. The number is the mart owner's judgment, made once and visible, not a dial quietly turned until the build goes green.

## Where this stops

**It does not pick a warehouse or a test tool.** dbt tests, Great Expectations, a hand-written SQL assertion and a notebook check all satisfy the rule, and which one a project uses is stated in its component map. This doc argues that the content check must exist and be independent; the project supplies the mechanism.

**It does not cover the transform itself.** How bronze becomes silver becomes gold — the modelling, the grain, the slowly-changing dimensions — is the medallion layer's subject. Reconciliation is the gate at the end that proves the transform did not lose or duplicate the truth, not a method for writing the transform.

**It does not reach a mart with no numeric truth to tie back.** A mart that is a pure relabelling or a filtered passthrough with no aggregation has little to reconcile beyond a row count, and the rule's first condition degrades to exactly that. The richer the aggregation, the more the reconciliation earns its place.

**It is one gate, not the whole of data correctness.** A mart that reconciles can still answer the wrong question, model the wrong grain, or serve a consumer a measure defined differently from how they read it. Reconciliation catches the class of defect where the figures silently stop tying to the source, which is the one most often shipped looking finished; it is a floor, not a proof of correctness.
