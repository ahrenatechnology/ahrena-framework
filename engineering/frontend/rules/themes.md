---
id: themes
type: rule
clade: engineering
subclade: frontend
title: Both themes, always
statement: Every screen works in the dark and light themes, every colour token has a value in both, and accessibility and visual-regression checks run in both.
enforcement: judgment
references:
  - docs/frontend-quality.md
---

# Both themes, always

The dark theme is an accessibility requirement, not a developer preference: for a person with photosensitivity a light theme strains the eyes through the working day. A light-only screen, or a dark theme that was never checked, excludes them. The catalogue ids (THM-1 to THM-3) are those of epic #323.

## Conditions

1. **THM-1: every screen works in both themes, follows the system setting by default and keeps the person's manual choice.** Threshold: 100% of screens. The default is `prefers-color-scheme`; a choice the person makes is stored and wins over the system setting on the next visit. Decided by the end-to-end suite run once per theme, including a case that sets the manual choice and reloads.
2. **THM-2: every colour token has a value in both themes.** Threshold: 100% of colour tokens; no colour exists in only one. Decided by validating `docs/brand/tokens.json` for a dark and a light value on each colour token.
3. **THM-3: the accessibility and visual-regression checks run in both themes.** Threshold: 100% of the runs that [`accessibility`](accessibility.md) and [`screen-fidelity`](screen-fidelity.md) require, once per theme. Decided by the CI job matrix: a run of axe, Lighthouse or capture comparison that exists for one theme and not the other fails.

## Where this stops

**Contrast is judged per theme, not once.** The 4.5:1 and 3:1 limits of WCAG 2.2 SC 1.4.3 and SC 1.4.11 hold in each theme separately; a token pair that passes in light and fails in dark fails.

**It reaches new and changed screens and tokens.** The legacy is held by the [ratchet](../docs/frontend-quality.md#the-ratchet).

**This rule does not ask for a third theme.** High-contrast or branded variants are the project's choice, and a project that adds one adds it to the matrix in condition 3.

**Photosensitivity has a second limit that a theme cannot fix.** Content that flashes more than three times a second is WCAG 2.2 SC 2.3.1 (Three Flashes or Below Threshold, A) and is not decided by any condition of this plugin's frontend rules, and a reviewer reads flashing content against it.

**Images and user content are not themed by this rule.** A photograph stays as it is; a logo variant per theme comes from the brand files ([`design-system`](design-system.md) condition 3).

**The detectors are not in this rule.** They belong to the frontend detectors of #323 (#333 for copy, density, themes and tokens; accessibility and screen-fidelity detectors have no issue yet), so the enforcement is `judgment` until they land.
