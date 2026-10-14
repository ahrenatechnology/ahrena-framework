# ADR-015: Reliability and observability are the third and fourth review pillars

- **Status:** accepted
- **Date:** 2026-10-14

## Context

The review system was planned around four pillars — quality, security, reliability and observability — and shipped two of them. Quality is the engineering rules over the source; security is six lenses over what a change lets the wrong party do. Reliability and observability existed only as incidental touches: an async note here, a timeout mention there, no lens that asks the question whole.

A lens in this system is a specific shape. It is a skill with numbered conditions, each naming a detectable state, what exempts it and the correction, and it joins a review through a row in `engineering/quality/skills/reviewing-diffs/references/routes.json` rather than through any edit to Argos. The question was not whether to review reliability and observability — the four-pillar plan already answered that — but where the two lenses live and how they are packaged.

Observability in particular had a history. It was carried in the predecessor as `lex-observability-required` and refused from the foundation port as *"Engineering, not foundation (#13)"* — recorded as a row in this log's *Refused* table. That refusal said where it does not belong; it did not say where it does.

## Decision

Reliability and observability each become their own engineering plugin — `ahrena-engineering-reliability` and `ahrena-engineering-observability` — cataloged in the marketplace like every other. Each ships exactly one review lens: `reviewing-reliability` (REL-1 to REL-7) and `reviewing-observability` (OBS-1 to OBS-4), each a skill of numbered conditions with the same four-field shape the security lenses use.

They join the review as data. Two rows are added to `routes.json`, one per lens, each driven by regular expressions over the changed paths and the lines a change adds; nothing in Argos or in the review procedure changes, because the route table is the only place a lens edge lives. Observability's corrections are bound by one standing rule: they add context — identifiers, counts, the operation's name — and never a value, so the lens never corrects toward the leak that `reviewing-sensitive-data` (DAT-1) exists to catch.

## Consequences

The four-pillar plan is complete: a change now meets quality, security, reliability and observability on one base and head, merged into one verdict.

The cost is paid at install and at attention. Two more plugins exist for a consumer to install, which is the same free-composition trade every pillar-as-plugin makes. More visibly, both new routes carry wide line drivers — error handling opens reliability (for the swallowed error, REL-4) and observability (for the failure with no log, OBS-1) alike — so an ordinary diff that contains a `try`/`catch` now loads two more checklists than it did. That is the cost `docs/review-findings.md` and `docs/review-routes.md` already accept for wide drivers: a checklist that opens and finds nothing costs attention, and a driver written narrow enough to avoid that cost is a driver that misses the case the lens exists for.

The two lenses deliberately overlap at one point — a swallowed error is both unhandled (REL-4) and unrecorded (OBS-1) — and each names the other so a reviewer keeps them as two causes rather than merging them into one weaker finding.

## Alternatives considered

- **Fold the conditions into the existing security or fundamentals plugins.** Rejected: the plugin boundary carries the taxonomy (`ARCHITECTURE.md`), a pillar is a plugin, and composition stays free only when a consumer installs the pillar it wants instead of inheriting three it does not.
- **Put observability in foundation.** Rejected: it was refused there once already as engineering, not foundation. It reviews a codebase, not an artifact, so it belongs beside the other engineering lenses.
- **One combined "operability" lens covering both.** Rejected: the two ask different questions — is the failure handled, and is it recorded — and a finding under one is not the other. Two lenses keep findings precise, the way the security plugin's six do rather than one lens called "security".
- **Leave reliability and observability as judgment prompts inside Argos.** Rejected: a lens that is not a row in the route table cannot be selected by path, cannot be reported as not-selected when it does not fire, and cannot be reused by a consumer who installs the plugin without the orchestrator.
