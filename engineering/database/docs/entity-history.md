---
id: entity-history
type: doc
clade: engineering
subclade: database
title: Append-Only or Upsert with History, and Where the History Lives
summary: Why a transactional table is append-only by preference and upsert with entity history otherwise, how to tell which a table is, what the mode registry beside the migrations records, where the history lives on each database, and where append-only stops — the companion of the persistence-mode rule.
references:
  - rules/persistence-mode.md
  - docs/database-capabilities.md
  - docs/transactions.md
---

# Append-Only or Upsert with History, and Where the History Lives

This is the rationale behind [`rules/persistence-mode.md`](../rules/persistence-mode.md). The rule says what a table must declare and what a write to it may do; this page says why, how a designer chooses, and how the choice is shaped by the database it runs on ([`database-capabilities.md`](database-capabilities.md)).

## Two modes, and the question that picks one

Every table of a transactional store is in one of two modes.

**Append-only.** A row, once written, is never changed or removed. The table is a log of things that happened; the current state is a projection read from it, and a test rebuilds that projection from the log.

**Upsert with history.** A row holds the current state of an entity and is changed in place; every change also writes, in the same transaction, a history record of who changed what, when, and the state before or after.

The maintainer's preference is append-only. The question that decides a table is: **is the record a fact that happened, or an entity a person edits?** An event, a measurement, an answer, a payment, a state transition is a fact: it is append-only, because a fact does not change after it happened, only gets followed by another fact. A configuration, a profile, a catalogue item, a draft is an entity a person edits: forcing it into a log of edits makes every read a reconstruction, so it is upsert with history.

