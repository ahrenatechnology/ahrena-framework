---
id: persistence-mode
type: rule
clade: engineering
subclade: database
title: Every Table Declares Its Mode, and Its Writes Keep It
statement: Every table is declared append-only, upsert-with-history or ephemeral; append-only is never changed, upsert writes versioned history in one transaction.
enforcement: judgment
references:
  - docs/entity-history.md
  - docs/database-capabilities.md
---

# Every Table Declares Its Mode, and Its Writes Keep It

A table of a transactional store is either a log of facts that is only appended to, or an entity that is changed in place and records every change; it says which in a versioned registry beside the migrations, and no write breaks what it says. Why, how a table's mode is chosen and where its history lives on each database are in [`docs/entity-history.md`](../docs/entity-history.md).

The conditions carry the quality rubric's identifiers (`PER-n`, ahrenatechnology/ahrena-framework#323). Until the rubric's detectors land they are decided by review, through `skills/reviewing-persistence/SKILL.md`, and by the integration tests some conditions name.

## Conditions

1. **Every table the migrations create is in the mode registry with the mode `append-only`, `upsert-with-history`, or `ephemeral` with its reason (see `Where this stops`).** (`PER-1`) Decided by review; the detector compares the registry with the tables the migrations create.
2. **No adapter issues `UPDATE` or `DELETE` (or the store's equivalent) against an append-only table, and the database refuses one where it can.** (`PER-2`) Decided by review of the adapters and the migration that grants or triggers the refusal.
3. **Every write to an upsert table writes, in the same transaction, one history record per change carrying the entity's identity, the version, when, who, and the state before or the whole state after.** (`PER-3`) Decided by review and by an integration test that changes the entity twice and finds two history records.
4. **An upsert table carries a version, and a write that states a version other than the stored one is refused.** (`PER-4`) Decided by review and by an integration test that writes with a stale version.
5. **No record is physically deleted: removal is an event on an append-only table or a deletion mark with its history row on an upsert table.** (`PER-5`) Decided by review of the adapters.
6. **The current state read from an append-only table is a projection with a test that rebuilds it from the log.** (`PER-6`) Decided by review: the test exists and rebuilds.
7. **A table's declared mode does not change unless the same change adds a decision record that supersedes the one behind it and migrates the rows already written.** (`PER-7`) Decided by review of the registry's diff.
8. **The registry declares where each table's history lives, in the shape `docs/entity-history.md` gives for the chosen database.** (`PER-8`) Decided by review against `docs/database-capabilities.md`.

## Where this stops

**Tables that are not the system's record.** A cache, a session, a lock, a queue's working table or a view rebuilt from the record is listed in the registry as `ephemeral` with its reason, and conditions 2 to 8 do not apply to it.

**The erasure of personal data.** A declared, audited erasure path, written in a decision record, is the one place allowed to make personal data unreadable; condition 5 does not forbid it, and forbids any other.

**Analytical stores.** A warehouse, a medallion layer or a mart is held to `ahrena-engineering-data`'s contract, not to this rule.

**Lookup tables.** An append-only table whose entry says `growth: fixed` holds rows only migrations write, such as a list of countries; it is read directly, and condition 6 does not apply to it.

**The migration tool's bookkeeping.** The table a migration tool keeps for itself (`alembic_version`, `schema_migrations`) is not in the registry; condition 1 does not apply to it.

**A migration's own statements.** The schema change that creates, alters or backfills a table is not an adapter's write; condition 2 reads the adapters.
