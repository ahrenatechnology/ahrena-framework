---
name: diagnosing-database
description: Use when a database misbehaves - a query that got slow, a request waiting on a lock or a deadlock, a migration that failed or left the schema half-changed - and the cause has to be found before anything is fixed. Reproduces the symptom, reads the database's own evidence (the plan, the lock and activity views, the migration tool's state) with read-only statements, names the first cause with its evidence, and proposes the fix and where it lands. It diagnoses; it runs no statement that changes data or schema.
type: skill
clade: engineering
subclade: database
references:
  - docs/database-capabilities.md
  - docs/indexing.md
  - docs/transactions.md
  - rules/index-coverage.md
  - rules/transaction-boundaries.md
---

# Diagnosing a database

The output is one diagnosis: the symptom reproduced, the first cause, the evidence that shows it, and the fix with where it lands. The read-only statement for each step on each database is in `references/diagnostics.md`, each with the page of the database's documentation behind it.

## 1. Pin the symptom

From the report, write down: which database and version, which environment, which statement or endpoint, since when, and what changed around then (a deploy, a migration, a data load, a new tenant). Read the deploy and migration history with `git log` on the migrations directory. Output: one sentence of what is wrong, where and since when.

A report that names no statement, no time and no environment cannot be diagnosed; ask for them once, in one batch.

## 2. Reproduce it

Run the statement, or the integration test that exercises it, against a database the caller allows reading — a local copy, staging, or a read replica — and see the symptom. A symptom that does not reproduce is written down as such, with what was tried, before any cause is named: a cause for a symptom never seen is a guess.

Read-only only. `EXPLAIN ANALYZE` executes the statement ([PostgreSQL: Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html#USING-EXPLAIN-ANALYZE)), and a `SELECT` can still write, through a data-modifying `WITH` or a volatile function. So every statement runs inside a read-only transaction that ends in `ROLLBACK`: `BEGIN TRANSACTION READ ONLY` on PostgreSQL, which refuses writes and `EXPLAIN ANALYZE` of a write ([SET TRANSACTION](https://www.postgresql.org/docs/current/sql-set-transaction.html)), and `START TRANSACTION READ ONLY` on MySQL ([START TRANSACTION](https://dev.mysql.com/doc/refman/8.4/en/commit.html)). A statement with `FOR UPDATE` or `FOR SHARE` takes row locks, so it gets plain `EXPLAIN` only. Elsewhere, only a statement `references/diagnostics.md` lists as one that cannot write runs.

## 3. Read the database's evidence for the kind of symptom

**A slow query.** Read the plan (`references/diagnostics.md`, "Slow query") and find the node that reads the most rows for what it returns: a full scan of a large table, a nested loop over a large inner side, a sort with no index, an index on the wrong leading column. Compare with the indexes at the head and with [`docs/indexing.md`](../../docs/indexing.md). Where the plan changed without a code change, compare the statistics' age and the table's growth.

**A lock or a deadlock.** Read who waits on whom (`references/diagnostics.md`, "Locks") and what the blocker is running and since when. The recurring causes: a transaction left open by an error path, against [`rules/transaction-boundaries.md`](../../rules/transaction-boundaries.md) condition 4; a migration taking a lock that blocks every reader, such as the many forms of `ALTER TABLE` that take `ACCESS EXCLUSIVE` on PostgreSQL ([Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-TABLES)); an index built without `CONCURRENTLY`; two use cases changing the same two roots in opposite order.

**A failed migration.** Read the migration tool's own state table, and the schema as it is (`references/diagnostics.md`, "Failed migration"). On MySQL, DDL commits implicitly, so a migration that failed after its first statement left that statement applied ([Implicit Commit](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html)). On PostgreSQL, a failed concurrent index build leaves an `INVALID` index ([CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY)).

Output: the evidence, quoted from the database's output with no row data in it.

## 4. Name the first cause

The first cause is the earliest thing that, had it not happened, would have prevented the symptom. A lock timeout is a symptom; the transaction that held the lock is the cause; the error path that left it open is the first cause. State it with the evidence from step 3 that shows it, and say what would disprove it.

## 5. Propose the fix, and where it lands

Name the change, the file it goes in and who writes it: a migration (an index, built without locking writes), an adapter or the unit of work (the transaction guard), a query. Name the test that would have caught it, so the fix arrives with its detector. Where the fix is an operation on a running database — terminating a blocking session, dropping an invalid index, marking a migration — write it as a step for the database's owner to run; do not run it.

## When this skill does not apply

**Designing what does not exist yet.** That is `skills/designing-persistence/SKILL.md`.

**Reviewing a change.** That is `skills/reviewing-persistence/SKILL.md`.

**The database's host.** An instance out of storage, a failover, a parameter group, a network path to the database: the cloud plugin's diagnosis (`ahrena-engineering-aws:diagnosing-aws-deployments` and its equivalents).

**A failed deployment pipeline** that happens to run migrations: the pipeline is `ahrena-engineering-devops`'s; this skill takes over once the failure is the migration's own.
