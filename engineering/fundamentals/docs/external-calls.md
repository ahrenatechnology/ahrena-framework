---
id: external-calls
type: doc
clade: engineering
subclade: architecture
title: Why an external call is where a port is earned
summary: Why an external call satisfies the abstraction trigger and an internal one does not, what an adapter must translate, and where each threshold in the rule came from.
references:
  - rules/external-calls.md
  - rules/yagni.md
  - docs/solid.md
  - docs/simplicity.md
---

# Why an external call is where a port is earned

This is the companion to [`rules/external-calls.md`](../rules/external-calls.md). The maintainer's decision of 14 November 2026 is ports and adapters only where there is an external call, without forcing the pattern anywhere else. The rule is that decision written as conditions; this is the argument that it agrees with the abstraction trigger instead of contradicting it.

## How the conditions meet the trigger

[`docs/simplicity.md`](simplicity.md) explains the trigger of `rules/yagni.md`: an abstraction needs a second real consumer, or a test that exists today requiring the seam. An external call is the common case of the second branch.

- A use case that calls a payment vendor directly cannot be tested without the vendor. The unit test needs a double, and the double needs a type to stand behind. The test exists today, so the seam is justified.
- An internal call, one module reaching another in the same process, has no such test. The real module runs in the test, so no seam is required and a port would be the single-implementation interface the trigger inlines.

So condition 1 (ADP-1) puts the call in one place, condition 2 (ADP-2) points the dependency inward (the argument of [`docs/solid.md`](solid.md)), and condition 4 (ADP-4) deletes the port that never showed either branch. Condition 5 is the same trigger read from the other side: no external call, no port.

## What an adapter owes at the port

The port is the project's vocabulary; the vendor's is behind it. Condition 3 (ADP-3) asks the adapter to translate the vendor's error and types into the domain's, because a vendor error that crosses the port teaches every caller to match on it, and replacing the vendor then edits every caller. The translation produces the `Result` of [`result-errors.md`](result-errors.md). The vendor's own detail is not lost: the adapter attaches it to its span, which is the diagnostic home the telemetry rules name.

## Where the numbers came from

| Condition | Threshold | Source |
|---|---|---|
| ADP-1 | 0 external calls outside an adapter | declared maintainer policy (#34); the import-only check in `rules/domain-model.md` covers part of it |
| ADP-2 | 0 concrete imports from a use case | dependency direction of condition 6 of `rules/solid.md` |
| ADP-3 | 0 vendor types or errors across the port | declared maintainer policy, the translation condition of `rules/domain-model.md` |
| ADP-4 | 0 orphan ports | the abstraction trigger of `rules/yagni.md` |

## Where this stops

This document does not say which pattern an adapter takes, since [`pattern-selection`](patterns.md) decides that after the trigger is met, and it does not list a project's adapter paths, which are in its layer map.
