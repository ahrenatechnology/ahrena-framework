---
name: reviewing-access
description: Use when a change under review adds or edits an entry point, a token or session, a permission or role check, an ownership predicate, a webhook receiver or a cross-origin rule, and the question is who can now reach or act on what they should not - an anonymous caller, a user of another tenant, a user of the same tenant without the role.
type: skill
clade: security
references:
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md

---

# Reviewing access

One question: with this change, who that should not be able to can now reach an entry point, act on a record, or be believed about who they are? Three parties gain — an anonymous caller, a user of another tenant, and a user of the same tenant without the role.

The conditions are in `references/conditions.md`, identified `ACC-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

## 1. Take the route, and read the repository first

The `access` route fired on lines that authenticate, authorise, scope by owner, receive a webhook, or set a cross-origin rule. Before the checklist, read how this repository authenticates a caller and where the owner or tenant identity comes from — its `AGENTS.md`, its architecture document, the decision records. Where it wrote the answer, that outranks the checklist; where it did not and a condition needs it, the finding is a `question`.

## 2. Map the entry and the actor

For each changed handler, route, consumer or job, establish two things: can it be reached without authentication, and does what it does check that this actor may do it. Compare a new entry point with two existing ones of the same kind — the guard they pass through is the pattern.

## 3. Apply the conditions

Open `references/conditions.md` and read against ACC-1 to ACC-8: an unauthenticated entry, a token trusted unverified, a session that outlives its reason, a permission checked only in the interface, a record fetched by id with no owner predicate, a webhook taken at its word, a browser trusted across origins, an answer that tells the caller too much.

Read each condition's `Exempt` line: a documented public endpoint, a header-authenticated API, a response that distinguishes absent from forbidden only in a development mode.

## 4. Write the findings

Each finding names the party and what they gain, carries the four fields in `docs/review-findings.md` with the `ACC-n` identifier, and a correction that is an instruction.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**What is logged, returned, stored or encrypted.** A secret in a log, a response that serialises a whole record, a password stored recoverably, cryptography chosen by hand: those are `reviewing-sensitive-data` (DAT), its sibling discipline.

**Outside input reaching a sink.** Injection, path traversal, mass assignment: `reviewing-untrusted-input` (INP).

**A tool callable by a model with more authority than the asker.** That is `reviewing-model-use` (LLM-6), which reuses this skill's ownership conditions.
