---
id: database-capabilities
type: doc
clade: engineering
subclade: database
title: What Each Database Supports, and Where It Says So
summary: For PostgreSQL, SQLite, MySQL, MongoDB and DynamoDB, the capabilities a persistence design depends on — indexable JSON, row-level isolation, building an index without blocking writes, DDL inside a transaction, the unit that is atomic, the plan reader and the size ceiling — each cited to the database's own documentation, read on 2026-11-14.
references:
  - docs/entity-history.md
  - docs/indexing.md
  - docs/transactions.md
  - docs/multi-tenancy.md
---

# What Each Database Supports, and Where It Says So

A persistence design is decided within the premises of the database it runs on. This page is where those premises are looked up: one row per capability, one column per database, each cell resting on a page of the database's own documentation. The other docs of this plugin argue what to do with a capability; this one only says whether it is there.

Every page below was read in its current text on 2026-11-14: PostgreSQL's `current` manual (18), SQLite's site, MySQL's 8.4 reference manual (the manual marks 9.7 as its newest; a project on 9.x checks its own version's page), MongoDB's manual and Atlas pages, and the DynamoDB developer guide. A claim about a version not listed here is a claim to check again, not to infer from this table.

## The table

| Capability | PostgreSQL | SQLite | MySQL (InnoDB) | MongoDB | DynamoDB |
|---|---|---|---|---|---|
| History held as indexable JSON beside the entity | `jsonb`, with GIN or expression indexes [^pg-json] | JSON functions built in since 3.38.0 and all deterministic, so an expression index can hold them [^sq-json] [^sq-expr] | `JSON` type, indexed through a generated column or a functional key part [^my-json] [^my-idx] | native: the document itself [^mg-ver] | native: an attribute, or sibling items under one partition key [^dy-sort] |
| Isolation of rows by tenant inside the database | Row-Level Security policies [^pg-rls] | none: no `GRANT`, only file permissions [^sq-omit] | none: privileges stop at the column [^my-priv] | none: privileges stop at the collection [^mg-auth] | `dynamodb:LeadingKeys` in an IAM policy, per partition key [^dy-fgac] |
| Index built without blocking writes | `CREATE INDEX CONCURRENTLY` [^pg-cic] | no: one writer at a time [^sq-wal] | online DDL: adding a secondary index leaves the table readable and writable [^my-online] | yes: exclusive lock only at the start and end of the build [^mg-build] | a global secondary index is backfilled while the table stays available [^dy-gsi-online] |
| A schema statement a migration cannot wrap in its transaction | `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block [^pg-cic] | not checked; read the manual before relying on it | every DDL statement commits implicitly [^my-commit] | not applicable | not applicable |
| What one write is atomic over | any rows, in a transaction | any rows, in a transaction [^sq-tx] | any rows, in a transaction | one document; several only in a multi-document transaction, at a cost [^mg-atom] [^mg-tx] | one item; up to 100 actions in `TransactWriteItems` [^dy-tx] |
| Reading how a query runs | `EXPLAIN` [^pg-explain] | `EXPLAIN QUERY PLAN` [^sq-eqp] | `EXPLAIN` [^my-explain] | `explain()` [^mg-explain] | no planner: `Query` against a key or index, or `Scan` of the whole table [^dy-scan] |
| Size ceiling a history must fit under | not a design constraint here | not a design constraint here | not a design constraint here | 16 MiB per document [^mg-limit] | 400 KB per item [^dy-item]; 10 GB per item collection with a local secondary index [^dy-lsi] |

## What the table decides

**Where history lives** follows the first row: [`entity-history.md`](entity-history.md) puts it in JSON beside the entity where the JSON is indexable, inside the document or in sibling items in a document store, and in an append-only log or a current-plus-history pair where neither exists. The last row bounds the document-store choice: a history embedded in one document grows toward a ceiling the database enforces.

**How tenants are isolated** follows the second row: [`multi-tenancy.md`](multi-tenancy.md) proposes Row-Level Security where the database has it, and records the alternative where it does not.

**How a new index ships** follows the third row: [`indexing.md`](indexing.md).

**How a migration is written** follows the fourth: on MySQL a migration that fails halfway keeps the DDL it already ran, so each migration holds one DDL change; on PostgreSQL a concurrent index build is its own migration, outside the transaction the migration tool would open ([`transactions.md`](transactions.md)).

## Where this stops

This page lists the five databases the issue named. A sixth one is added here with its own pages before a design relies on it; nothing about it is inferred from a neighbour. Managed variants (Aurora, Cloud SQL, Atlas) inherit their engine's row unless their own documentation says otherwise, and which managed service to choose is the cloud plugin's (`ahrena-engineering-aws:docs/services.md` and its Google Cloud and Azure equivalents).

[^pg-json]: PostgreSQL, [8.14.4 jsonb Indexing](https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING).
[^pg-rls]: PostgreSQL, [5.9 Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).
[^pg-cic]: PostgreSQL, [CREATE INDEX — Building Indexes Concurrently](https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY).
[^pg-explain]: PostgreSQL, [14.1 Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html).
[^sq-json]: SQLite, [JSON Functions And Operators — Overview](https://sqlite.org/json1.html), which marks every JSON function `SQLITE_DETERMINISTIC`.
[^sq-expr]: SQLite, [Indexes On Expressions](https://sqlite.org/expridx.html#how_to_use_indexes_on_expressions).
[^sq-omit]: SQLite, [SQL Features That SQLite Does Not Implement](https://sqlite.org/omitted.html).
[^sq-wal]: SQLite, [Write-Ahead Logging](https://sqlite.org/wal.html).
[^sq-tx]: SQLite, [Transaction](https://sqlite.org/lang_transaction.html).
[^sq-eqp]: SQLite, [EXPLAIN QUERY PLAN](https://sqlite.org/eqp.html).
[^my-json]: MySQL 8.4, [The JSON Data Type](https://dev.mysql.com/doc/refman/8.4/en/json.html).
[^my-idx]: MySQL 8.4, [CREATE INDEX Statement](https://dev.mysql.com/doc/refman/8.4/en/create-index.html).
[^my-priv]: MySQL 8.4, [Privileges Provided by MySQL](https://dev.mysql.com/doc/refman/8.4/en/privileges-provided.html) and [GRANT Statement](https://dev.mysql.com/doc/refman/8.4/en/grant.html), whose levels are global, database, table, column, routine and proxy.
[^my-online]: MySQL 8.4, [Online DDL Operations](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html#online-ddl-index-operations).
[^my-commit]: MySQL 8.4, [Statements That Cause an Implicit Commit](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).
[^my-explain]: MySQL 8.4, [EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html).
[^mg-ver]: MongoDB, [Keep a History of Document Versions](https://www.mongodb.com/docs/manual/data-modeling/design-patterns/data-versioning/document-versioning/).
[^mg-auth]: MongoDB, [Role-Based Access Control](https://www.mongodb.com/docs/manual/core/authorization/).
[^mg-build]: MongoDB, [Index Builds on Populated Collections](https://www.mongodb.com/docs/manual/core/index-creation/).
[^mg-atom]: MongoDB, [Atomicity and Transactions](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/).
[^mg-tx]: MongoDB, [Transactions](https://www.mongodb.com/docs/manual/core/transactions/).
[^mg-explain]: MongoDB, [Explain Results](https://www.mongodb.com/docs/manual/reference/explain-results/).
[^mg-limit]: MongoDB, [MongoDB Limits and Thresholds](https://www.mongodb.com/docs/manual/reference/limits/).
[^dy-sort]: DynamoDB, [Using sort keys for version control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-sort-keys.html#bp-sort-keys-version-control).
[^dy-fgac]: DynamoDB, [Using IAM policy conditions for fine-grained access control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html#FGAC_DDB.ConditionKeys).
[^dy-gsi-online]: DynamoDB, [Adding a global secondary index to an existing table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.OnlineOps.html#GSI.OnlineOps.Creating.Phases).
[^dy-tx]: DynamoDB, [TransactWriteItems API](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html#transaction-apis-txwriteitems).
[^dy-scan]: DynamoDB, [Best practices for querying and scanning data](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-query-scan.html#bp-query-scan-performance).
[^dy-item]: DynamoDB, [Constraints — item size](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html#limits-items-size).
[^dy-lsi]: DynamoDB, [Item collection size limit](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/LSI.html#LSI.ItemCollections.SizeLimit).
