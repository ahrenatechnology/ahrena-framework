# Persistence design: <capability>

Issue: <the capability's issue>. Database: <engine and version>. Registry: <path to the mode registry>.

## Inputs

| Input | Value | Source |
|---|---|---|
| Aggregates and roots | <list> | <domain layer, issue> |
| Queries or access patterns | <list, each with an id> | <use cases, API, issue> |
| Tenant | <the column or concept, or none> | <issue, model> |
| Figures assumed | <row counts, rates; "not stated" where the issue gave none> | |

## Tables

| Table | Mode | Why: fact or edited entity | History: shape and place | Version | Tenant |
|---|---|---|---|---|---|
| <name> | <append-only, upsert-with-history, ephemeral> | <one line> | <from docs/entity-history.md> | <column or n/a> | <column or none> |

## Indexes

| Index | Table | Columns or keys | Serves | Ships without locking writes by |
|---|---|---|---|---|
| <name> | <table> | <columns, partition and sort key> | <query or access-pattern id> | <CONCURRENTLY, LOCK=NONE, online build, new table: n/a> |

## Transactions

| Use case | Unit of work opened at | Root changed | Writes inside | On failure | Effect on another root |
|---|---|---|---|---|---|
| <name> | <the use-case edge> | <root> | <entity, history, event> | <rollback on exception, unexpected error and error result> | <event, or none> |

## Tenant strategy

<The strategy on record and how each tenant table meets it; or the proposed decision record's path and its status (proposed, accepted); or "no tenant".>

## Rule check

| Condition | Met by | Not met, and why |
|---|---|---|
| PER-1 … PER-8, TRX-1 … TRX-4, IDX-1 … IDX-4, MT-1 … MT-5 | <the table, index or boundary above> | <reason, or none> |

## Left open

<Questions, each with who answers it; decisions to record; figures assumed.>
