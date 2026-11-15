---
id: transactions
type: doc
clade: engineering
subclade: database
title: Transaction Boundaries
summary: Why a transaction opens once at the use-case edge as a unit of work, always ends in commit or rollback, changes one aggregate root, and what each database makes atomic, isolates by default and asks the caller to retry — the companion of the transaction-boundaries rule.
references:
  - rules/transaction-boundaries.md
  - docs/database-capabilities.md
  - docs/entity-history.md
---

# Transaction Boundaries

This is the rationale behind [`rules/transaction-boundaries.md`](../rules/transaction-boundaries.md). A transaction is the database's promise that a group of writes happens entirely or not at all. The promise is only as good as the boundary drawn around it: drawn too narrow, an entity is saved without its history; drawn in the wrong place, two adapters each commit half of one decision; left open, a connection holds locks nobody will release.

## One unit of work, opened at the use-case edge

A use case loads an aggregate, asks it to decide, and saves what it decided. That save, the entity, its history row, and the event it emits, is one unit. So the transaction opens once, where the use case starts, and closes where it ends. An adapter (a repository, a gateway) never opens or commits on its own: it receives the open transaction, or a session bound to it, and writes inside it. The use case does not name the mechanism either: it asks a unit-of-work port to run it, and the composition root gives that port its database.

An adapter that writes `BEGIN` and `COMMIT` in its own body breaks this twice: its commit is final even when the use case later fails, and two adapters in one use case become two transactions.

## Every transaction ends, in commit or rollback

The unit of work commits when the use case returns success, and rolls back on everything else: an exception the code expected, one it did not, and a failure returned as a value (a `Result` of error) rather than thrown. The last is the case that is forgotten: no exception reaches the transaction's guard, so the guard commits a half-done change unless it reads the result. A transaction left open holds its locks until the connection closes. The idiomatic guard in each language (a context manager, a `try`/`finally`, a `defer`, a callback API) is the one place that decides; the test forces a failure of each kind and asserts the rollback and that no transaction is left open.

Database by database, the mechanics:

- **PostgreSQL** runs at Read Committed unless told otherwise; at Serializable a transaction can fail with a serialization failure, and the application must be prepared to retry it ([Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-SERIALIZABLE)).
- **SQLite** begins a transaction as `DEFERRED` by default, and without an explicit `BEGIN` every statement is its own transaction ([Transaction](https://sqlite.org/lang_transaction.html)). In WAL mode readers proceed while one writer writes, but there is only one writer at a time ([WAL — concurrency](https://sqlite.org/wal.html#concurrency)), so a long transaction that writes blocks every other writer.
- **MySQL**'s InnoDB defaults to Repeatable Read ([Isolation Levels](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html#isolevel_repeatable-read)), detects a deadlock and rolls back one of the transactions, which the caller retries ([Deadlock Detection](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-detection.html)), and ends any open transaction when a DDL statement runs ([Implicit Commit](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html)) — so a migration never mixes a schema change with the data change that depends on it in one transaction.
- **MongoDB** makes one document atomic, embedded parts included ([Atomicity and Transactions](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)). A multi-document transaction exists and costs more than a single-document write; for many cases the denormalised model remains optimal ([Transactions](https://www.mongodb.com/docs/manual/core/transactions/)). The drivers' callback API retries a `TransientTransactionError` and commits, or aborts on error ([Drivers API](https://www.mongodb.com/docs/manual/core/transactions-in-applications/)), so the unit of work uses it rather than a hand-written commit.
- **DynamoDB** makes one item atomic; `TransactWriteItems` groups up to 100 write actions all-or-nothing ([TransactWriteItems](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html#transaction-apis-txwriteitems)). An entity and its history item go in one such call.

On the document and key-value stores the unit of work is the same idea at a different grain: the single-document or single-item write when the aggregate fits in one, the transaction API when the entity and its history are two.

## One aggregate root per transaction

A transaction changes one aggregate root. The root is the boundary the domain draws around an invariant (`ahrena-engineering-fundamentals:rules/aggregates.md`); two roots changed in one transaction is a second invariant nobody modelled, held together by a lock. An effect on another root — reserve stock when an order is placed — goes out as an event the first transaction records, and the second root reacts to it in its own transaction. The event is written in the same transaction as the change that produced it (an outbox row, an append-only event), so it is never lost and never sent for a change that rolled back.

## A write is always in a transaction

A single-row write still belongs to a transaction when it also writes history: the entity row and its history row are two writes, and the database's autocommit would make them two transactions. The integration test makes the second write fail and asserts the first did not stay.

## Where this stops

Distributed transactions across services, and sagas, are a design across components, made with the cloud plugin and the backend builder. Read-only queries need no unit of work beyond what the driver gives them, unless they need a consistent snapshot across several reads. Retry policy for a failed transaction — how many times, with what backoff — is `ahrena-engineering-reliability`'s.
