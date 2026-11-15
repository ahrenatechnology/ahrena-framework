---
id: multi-tenancy
type: doc
clade: engineering
subclade: database
title: Tenant Isolation in the Database
summary: Why a tenant that appears with no recorded strategy stops the change and a decision record proposes Row-Level Security, how RLS is applied once accepted — enabled and forced on every tenant table, the tenant set per transaction, a connection role that cannot bypass it, a separate migration role — and what each database without RLS records instead; the companion of the tenant-isolation rule.
references:
  - rules/tenant-isolation.md
  - docs/database-capabilities.md
  - docs/transactions.md
---

# Tenant Isolation in the Database

This is the rationale behind [`rules/tenant-isolation.md`](../rules/tenant-isolation.md). A tenant is whatever separates one customer's data from another's: an organisation, an account, a workspace — a column or a concept of owner that every row carries. When a model has one, a query that forgets to filter by it reads another customer's data, and that is the incident this page exists to prevent.

## A tenant with no strategy stops the change

The first time a tenant appears in a model, the strategy for isolating it is a decision, and it is the maintainer's to take, not the builder's. So the change stops and proposes it in a decision record (`ahrena-contributing:skills/writing-decision-records/SKILL.md`), with Row-Level Security as the proposal where the database has it, and nothing is isolated by hand in the meantime: a hand-written filter added "for now" becomes the strategy by default. Once the record is accepted it enters the `strategies:` block of the mode registry and holds for every tenant table after it; a later change follows it, and replacing it takes a record that supersedes the first and a migration plan.

## Why Row-Level Security

A filter written in every query is correct only as long as every query remembers it. Row-Level Security moves the filter into the database: a policy on the table decides which rows a session may see and change, and no query can leave it out. In PostgreSQL:

- **Enable it on the table.** `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`; with RLS on and no policy, the table denies everything ([Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html#DDL-ROWSECURITY)).
- **Force it.** The table's owner normally bypasses its policies; `FORCE ROW LEVEL SECURITY` applies them to the owner too ([same page](https://www.postgresql.org/docs/current/ddl-rowsecurity.html#DDL-ROWSECURITY)). Without it, an application that connects as the owner is not isolated at all.
- **Write the policy both ways.** `USING` decides which existing rows are visible, updatable and deletable; `WITH CHECK` decides which rows may be inserted or written ([CREATE POLICY](https://www.postgresql.org/docs/current/sql-createpolicy.html#SQL-CREATEPOLICY-SUMMARY)). A policy with only `USING` lets a session write a row into another tenant.
- **Set the tenant inside the transaction.** The unit of work, at the use-case edge, sets the tenant for the session with `SET LOCAL` or `set_config(name, value, true)`, which last only until the transaction ends ([SET](https://www.postgresql.org/docs/current/sql-set.html), [Configuration Settings Functions](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADMIN-SET)); the policy reads it with `current_setting`. Set for the transaction rather than the connection, it cannot leak to the next request a pooled connection serves. `SET LOCAL` outside a transaction has no effect beyond a warning, which is one more reason the write is always in one ([`transactions.md`](transactions.md)).
- **Connect with a role that cannot bypass it.** Superusers and roles with `BYPASSRLS` always bypass row security ([Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html#DDL-ROWSECURITY), [CREATE ROLE](https://www.postgresql.org/docs/current/sql-createrole.html)). The application's role is neither, and is not the tables' owner; migrations run under a second role that owns the schema and that the application never uses.
- **Test it with two tenants.** An integration test acting as one tenant tries to read, change and delete the other's rows, through the adapters and through a raw query on the application's role, and finds nothing.

## Databases without Row-Level Security

The decision records the alternative, and the two-tenant test is required all the same.

| Database | What it offers | The alternative to record |
|---|---|---|
| SQLite | no `GRANT` or `REVOKE`: the only permissions are the file's ([Not Implemented](https://sqlite.org/omitted.html)) | the tenant filter applied in a single database-access base every adapter goes through, never written by hand in each query; or one database file per tenant |
| MySQL | privileges at global, database, table, column, routine and proxy level, none per row ([GRANT](https://dev.mysql.com/doc/refman/8.4/en/grant.html)) | the single access base with the filter; or a schema per tenant when tenants are few and must be separated hard |
| MongoDB | privileges on a database, a collection, a set of collections or the cluster ([Role-Based Access Control](https://www.mongodb.com/docs/manual/core/authorization/)) | MongoDB's own guide names a database per tenant for a few hundred stable tenants needing strict isolation, and shared collections with a tenant id on every document for unbounded growth, isolated by the application; it advises against a set of collections per tenant in one database ([Build a Multi-Tenant Architecture](https://www.mongodb.com/docs/atlas/build-multi-tenant-arch/)) |
| DynamoDB | the IAM condition key `dynamodb:LeadingKeys` limits a principal to items whose partition key matches, with the `ForAllValues` modifier, and `Scan` not granted ([Fine-grained access control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html#FGAC_DDB.ConditionKeys)) | the tenant as the leading part of the partition key, and the credentials of each request scoped to it by that condition |

## Where this stops

This page isolates tenants inside the database. Who a user is and which tenant they belong to is decided before the request reaches it, and checking that a user may act on a record of their own tenant is `ahrena-engineering-security:reviewing-access`. Which client is a tenant, and how many there are, is client logic and an input to the design.
