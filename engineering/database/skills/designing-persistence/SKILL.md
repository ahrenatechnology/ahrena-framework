---
name: designing-persistence
description: Use before the OLTP layer of a backend build, or the schema layer of a data build whose store is transactional, when a model has to be persisted and nothing decides how yet - a new aggregate, a new table or collection, a tenant appearing in the model, a change of database. Produces, for the given model and database, the mode of each table (append-only or upsert with history), the shape and place of its history, its indexes with the query or access pattern each serves, the transaction boundaries, and the tenant strategy when a tenant exists, written into the mode registry beside the migrations and a design note. It designs; it writes no migration or adapter code.
type: skill
clade: engineering
subclade: database
references:
  - rules/persistence-mode.md
  - rules/transaction-boundaries.md
  - rules/index-coverage.md
  - rules/tenant-isolation.md
  - docs/database-capabilities.md
  - docs/entity-history.md
  - docs/indexing.md
  - docs/transactions.md
  - docs/multi-tenancy.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-contributing:skills/writing-decision-records/SKILL.md
---

# Designing persistence

The output is two files the builder of the OLTP layer writes against and a reviewer holds the result to: the mode registry beside the migrations, from `references/persistence-modes.example.yaml`, and a design note, from `references/design-template.md`. Every choice names its reason; every reason that is a fact about the database names the page in this plugin's docs that cites it.

## 1. Read what is already decided

Run `ahrena-engineering-fundamentals:reading-the-component-map` for the project's words and its persistence component. Then read, in the project: the existing mode registry, if any; the migrations directory and the tool that runs them; the adapters (repositories, gateways) and how they open transactions; the decision records and the strategy register. Output: the database and its version, the registry or its absence, the strategies already chosen.

A strategy already on record — a mode, a history shape, a unit-of-work mechanism, a tenant strategy — is kept. This design extends it; it does not open a second way. A design that needs to change one stops here and says so: the change takes a decision record that supersedes the first and a migration plan, and that is the maintainer's to approve.

## 2. Settle the inputs, or stop

From the brief and the domain layer: the aggregates and their roots, each entity's fields, the use cases that load and save them, the queries the use cases and the API will run, and whether a tenant separates the data. For a document or key-value store, also every access pattern: who reads or writes what, by which key, in what order, how often.

A missing database, a missing access pattern on a NoSQL store, or a tenant whose strategy is not on record changes the design, so each is a question back to the caller, asked in one batch, before step 3. Write "not stated" beside any figure the brief did not give and the design assumed.

## 3. Choose each table's mode

For each table, collection or item type, ask whether its record is a fact that happened or an entity a person edits, as [`docs/entity-history.md`](../../docs/entity-history.md) argues: a fact is `append-only`; an edited entity is `upsert-with-history`; a cache, session, lock or rebuilt view is `ephemeral`, with the reason. Prefer append-only when the answer is unclear. Split a table that is both into the entity and its facts.

The recurring failure is calling a table upsert because the first screen edits it, when what the screen records is a sequence of facts (a status that moves forward is a log of transitions, not an editable field).

## 4. Place the history

For each upsert table, choose where its history lives from the table in `docs/entity-history.md`, by what [`docs/database-capabilities.md`](../../docs/database-capabilities.md) says the chosen database supports: JSON beside the entity where JSON is indexable; a version collection or sibling items under the same partition key on a document or key-value store; append-only first, or a current-plus-history pair, where neither exists. Name the version column, the history's fields (identity, version, at, by, state), and the erasure path when the record holds personal data. For each append-only table, name the projection that reads its current state and the test that rebuilds it.

## 5. Derive the indexes

Relational: list each query from step 2 with its filter, join and sort columns, and give it an index whose leading columns are its equality filters, per [`docs/indexing.md`](../../docs/indexing.md); add the index a foreign key needs where a query joins or cascades along it. NoSQL: derive the partition key, sort key and each secondary index from the access patterns, and name the pattern each serves; a pattern only a scan would serve is a missing key.

Every index is written with the query or pattern it serves. An index with none is not designed. For an index on a table that already holds rows, name how it ships without locking writes on the chosen database.

## 6. Draw the transaction boundaries

Per use case: the unit of work it opens at its edge, the aggregate root it changes, the writes inside it (entity, history, event), and how it ends on success and on each kind of failure, per [`docs/transactions.md`](../../docs/transactions.md). An effect on a second root becomes an event recorded in the same transaction. On a document or key-value store, say whether the single-write atomicity suffices or the transaction API is needed, and check the group fits the API's limit.

## 7. Decide the tenant strategy, when a tenant exists

If a tenant exists and the register holds a strategy, apply it to every tenant table. If it holds none, draft the decision record with `ahrena-contributing:writing-decision-records`, proposing Row-Level Security where the database has it, as [`docs/multi-tenancy.md`](../../docs/multi-tenancy.md) describes — enabled and forced, `USING` and `WITH CHECK` on the session's tenant, the tenant set per transaction, an application role that is not a superuser, has no `BYPASSRLS` and does not own the tables, a separate migration role — or recording the alternative where the database has no RLS. The record is a proposal: nothing is isolated until the maintainer accepts it, and the two-tenant test is in the design either way.

## 8. Write the registry and the note

Write the registry from `references/persistence-modes.example.yaml` beside the migrations, at the path the project's migration tool uses, and the design note from `references/design-template.md` where the project keeps designs, or return it in full when it keeps none. Every table in the model is in the registry. Check the result against the four rules — [`persistence-mode`](../../rules/persistence-mode.md), [`transaction-boundaries`](../../rules/transaction-boundaries.md), [`index-coverage`](../../rules/index-coverage.md), [`tenant-isolation`](../../rules/tenant-isolation.md) — condition by condition; a condition the design cannot meet is named in the note with its reason, not left for review to find.

## When this skill does not apply

**Writing the migrations and adapters.** That is the OLTP layer's builder, against this design.

**Analytical stores.** A warehouse, a medallion layer or a mart is designed by `ahrena-engineering-data`'s contract-first build.

**Choosing the managed service.** Which managed database a workload runs on is the cloud plugin's design (`ahrena-engineering-aws:designing-on-aws` and its Google Cloud and Azure equivalents); this skill starts from the engine it chose.

**A change already written.** That is `skills/reviewing-persistence/SKILL.md`; a slow query, a lock or a failed migration is `skills/diagnosing-database/SKILL.md`.
