# Persistence review conditions

The conditions `reviewing-persistence` applies, with the quality rubric's identifiers (ahrenatechnology/ahrena-framework#323). Severity is not fixed here: it follows `review-findings.md`, by whether the line is in the diff. Each gives the state, how it is read today, what exempts it, the correction, and the rule condition it comes from. Where an integration test already decides a condition on this change and is green, cite the test instead of reading the condition again.

## Persistence mode

### PER-1 A table with no declared mode

- **State:** a table, collection or item type the migrations create that has no entry in the mode registry, or an entry whose `mode` is not `append-only`, `upsert-with-history` or `ephemeral`, or an `ephemeral` entry with no `reason`.
- **Detect:** compare the tables created at the head with the registry's `tables`.
- **Exempt:** the migration tool's own bookkeeping table.
- **Correct:** add the entry, choosing the mode by whether the record is a fact or an edited entity.
- **Source:** `rules/persistence-mode.md` condition 1.

### PER-2 An append-only table changed or emptied

- **State:** an adapter issues `UPDATE`, `DELETE`, `MERGE`/`ON CONFLICT DO UPDATE`, `replaceOne`, `updateOne`, `deleteOne`, `UpdateItem` or `DeleteItem` against a table declared `append-only`; or the database grants the application role `UPDATE` or `DELETE` on it where it could refuse.
- **Detect:** every write to the table in every adapter; the grants or triggers in the migrations.
- **Exempt:** the declared erasure path of a decision record.
- **Correct:** write the change as a new fact; grant `INSERT` and `SELECT` only, or add the refusing trigger.
- **Source:** `rules/persistence-mode.md` condition 2.

### PER-3 An upsert with no history in its transaction

- **State:** a write to an `upsert-with-history` table with no history record written in the same transaction, or a history record missing identity, version, when, who, or the state.
- **Detect:** each write path to the table; the integration test that changes the entity twice and counts two history records.
- **Exempt:** none.
- **Correct:** write the history record in the same unit of work, in the shape the registry declares.
- **Source:** `rules/persistence-mode.md` condition 3.

### PER-4 An upsert with no version check

- **State:** an `upsert-with-history` table with no version column, or a write that does not condition on the version it read (no `AND version = ?`, no version filter, no condition expression).
- **Detect:** the table definition and each update statement; the integration test that writes with a stale version.
- **Exempt:** none.
- **Correct:** add the version, condition every write on it, and refuse a write that touched no row.
- **Source:** `rules/persistence-mode.md` condition 4.

### PER-5 A physical delete

- **State:** a `DELETE`, `deleteOne`/`deleteMany`, `DeleteItem` or `TRUNCATE` on a table that is not `ephemeral`.
- **Detect:** the adapters and scheduled jobs.
- **Exempt:** the declared erasure path; an `ephemeral` table.
- **Correct:** record the removal as an event, or set a deletion mark and write its history.
- **Source:** `rules/persistence-mode.md` condition 5.

### PER-6 A projection nothing rebuilds

- **State:** a current-state read model over an `append-only` table with no test that rebuilds it from the log and compares.
- **Detect:** the registry's `projection` and `rebuild_test`; the test itself.
- **Exempt:** none.
- **Correct:** add the rebuild test.
- **Source:** `rules/persistence-mode.md` condition 6.

### PER-7 A mode changed without a decision

- **State:** the registry's `mode` for an existing table changes in the diff without a superseding decision record and a data migration in the same change.
- **Detect:** the registry's diff against the base.
- **Exempt:** a table created in the same change.
- **Correct:** add the decision record and the migration of the existing rows, or restore the mode.
- **Source:** `rules/persistence-mode.md` condition 7.

### PER-8 History away from the entity, or in a shape the database does not serve

- **State:** an upsert table whose registry entry has no `history`, or a shape `docs/entity-history.md` does not give for the database (an array growing with every edit inside a MongoDB document; JSON history on a store with no index over JSON).
- **Detect:** the registry against `docs/database-capabilities.md`.
- **Exempt:** none.
- **Correct:** declare the shape the database supports best, from `docs/entity-history.md`.
- **Source:** `rules/persistence-mode.md` condition 8.

## Transactions

### TRX-1 A write outside a transaction

- **State:** a write that runs in autocommit, including one that also writes history in a second statement.
- **Detect:** the path from the use case to the adapter; the integration test that fails the second write and finds the first gone.
- **Exempt:** a single-document or single-item write that holds the aggregate and its history whole.
- **Correct:** run the writes through the unit of work.
- **Source:** `rules/transaction-boundaries.md` condition 1.

### TRX-2 A transaction opened in an adapter

- **State:** an adapter body that issues `BEGIN`, `COMMIT`, `ROLLBACK`, `session.begin()`, `startTransaction`, `TransactWriteItems` of its own accord, or a driver's equivalent, rather than receiving the open unit of work.
- **Detect:** the adapters.
- **Exempt:** the unit of work's own implementation; a migration.
- **Correct:** remove the transaction from the adapter and pass it the unit of work's session; on MongoDB the adapter receives the callback API's `session`; on DynamoDB the adapter adds its write actions to the unit of work, and the unit of work alone calls `TransactWriteItems` at commit.
- **Source:** `rules/transaction-boundaries.md` condition 2.

