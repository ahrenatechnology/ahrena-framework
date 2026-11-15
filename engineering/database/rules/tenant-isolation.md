---
id: tenant-isolation
type: rule
clade: engineering
subclade: database
title: Tenants Are Isolated by the Database Once the Strategy Is Recorded
statement: A tenant with no strategy stops for an RLS decision record; once adopted, RLS is enabled and forced on every tenant table under a non-bypassing role.
enforcement: judgment
references:
  - docs/multi-tenancy.md
  - docs/database-capabilities.md
---

# Tenants Are Isolated by the Database Once the Strategy Is Recorded

When a model holds more than one customer's data, the strategy that keeps them apart is a decision on record before any isolation is written, and once Row-Level Security is adopted it holds on every tenant table with no way for the application to step around it. Why, how RLS is applied, and what a database without it records instead are in [`docs/multi-tenancy.md`](../docs/multi-tenancy.md).

The conditions carry the quality rubric's identifiers (`MT-n`, ahrenatechnology/ahrena-framework#323) and are decided by review, through `skills/reviewing-persistence/SKILL.md`, until the rubric's detectors land.

## Conditions

1. **A change that adds a tenant column or owner concept to a project with no tenant strategy on record in the registry's `strategies:` block stops and proposes Row-Level Security in a decision record, and isolates nothing by hand.** (`MT-1`) Decided by review: a tenant column in the migrations and no accepted strategy in `strategies.tenancy`.
2. **Once RLS is adopted, every table with a tenant column has row-level security enabled and forced, and a policy whose `USING` and `WITH CHECK` filter by the session's tenant.** (`MT-2`) Decided by review of the migrations and by a catalogue query in the integration test.
3. **The tenant is set for the transaction at the use-case edge (`SET LOCAL` or `set_config(..., true)`), and no adapter's hand-written tenant filter stands in place of the policy.** (`MT-3`) Decided by review of the unit of work and the adapters.
4. **Every tenant table has an integration test in which one tenant fails to read, change or delete another's rows.** (`MT-4`) Decided by the test. This condition holds on every database, with or without RLS.
5. **The application connects with a role that is not a superuser, has no `BYPASSRLS` and does not own the tables; migrations run under a different role.** (`MT-5`) Decided by review of the connection configuration and by a check in the integration test.

## Where this stops

**A database without RLS.** SQLite, MySQL, MongoDB and DynamoDB have no row policy of PostgreSQL's kind. There the decision record of condition 1 records the alternative from `docs/multi-tenancy.md`, conditions 2, 3 and 5 are replaced by what that record says, and condition 4 still holds.

**Application access control.** Whether a user may act on a record of their own tenant is `ahrena-engineering-security:reviewing-access`.

**A strategy already recorded that is not RLS.** Condition 1 proposes; the maintainer decides. A project that recorded another strategy keeps it, and conditions 2 to 5 are read against that record.
