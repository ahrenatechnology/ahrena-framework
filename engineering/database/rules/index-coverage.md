---
id: index-coverage
type: rule
clade: engineering
subclade: database
title: Every Query Has an Index and Every Index a Query
statement: Every query on a growing table has an index, every index a query; NoSQL keys come from access patterns; an index on a table with rows never locks writes.
enforcement: judgment
references:
  - docs/indexing.md
  - docs/database-capabilities.md
---

# Every Query Has an Index and Every Index a Query

An index exists because a named query needs it and leaves when none does; on a document or key-value store the keys and indexes are drawn from access patterns declared before the schema; and an index added to a table people already write to is built without stopping their writes. Why, and what each database offers and charges, are in [`docs/indexing.md`](../docs/indexing.md).

The conditions carry the quality rubric's identifiers (`IDX-n`, ahrenatechnology/ahrena-framework#323) and are decided by review, through `skills/reviewing-persistence/SKILL.md`, until the rubric's detectors land.

## Conditions

1. **Every query an adapter issues against a table that grows is served by an index: its plan, read in the integration test, shows no full scan of that table.** (`IDX-1`) Decided by the plan — `EXPLAIN`, `EXPLAIN QUERY PLAN`, `explain()` — asserted in the integration test; in DynamoDB, by no `Scan` serving an access pattern.
2. **Every index the migrations create is used by at least one adapter query.** (`IDX-2`) Decided by review, matching each index to a query whose plan uses it.
3. **On a document or key-value store, the access patterns are recorded before the keys, and the partition key, sort key and secondary indexes are each derived from a recorded pattern.** (`IDX-3`) Decided by review of the mode registry against the table or collection definition.
4. **An index added to a table that already holds rows in an environment people use is built without locking writes: `CREATE INDEX CONCURRENTLY` in PostgreSQL, `LOCK=NONE` in MySQL, or the database's equivalent.** (`IDX-4`) Decided by review of the migration.

## Where this stops

**Small, fixed tables.** A lookup table whose rows are written by migrations only, such as a list of countries, does not grow; condition 1 does not apply to it, and its registry entry says `growth: fixed`.

**Uniqueness.** An index that enforces a primary key or a unique constraint is there for the constraint; condition 2 does not apply to it.

**Tables created in the same migration.** Nothing writes to them yet, so condition 4 does not apply.

**SQLite.** One writer at a time is its design; condition 4 is met by stating that the build runs while the table is small or in a maintenance window.

**Performance beyond the index.** A slow query whose plan already uses the right index is a diagnosis, not a breach of this rule.
