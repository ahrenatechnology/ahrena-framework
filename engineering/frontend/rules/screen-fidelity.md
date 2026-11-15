---
id: screen-fidelity
type: rule
clade: engineering
subclade: frontend
title: The screen is the approved wireframe
statement: Every screen, state and flow a pull request ships has an approved wireframe, exists in code with a test, and renders within tolerance of that wireframe.
enforcement: judgment
references:
  - docs/frontend-quality.md
---

# The screen is the approved wireframe

[`wireframe-first`](wireframe-first.md) fixes the order: the wireframe is approved before code. This rule fixes the other end: what the pull request ships is what was approved, with nothing missing and nothing added. The catalogue ids (UI-1 to UI-3) are those of epic #323.

## Conditions

1. **UI-1: every screen, state and flow in the pull request has a wireframe approved in the team's UX/UI design tool, and the pull request links it.** Threshold: 100% of screens. An Artifact is the preferred form. Decided by the detector reading the link in the pull-request body and the approval record in the tool; a screen with no link, or a link with no approval, is a failure.
2. **UI-2: every state the wireframe draws (empty, loading, error, full, no permission) exists in code and has an end-to-end test.** Threshold: 100% of the drawn states, one test each. Decided by the end-to-end suite, which names each state it covers; a drawn state with no test fails.
3. **UI-3: the rendered screen matches the approved wireframe.** Threshold: visual difference within the tolerance the project declares, in both themes ([`themes`](themes.md) condition 3). Decided by visual regression comparing a capture of each state with the wireframe.

## Where this stops

**It reaches a screen the pull request adds or changes.** A screen the pull request does not touch is not re-checked; the legacy is held by the ratchet, not by this rule.

**UI-1 is a record, not a taste test.** The detector sees that an approval exists and who gave it; it does not see whether the owner should have approved. That stays with [`wireframe-first`](wireframe-first.md) condition 2.

**UI-3 compares structure and states, not final pixels.** [`wireframe-first`](wireframe-first.md) approves a wireframe on its structure. The tolerance is the project's to set, because a wireframe is not a visual design; a tolerance so wide that nothing fails is a review finding.

**The detectors are not in this rule.** They are the frontend detectors sub-issue of #323. Until they exist, a reviewer reads each condition against the pull request, which is why the enforcement is `judgment`.
