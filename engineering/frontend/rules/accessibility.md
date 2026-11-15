---
id: accessibility
type: rule
clade: engineering
subclade: frontend
title: Every state is accessible
statement: Every state of every screen has no serious or critical axe violation (WCAG 2.2 AA), scores 95+ on Lighthouse, and meets keyboard, contrast and target limits.
enforcement: judgment
references:
  - docs/frontend-quality.md
---

# Every state is accessible

Accessibility is measured on the rendered state, not on the source, and against one standard: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) at level AA. Each threshold below names the success criterion it comes from. The catalogue ids (A11Y-1 to A11Y-3) are those of epic #323.

## Conditions

1. **A11Y-1: no serious or critical violation in any state.** Threshold: 0 violations of impact `serious` or `critical`, measured against the WCAG 2.2 A and AA rules the checker carries. Decided by axe-core run on each state of each screen, in both themes ([`themes`](themes.md) condition 3).
2. **A11Y-2: the accessibility score of each page is 95 or more.** Threshold: at least 95. This is maintainer policy (#34), a proxy for WCAG 2.2 conformance built on the same axe rules as condition 1. Decided by Lighthouse on each page, in both themes.
3. **A11Y-3: everything operates by keyboard alone, with visible focus, enough contrast and a target large enough to hit.** Four limits, all at 100% of the elements they apply to:
   - every function works from the keyboard, with no trap (WCAG 2.2 SC 2.1.1 Keyboard, A; SC 2.1.2 No Keyboard Trap, A);
   - focus is visible and not hidden behind other content (SC 2.4.7 Focus Visible, AA; SC 2.4.11 Focus Not Obscured (Minimum), AA);
   - text contrast is at least 4.5:1 (SC 1.4.3 Contrast (Minimum), AA), and the boundary of a control and the focus indicator at least 3:1 (SC 1.4.11 Non-text Contrast, AA);
   - the pointer target is at least 24 by 24 CSS pixels (SC 2.5.8 Target Size (Minimum), AA).

   Decided, in both themes ([`themes`](themes.md) condition 3), by an end-to-end keyboard test that activates each interactive element with Enter or Space and asserts its effect, asserts Tab leaves every element, and asserts the focused element is not fully covered; and by axe configured at 4.5:1 for all text, for contrast and target size.

## Where this stops

**Flashing content is not decided here.** WCAG 2.2 SC 2.3.1 (Three Flashes or Below Threshold, A) has no condition above; a reviewer reads flashing content against it.

**An automated checker finds only part of what WCAG asks.** axe and Lighthouse cannot judge whether alt text is meaningful or a reading order makes sense. A pass is the floor, not conformance, and a reviewer still reads what a person using a screen reader would hear.

**Target size keeps the exceptions of SC 2.5.8 as axe applies them.** Spaced targets, inline links and the others are not failed by the detector; a reviewer reads whether the exception is real.

**Large text has a lower contrast bar in WCAG, and this rule does not use it.** SC 1.4.3 allows 3:1 for large text. The limit stays at 4.5:1 for all text so the detector needs no judgment about what counts as large.

**The score in condition 2 is a number, not a standard.** A page can score 95 with a keyboard trap that axe cannot see; condition 3 exists for that reason, and neither replaces the other.

**It reaches states the pull request adds or changes.** The legacy is held by the [ratchet](../docs/frontend-quality.md#the-ratchet): a total that gets worse blocks, an old violation does not.

**The detectors are not in this rule.** They belong to the frontend detectors of #323 (#333 for copy, density, themes and tokens; accessibility and screen-fidelity detectors have no issue yet), so the enforcement is `judgment` until they land.
