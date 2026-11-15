---
id: transaction-boundaries
type: rule
clade: engineering
subclade: database
title: A Transaction Opens at the Use-Case Edge and Always Ends
statement: Every write runs in a transaction opened once at the use-case edge, not in an adapter, ending in commit or rollback, changing one aggregate root.
enforcement: judgment
references:
  - docs/transactions.md
  - docs/database-capabilities.md
---

# A Transaction Opens at the Use-Case Edge and Always Ends

A write to the database happens inside a transaction that the use case opens as its unit of work, that ends in commit on success and rollback on any failure, and that changes one aggregate root. Why, and what each database makes atomic and asks the caller to retry, are in [`docs/transactions.md`](../docs/transactions.md).

The conditions carry the quality rubric's identifiers (`TRX-n`, ahrenatechnology/ahrena-framework#323) and are decided by review, through `skills/reviewing-persistence/SKILL.md`, until the rubric's detectors land.

## Conditions

1. **Every write to the database runs inside a transaction, including a single-row write that also writes history.** (`TRX-1`) Decided by review and by an integration test that makes the second write fail and finds the first gone.
2. **The transaction is opened once, at the use-case edge, through a unit of work; no adapter body issues `BEGIN`, `COMMIT` or `ROLLBACK`, or the driver's equivalent, on its own.** (`TRX-2`) Decided by review of the adapters.
3. **A transaction changes one aggregate root; an effect on another root leaves as an event recorded in the same transaction.** (`TRX-3`) Decided by review of the use case.
4. **Every transaction ends in commit on success and in rollback on any failure — an expected exception, an unexpected one, and a failure returned as a value — and none is left open.** (`TRX-4`) Decided by review of the unit of work and by a test that forces each kind of failure and finds the rollback and no transaction pending.

## Where this stops

**Reads.** A read-only query needs no unit of work unless it needs one snapshot across several reads.

**Migrations.** A migration is a transaction of its own, opened by the migration tool; condition 2 reads application adapters. A statement that cannot run in a transaction, such as PostgreSQL's concurrent index build, is its own migration.

**Single-document and single-item stores.** Where the aggregate and its history fit in one document or one item, the store's single-write atomicity is the transaction; condition 1 holds without a transaction API.

**Distributed work.** A saga across services is a design across components, not a database transaction.
