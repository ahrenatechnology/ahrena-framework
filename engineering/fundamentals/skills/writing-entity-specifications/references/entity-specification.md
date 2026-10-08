# Entity specification

The skeleton step 3 copies, the prompt for each part, and a filled example.
Everything between the rules is the specification; the rules are not part of it.

Save it as `docs/<context>/entities/<entity>.md`. Text in braces is what you
replace, and the hook fails any brace pair left outside code.

---

# {EntityName}

- **Classification:** {aggregate root, entity or value object}
- **Context:** {context}

## Why it exists

{Two to four sentences, in the words of somebody who does this business.}

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| {field} | {type} | {yes or no} | {what it holds} |

## Invariants

- **INV-1:** {a condition that is true in every state}

## Business rules

- **BR-1:** {what one operation or transition requires or refuses}

## Relationships

| Relation | Target | Cardinality | Held as | Note |
|---|---|---|---|---|
| {owns or refers to} | {OtherEntity} | {1, 0..1 or 1..n} | {part or identity} | {why} |

## Events

| Event | Emitted when | Carries |
|---|---|---|
| {FactInThePast} | {the transition that produces it} | {identity, time, payload} |

## Errors

| When | Rule | What the caller is told |
|---|---|---|
| {the attempt that is refused} | {INV-n or BR-n} | {the reason, in the caller's terms} |

---

## The heading and the header lines

**The heading** is the entity's name as the domain says it, one PascalCase word,
with no prefix. The filename is the same name in kebab-case.

**Classification** is `aggregate root`, `entity` or `value object`. A root is
what the outside addresses and what a transaction changes. An entity is reached
through its root, so add `- **Aggregate:** Order` under `Context` to say which.
A value object has no identity; its `Events` and `Errors` usually read `None`.

**Context** is the name of the directory the file sits in, exactly.

## The seven sections

A section with nothing to say keeps its heading and reads `None`, with the
reason when it is not obvious.

**Why it exists** is the business problem, not the schema. If it could be
written by reading the table below it, it has not been written yet.

**Fields** are named and typed in the domain's vocabulary. A type is another
entity, a value object, or a plain kind with its bound: `text, at most 140`,
`instant`, `one of draft, sent, paid`. A column type or a serialisation format
is condition 2 of `rules/domain-model.md` failing in a document. A root lists
its identity as one field, and a persisted entity lists the four audit fields
of condition 3. No real customer, account or person appears in an example.

**Invariants** hold at every commit and admit no exception. Number them `INV-1`
upward and never renumber. Each names only what is inside this aggregate; one
that needs a second root is condition 1 of `rules/aggregates.md` speaking, and
step 4 of the skill says what to do with it.

**Business rules** govern one operation or one transition, and may depend on the
state it starts from. Number them `BR-1` upward. One sentence each, in domain
language: no query, no status code.

**Relationships** say `part` when the target exists only inside this aggregate,
and `identity` when it is another aggregate, held as that root's identifier by
condition 3 of `rules/aggregates.md`.

**Events** are facts in the past tense that leave the boundary. Each carries the
root's identity and the time it happened, and no entity, by conditions 5 and 6
of `rules/aggregates.md`. The wire shape is the contract's, under
`docs/<context>/contracts/`; name the event here and do not copy its payload.

**Errors** has one row per rule a caller can trip, citing the `INV` or `BR` it
enforces. The code vocabulary is the project's; the row says when and why.

## A filled example

Saved as `docs/billing/entities/subscription.md`. It is an example, not a model
to adopt.

---

# Subscription

- **Classification:** aggregate root
- **Context:** billing

## Why it exists

A customer's standing agreement to pay for a plan, period after period, until
one side ends it. It separates the agreement from the invoices raised under it,
so that a plan can change or a payment fail without rewriting what was already
billed.

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | SubscriptionId | yes | The identity the outside addresses. |
| `customer_id` | CustomerId | yes | Who agreed to pay. |
| `plan` | Plan | yes | What is being paid for in the current period. |
| `status` | one of trialing, active, cancelled | yes | Where the agreement stands. |
| `current_period` | Period | yes | The start and end of the period now running. |
| `cancelled_at` | instant | no | When the agreement ended. |
| `created_at`, `created_by` | instant, ActorId | yes | Audit stamp: creation. |
| `updated_at`, `updated_by` | instant, ActorId | yes | Audit stamp: last change. |

## Invariants

- **INV-1:** `current_period` ends after it starts.
- **INV-2:** `cancelled_at` is set exactly when `status` is `cancelled`.
- **INV-3:** A cancelled subscription never changes status again.

## Business rules

- **BR-1:** Only a `trialing` or `active` subscription can change plan.
- **BR-2:** A plan change takes effect when the next period starts.
- **BR-3:** A trial becomes `active` when its first paid period starts.

## Relationships

| Relation | Target | Cardinality | Held as | Note |
|---|---|---|---|---|
| owns | Plan | 1 | part | A value, replaced whole on a plan change. |
| owns | Period | 1 | part | A value. |
| refers to | Customer | 1 | identity | Another aggregate, with its own lifecycle. |

## Events

| Event | Emitted when | Carries |
|---|---|---|
| SubscriptionActivated | a trial becomes active | subscription id, time, plan |
| SubscriptionPlanChanged | a new plan takes effect | subscription id, time, old and new plan |
| SubscriptionCancelled | the agreement ends | subscription id, time |

## Errors

| When | Rule | What the caller is told |
|---|---|---|
| a plan change on a cancelled subscription | BR-1 | The subscription has ended and cannot change plan. |
| any change to a cancelled subscription | INV-3 | The subscription has ended. |

---

## What is deliberately absent

**No base fields every entity repeats.** An identifier format, a version counter
and a soft-delete marker are one project's entity contract. What a root and a
persisted entity owe is in `rules/domain-model.md`, and it is four audit fields
and an identity.

**No storage, no endpoint list, no payloads.** Those are derived from this
document or specified beside it, and a copy here is the copy that goes stale.

**No state diagram section.** A lifecycle is the `status` field, the business
rules that move it and the events that announce it. A diagram may be added
under `Business rules`; it replaces none of the three.
