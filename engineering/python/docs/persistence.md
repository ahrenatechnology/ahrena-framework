---
id: persistence
type: doc
clade: engineering
subclade: python
title: SQLAlchemy behind a port
summary: Why an ORM model is not a domain value and a repository maps between the two, where the unit of work begins and ends and why a repository flushes but never commits, what the async session needs, how a driver's error becomes something a use case can name, and what to read in an Alembic migration before it runs.
references:
  - docs/architecture.md
  - docs/libraries.md
  - docs/testing.md
  - rules/immutability.md
  - rules/error-handling.md
---

# SQLAlchemy behind a port

The persistence adapter is the repository behind a port that [`architecture.md`](architecture.md) puts in `application/ports.py`. [`libraries.md`](libraries.md) recommends SQLAlchemy in its 2.0 style, asyncpg under it for PostgreSQL, and Alembic for migrations, and says when each is wrong. This page is how they are used, carried from the predecessor's SQLAlchemy manual with its rules kept and argued, and two of its configuration lines turned into the reasons behind them.

## What the specification says

- **A query's values are bound by the driver, never formatted into the statement**: the DB-API, PEP 249, defines `paramstyle` and `execute(operation, parameters)` for exactly that. SQLAlchemy and asyncpg implement it.
- **A connection owns a transaction, closed by `commit()` or `rollback()`**: PEP 249, *Connection Objects*. The unit-of-work section is where this framework places those two calls.
- **`async with` closes a resource on every exit, normal or not**: Language Reference §8.5 (*The with statement*) and §8.9.3 (*The async with statement*), PEP 492.

## An ORM model is not a domain value

The mapped class — `class OrderRow(Base)` with `Mapped[...]` columns — lives in `infra/` and describes a table. The domain's `Order` is a frozen dataclass that describes the business's idea of an order. They are two types on purpose.

A mapped class is mutable by construction, tracks its own changes against a session, loads relationships lazily, and carries columns the domain does not care about: a soft-delete stamp, a row version, a tenant key. Handing it to the domain hands the domain all of that, and a use case that changes an attribute has written to the database at the next flush without saying so. [`rules/immutability.md`](../rules/immutability.md) keeps the domain's records frozen, and an ORM instance would be the one record it cannot see.

So the repository maps: `_to_row` on the way in, `_to_domain` on the way out, private and beside each other so a column added to one is visibly missing from the other. The mapping is the cost of the separation, and it is paid in one file per aggregate.

## The repository flushes; the boundary commits

A repository method adds, changes or deletes through the session and calls `flush()` when it needs the database to have seen the change — to get a generated key, or to surface a constraint violation now rather than at commit. It never calls `commit()`.

The transaction belongs to the unit of work, and the unit of work is the use case's call: everything one business operation writes either lands together or not at all. The edge opens it — `async with session.begin():` in the dependency that yields the session, or around the use case call in a job handler — and the context manager commits on a normal exit and rolls back on an exception. This is condition 2 of the fundamentals cross-cutting-concerns rule from the other side: a function that both commits and rolls back owns the boundary as well as the work, and the fix is to let the body raise and let the boundary decide.

A use case that needs two transactions — write, call an external service, write again — is two use cases or an outbox, never a repository that commits halfway.

## What the async session needs

**`expire_on_commit=False` on the session factory.** By default a commit expires every loaded attribute so the next access reloads it. In async code that next access is an implicit I/O call outside an `await`, which SQLAlchemy refuses with an error. Turning expiry off keeps the values the transaction saw, which is what a repository that has already mapped them to domain values wants.

**No lazy loading.** A relationship touched outside a query is a lazy load, and the same refusal applies. Load what a use case needs in the query — `selectinload`, `joinedload` — or declare the relationship `lazy="raise"` so a missed load fails in a test instead of in production.

**`pool_pre_ping=True`, or a pool recycle shorter than the server's idle timeout.** A connection the server closed while it sat in the pool fails on its next use; pre-ping tests it first, at the cost of a round trip. Which of the two a service needs depends on its traffic and its database's settings, and is the service's to decide. What is not optional is deciding.

**The connection string is a setting**, read through the settings model [`libraries.md`](libraries.md) recommends, never a literal: SEC-1 of the security plugin.

## Queries are bound, always

Every value reaches the database as a bound parameter: `select(OrderRow).where(OrderRow.id == order_id)`, or `text("... WHERE status = :status")` with the value passed separately. A value formatted into a statement string is INP-1, and `text(f"...")` is the shape it takes in SQLAlchemy. An identifier that genuinely varies — a sort column — is looked up in a dictionary of allowed columns and the lookup's result is used, which is the exemption INP-1 itself gives.

Lists are paged by a cursor, not an offset, wherever the table grows: `WHERE id > :cursor ORDER BY id LIMIT :n` costs the same on page one thousand as on page one, and an offset does not.

## A driver's error becomes something a use case can name

`IntegrityError` from a unique constraint is the database saying "this already exists", and the use case cannot catch that without importing SQLAlchemy, which the layering forbids. The repository catches the narrow error it can interpret, checks that it is the constraint it expects, and raises the domain's or the port's exception for it — `OrderAlreadyExists` — with `raise ... from exc`, so the cause stays on the traceback. What it cannot interpret it lets through. A repository that catches `SQLAlchemyError` and returns `None` has told the use case the order does not exist when the database was down, which is the swallowed failure condition 5 of the typing rule and REL-4 of the reliability plugin both read.

## Migrations

One Alembic revision per logical schema change, with a name that says what it does. Autogenerate drafts it from the difference between the mapped classes and the database, and it is a draft:

- **Read the SQL it will run** (`alembic upgrade head --sql`, offline mode), because autogenerate cannot see a rename and writes it as a drop and an add, which loses the column's data.
- **Write `downgrade()`, or say in the revision why it cannot exist.** A dropped column cannot be restored by a downgrade; a migration that drops data is REL-7 in the reliability plugin, and its reversal is a backup and a decision, not a function.
- **Split a destructive change across releases.** Add the new column, deploy code that writes both, backfill, deploy code that reads the new one, then drop the old one. Each step is reversible on its own; the one-step version is not.
- **Run the migrations against the real engine in the pipeline**, from an empty database to head, which is where the backend plugin's OLTP layer is tested. SQLite accepts DDL PostgreSQL refuses and refuses DDL PostgreSQL accepts.

## Testing the repository

Against a real database, never a double: the test-first skill in the backend plugin says so for the OLTP layer, and [`testing.md`](testing.md) shows the fixture that opens a transaction per test and rolls it back, so each test starts from the migrated, empty schema. A repository test asserts the round trip — what was saved comes back equal — and the failure translation: the duplicate raises the named exception.

## Where this stops

**It does not model the schema.** Which tables, which keys, which constraints: the data contract and the aggregate boundaries decide that, in the data plugin and the fundamentals aggregates rule.

**It does not cover analytical queries.** A report scanning millions of rows does not belong in a repository that maps rows to domain objects; [`libraries.md`](libraries.md) sends that work elsewhere.

**It does not pin pool sizes.** The predecessor set ten connections and twenty overflow, with no measurement behind either. A pool's size is the database's connection limit divided among the processes that share it, and that division is the deployment's, not a document's.

**It does not decide soft deletion.** The fundamentals domain-model rule keeps the deleted-at stamp out of the domain contract because it is a storage decision; whether a repository filters on it is the adapter's choice, made once per aggregate.
