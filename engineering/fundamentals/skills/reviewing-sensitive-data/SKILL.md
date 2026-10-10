---
name: reviewing-sensitive-data
description: Use when a change under review logs, serialises into a response, stores or transmits data, or chooses a cryptographic primitive, and the question is who can read a datum they should not - a secret or personal field in a log or trace, a whole record returned by default, a password stored recoverably, a hand-rolled cipher, data sent to a new recipient.
type: skill
clade: engineering
subclade: quality
references:
  - docs/review-findings.md
  - docs/review-routes.md
---

# Reviewing sensitive data

One question: with this change, does a datum become readable to someone who should not read it — in a log, in a response, in storage, in transit, or because the cryptography protecting it is weak? This is the sibling of `reviewing-access`: that skill decides who may act, this one decides who may read what the system keeps.

The conditions are in `references/conditions.md`, identified `DAT-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

## 1. Take the route, and read the repository first

The `sensitive-data` route fired on lines that log or trace, build a response, store a credential, or call a hash, cipher, signing or random primitive. Read what the repository treats as sensitive and which recipients its documents already name for which category of data, so DAT-5 is judged against that and not from scratch.

## 2. Follow the datum to where it rests or leaves

For each changed log call, response builder, storage write and outbound call, ask what fields the object actually carries. A whole record or request object handed to a logger or a serialiser carries every field it has, including the ones added later.

## 3. Apply the conditions

Open `references/conditions.md` and read against DAT-1 to DAT-5: sensitive data in a log or trace, a response that returns the whole record, a password or secret stored recoverably, cryptography chosen by hand, data sent to a new recipient.

Read each condition's `Exempt` line: an internal identifier that is not personal data, a response built from a field-naming schema, a fast hash used as a checksum with no security claim.

## 4. Write the findings

Each finding carries the four fields in `docs/review-findings.md` with the `DAT-n` identifier and a correction that is an instruction. Whether a recipient may receive a category of data at all is a `question` for the organisation, not a verdict this skill settles.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**Who may reach an entry point or act on a record.** Authentication, authorisation and ownership are `reviewing-access` (ACC).

**A credential written as a literal.** That is the baseline `reviewing-secrets` sweep (SEC-1 to SEC-4), which also covers a secret travelling into a log; this skill covers personal and business data that is not itself a credential, and the storage of credentials (DAT-3).

**Data placed into a model's context.** That is `reviewing-model-use` (LLM-3).