When a table seems to be both, it is usually two: the entity a person edits, and the facts about it (an order's line items are edited until it is placed; its placement, payment and shipment are facts).

Either mode leaves a record of every change. That is the point of both: no write destroys the state it replaced.

## What both modes forbid

**A physical delete.** Removing a record is itself a fact: an event in an append-only table, a deletion mark (a timestamp and who) on an upserted entity, with its history row. The record stays readable to whoever audits it.

**A write with a stale version.** An upserted entity carries a version number; a write states the version it read, and the database refuses it when the stored version moved. Every database here can do this in one statement: an `UPDATE ... WHERE id = $1 AND version = $2` that reports zero rows touched on a relational store, a filter on the version in MongoDB's update (single-document writes are atomic, [MongoDB: Atomicity and Transactions](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)), and a condition expression on the version attribute in DynamoDB, which raises `ConditionalCheckFailedException` when it fails ([DynamoDB: Optimistic locking with version number](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBMapper.OptimisticLocking.html), [Condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)).

**A second write outside the transaction.** The entity and its history row are one unit: written together or not at all ([`transactions.md`](transactions.md)).

## The mode registry

Each table's mode is written down, once, in a versioned file beside the migrations, so a reviewer and a detector can compare what a table claims with what its writes do. The skill `designing-persistence` keeps the template (`skills/designing-persistence/references/persistence-modes.example.yaml`). Per table it records the mode, the shape of the history and where it lives, the version column, the tenant column if any, and the decision record behind a mode that was ever changed. For a document or key-value store it also records the access patterns the keys and indexes were drawn from ([`indexing.md`](indexing.md)).

The registry's `strategies:` block is where the project's persistence strategies are on record: the unit of work, and the tenant strategy, which is on record when `strategies.tenancy.strategy` is not `none` and names an accepted decision. Once a table's mode or a strategy is set it is kept. Changing it takes a decision record that supersedes the first and a data migration in the same change, because the rows already written were written under the old mode.

## Where the history lives, by database

The history lives close to the entity, in the form the chosen database supports best. The order of preference:

| The database has | History lives | Why |
|---|---|---|
| JSON with an index on it: PostgreSQL `jsonb`, SQLite's JSON functions, MySQL's `JSON` | relational columns for the entity, the history as JSON beside it: a child table of `(entity id, version, at, by, state jsonb)`, or a column when the history is short and read with the entity | the entity stays queryable by column; the history keeps any shape the entity had at the time, with an index on the fields a query reads ([PostgreSQL: jsonb Indexing](https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING); [SQLite: Indexes On Expressions](https://sqlite.org/expridx.html#how_to_use_indexes_on_expressions); [MySQL: indexing a generated column over JSON](https://dev.mysql.com/doc/refman/8.4/en/create-table-secondary-indexes.html#json-column-indirect-index)) |
| documents: MongoDB | the current document in one collection and its earlier versions in a second, keyed by the document's id and version; inside the document only when the design states a cap on the number of versions and that cap times the largest version stays under the 16 MiB limit with the margin the design states | MongoDB's own versioning pattern keeps older versions "in a separate collection from the current data" ([Keep a History of Document Versions](https://www.mongodb.com/docs/manual/data-modeling/design-patterns/data-versioning/document-versioning/)); an array that grows with every edit is the unbounded-array anti-pattern and can reach the 16 MiB document limit ([Unbounded Arrays](https://www.mongodb.com/docs/manual/data-modeling/design-antipatterns/unbounded-arrays/), [Limits](https://www.mongodb.com/docs/manual/reference/limits/)) |
| items and keys: DynamoDB | sibling items under the entity's partition key, one per version, with a sort-key prefix for the version and a fixed one for the latest | AWS's version-control pattern does exactly this: the zero-prefixed item is the latest, each update writes the next prefix and copies itself to zero ([Using sort keys for version control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-sort-keys.html#bp-sort-keys-version-control)); both writes go in one `TransactWriteItems` ([TransactWriteItems](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html#transaction-apis-txwriteitems)) and every item stays under 400 KB ([Constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html#limits-items-size)) |
| none of these: a relational store without indexable JSON | append-only first; where the current state must be read cheaply, a current table and a history table with the same columns plus version, at and by | without JSON a history of a changing shape is a second schema to keep in step, so the log that needs no second schema comes first |

DynamoDB Streams and change-data capture in general record changes too, but outside the write: a stream keeps item-level modifications for 24 hours ([DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)). A history that must exist when the write commits is written by the write.

## Keeping append-only honest

A convention that only the code keeps is broken by the first hand-written fix. The database can refuse it: on PostgreSQL the application's role is granted `INSERT` and `SELECT` on an append-only table and not `UPDATE` or `DELETE` ([Privileges](https://www.postgresql.org/docs/current/ddl-priv.html)); on SQLite, which has no grants, a trigger raises `RAISE(ABORT, ...)` on an update or delete ([CREATE TRIGGER — the RAISE function](https://sqlite.org/lang_createtrigger.html#the_raise_function)); on MySQL a `BEFORE UPDATE` or `BEFORE DELETE` trigger signals `SQLSTATE '45000'` ([SIGNAL Statement](https://dev.mysql.com/doc/refman/8.4/en/signal.html)). Document and key-value stores refuse it through the application's role: a MongoDB user-defined role can grant the `insert` and `find` actions on a collection without `update` and `remove` ([Privilege Actions](https://www.mongodb.com/docs/manual/reference/privilege-actions/)), and a DynamoDB IAM policy names each action it allows, so `dynamodb:PutItem`, `GetItem` and `Query` can be granted without `UpdateItem` and `DeleteItem` ([Using IAM policy conditions for fine-grained access control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)). Only where the application cannot run under a role of its own is the single access layer where the rule is kept, and the review what checks it.

## Where this stops

Where append-only itself stops:

**The right to erase personal data.** Brazil's LGPD, and laws like it, give a person the right to have their data erased. An append-only log meets it with a declared, audited erasure path — for example, the personal fields encrypted under a per-person key that is destroyed on request — never with a loose `DELETE`. The path is written in a decision record and is the only code allowed to make personal data unreadable.

**Data that is not the system's record.** A cache, a session, a lock, a queue's working table, a materialised view rebuilt from the record: none holds a fact or an entity the system answers for, so none needs history. The registry lists such a table with the mode `ephemeral` and the reason, so the absence of history is a decision rather than an omission.

**Analytical stores.** A warehouse, a medallion layer or a mart is `ahrena-engineering-data`'s, under its own contract.
