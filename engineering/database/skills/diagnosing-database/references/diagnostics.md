# Read-only diagnostics, by database

The statements `diagnosing-database` runs at steps 2 and 3. Every one reads; none changes data, schema or a session. On PostgreSQL and MySQL each statement runs inside a read-only transaction ended by `ROLLBACK`, as that skill's step 2 states, and `ANALYZE` is never used on a statement with `FOR UPDATE` or `FOR SHARE`. SQLite's `EXPLAIN QUERY PLAN` and `PRAGMA table_info`, MongoDB's `explain()` on a `find` and its catalogue reads, and DynamoDB's `describe-table` execute no write and run as given. Each names the page of the database's documentation it rests on, read on 2026-11-14. Paste a plan or a lock row into the diagnosis with any row data removed.

## Slow query

| Database | Read | What to look for |
|---|---|---|
| PostgreSQL | `BEGIN TRANSACTION READ ONLY; EXPLAIN (ANALYZE, BUFFERS) <select>; ROLLBACK;`; `EXPLAIN <write>` | `Seq Scan` on a large table, rows estimated far from actual ([Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)); the statement's totals in `pg_stat_statements`, which needs the module in `shared_preload_libraries` ([pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)) |
| SQLite | `EXPLAIN QUERY PLAN <statement>` | `SCAN <table>` where `SEARCH ... USING INDEX` was expected ([EXPLAIN QUERY PLAN](https://sqlite.org/eqp.html#table_and_index_scans)) |
| MySQL | `EXPLAIN <statement>`; `START TRANSACTION READ ONLY; EXPLAIN ANALYZE <select>; ROLLBACK;` | join type `ALL`, the `key` column empty ([EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html)) |
| MongoDB | `db.<collection>.find(<filter>).explain("executionStats")` | `COLLSCAN`, or `totalDocsExamined` far above `nReturned` ([Explain Results](https://www.mongodb.com/docs/manual/reference/explain-results/)) |
| DynamoDB | the access pattern's call in the code, and the table's key schema and indexes (`aws dynamodb describe-table`) | a `Scan`, or a `Query` with a filter expression discarding most of what it read ([Querying and scanning](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-query-scan.html)) |

## Locks

| Database | Read | What to look for |
|---|---|---|
| PostgreSQL | `pg_stat_activity` (`state`, `wait_event_type`, `xact_start`, `query`); `pg_blocking_pids(<pid>)`; `pg_locks` where `granted` is false | the blocker's session, how long its transaction has been open, `idle in transaction` ([pg_stat_activity](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW), [pg_blocking_pids](https://www.postgresql.org/docs/current/functions-info.html#FUNCTIONS-INFO-SESSION-TABLE), [pg_locks](https://www.postgresql.org/docs/current/view-pg-locks.html)); which statements take which lock mode ([Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-TABLES)) |
| SQLite | the error the caller got (`SQLITE_BUSY`) and which connection held a write transaction | one writer at a time, and even in WAL mode a reader can occasionally get `SQLITE_BUSY` ([WAL — concurrency](https://sqlite.org/wal.html#concurrency)) |
| MySQL | `performance_schema.data_locks` and `data_lock_waits`; `SHOW ENGINE INNODB STATUS` for the latest deadlock | the lock held and the one requested ([data_locks](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-locks-table.html)); the two transactions of the deadlock and which was rolled back ([Deadlocks](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html)) |
| MongoDB | `db.currentOp()` filtered on `waitingForLock`; transactions open for long | an operation waiting behind an index build's brief exclusive lock ([Index Builds](https://www.mongodb.com/docs/manual/core/index-creation/)) |
| DynamoDB | the `TransactionConflictException` or `ConditionalCheckFailedException` the caller got | two writers on one item; a version that moved ([TransactWriteItems](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)) |

A wait that recurs is prevented, not only cleared: `lock_timeout` on PostgreSQL makes a migration fail fast instead of queueing every reader behind it ([Client Connection Defaults](https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-LOCK-TIMEOUT)).

## Failed migration

| Database | Read | What to look for |
|---|---|---|
| any | the migration tool's state table (`alembic_version`, `schema_migrations`, `flyway_schema_history`, `_prisma_migrations`) and its log | the last migration marked applied, and one marked failed or dirty |
| PostgreSQL | `pg_index` where `indisvalid` is false | an `INVALID` index left by a failed concurrent build, to be dropped and rebuilt ([CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY)) |
| SQLite | `PRAGMA table_info(<table>)` against the migration | a change `ALTER TABLE` does not support, which needs the table rebuilt ([ALTER TABLE](https://sqlite.org/lang_altertable.html#making_other_kinds_of_table_schema_changes)) |
| MySQL | `SHOW CREATE TABLE <table>` against the migration's statements | the statements that ran before the failure, committed by DDL's implicit commit ([Implicit Commit](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html)) |
| MongoDB | `db.<collection>.getIndexes()`; the validator in `db.getCollectionInfos()` | an index or a `$jsonSchema` validator the migration meant to add ([Schema Validation](https://www.mongodb.com/docs/manual/core/schema-validation/)) |
| DynamoDB | `aws dynamodb describe-table` | a global secondary index still `CREATING`, which cannot be queried until `ACTIVE` ([Adding a GSI](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.OnlineOps.html)) |