### TRX-3 Two aggregate roots in one transaction

- **State:** a use case that saves two roots inside one unit of work.
- **Detect:** the use case and the repositories it calls.
- **Exempt:** none.
- **Correct:** save one root, record an event in the same transaction, and let the second root react in its own.
- **Source:** `rules/transaction-boundaries.md` condition 3.

### TRX-4 A transaction that does not always end

- **State:** a unit of work that commits on a returned error, does not roll back on an unexpected exception, or has a path that leaves the transaction open.
- **Detect:** the guard around the use case; the test that forces each kind of failure.
- **Exempt:** none.
- **Correct:** commit only on success, roll back on every other outcome in a `finally` or the language's equivalent.
- **Source:** `rules/transaction-boundaries.md` condition 4.

## Indexes

### IDX-1 A query no index serves

- **State:** an adapter query against a table that grows whose plan shows a full scan (`Seq Scan`, `SCAN`, type `ALL`, `COLLSCAN`), or a DynamoDB `Scan` serving an access pattern.
- **Detect:** the plan asserted in the integration test; without one, the query's filter columns against the indexes at the head.
- **Exempt:** a table whose registry entry says `growth: fixed` (rows written by migrations only).
- **Correct:** add the index whose leading columns are the query's equality filters, or the key the pattern needs.
- **Source:** `rules/index-coverage.md` condition 1.

### IDX-2 An orphan index

- **State:** an index the change adds that no adapter query uses.
- **Detect:** match each new index to a query whose filter, join or sort it serves.
- **Exempt:** an index enforcing uniqueness.
- **Correct:** remove it, or name the query it serves.
- **Source:** `rules/index-coverage.md` condition 2.

### IDX-3 NoSQL keys with no recorded pattern

- **State:** a partition key, sort key or secondary index on a document or key-value store with no access pattern in the registry that it serves.
- **Detect:** the registry's `access_patterns` against the table or collection definition.
- **Exempt:** none.
- **Correct:** record the pattern first, then derive the key from it.
- **Source:** `rules/index-coverage.md` condition 3.

### IDX-4 An index that locks writes

- **State:** a migration that creates an index on a table already holding rows with a plain `CREATE INDEX` on PostgreSQL, or without `LOCK=NONE` on MySQL.
- **Detect:** the migrations; whether the table was created in the same change.
- **Exempt:** a table created in the same change; SQLite with the window stated.
- **Correct:** build it concurrently in a migration of its own, outside the transaction, or state `LOCK=NONE`.
- **Source:** `rules/index-coverage.md` condition 4.

## Tenants

### MT-1 A tenant with no strategy

- **State:** a tenant column or owner concept added while the registry's `strategies.tenancy` holds no accepted strategy; or a filter by tenant written by hand in its place.
- **Detect:** the migrations and the registry's `strategies:` block.
- **Exempt:** none.
- **Correct:** stop and propose Row-Level Security, or the database's alternative, in a decision record; remove the hand-written isolation.
- **Source:** `rules/tenant-isolation.md` condition 1.

### MT-2 A tenant table without forced RLS

- **State:** with RLS adopted, a tenant table without `ENABLE` and `FORCE ROW LEVEL SECURITY`, or with a policy lacking `USING` or `WITH CHECK` on the session's tenant.
- **Detect:** the migrations at the head; the catalogue query in the integration test.
- **Exempt:** a database whose decision record names another strategy.
- **Correct:** enable and force RLS and add the policy both ways.
- **Source:** `rules/tenant-isolation.md` condition 2.

### MT-3 The tenant filtered by hand

- **State:** the tenant set on the connection rather than the transaction, set outside the use-case edge, or an adapter's own tenant filter standing in place of the policy (no policy on the table, the filter doing its work).
- **Detect:** the unit of work and the adapters.
- **Exempt:** the single access base of a decision record for a database without RLS.
- **Correct:** set it with `SET LOCAL` or `set_config(..., true)` in the unit of work and drop the hand-written filter.
- **Source:** `rules/tenant-isolation.md` condition 3.

### MT-4 No two-tenant test

- **State:** a tenant table with no integration test in which one tenant fails to read, change and delete another's rows.
- **Detect:** the integration tests.
- **Exempt:** none, on any database.
- **Correct:** add the test.
- **Source:** `rules/tenant-isolation.md` condition 4.

### MT-5 A role that can bypass isolation

- **State:** the application connects as a superuser, a role with `BYPASSRLS`, or the tables' owner; or migrations run under the application's role.
- **Detect:** the connection configuration and the role definitions.
- **Exempt:** none.
- **Correct:** connect with a role that has none of these, and run migrations under a separate one.
- **Source:** `rules/tenant-isolation.md` condition 5.
