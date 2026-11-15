---
id: density
type: rule
clade: engineering
subclade: frontend
title: Screens are dense and show the main thing at once
statement: Spacing uses the compact token scale, rows are at most 32 px, nothing is decorative, and the main information shows at 1280 by 800 unscrolled.
enforcement: judgment
references:
  - docs/frontend-quality.md
---

# Screens are dense and show the main thing at once

A working screen is read many times a day; every empty block costs a scroll. The catalogue ids (DEN-1, DEN-2) are those of epic #323. Both limits are maintainer policy (#34), set against the target size floor of WCAG 2.2 SC 2.5.8 (24 by 24 CSS pixels), which a 32 px row clears.

## Conditions

1. **DEN-1: spacing is from the compact scale, rows are short and nothing is decorative.** Threshold: spacing values only from the compact scale of the tokens; list and table rows at most 32 px high; 0 decorative empty areas (a hero, an illustration, a welcome card). Decided by stylelint over the styles against the tokens (a tokens file with no compact scale fails), by a measurement in the end-to-end suite for row height, and by a search for the decorative patterns.
2. **DEN-2: the main information of each screen is in view without scrolling at 1280 by 800.** Threshold: 100% of screens. The project names, per screen, the element that is the main information; a screen that names none fails. Decided by an end-to-end test at 1280 by 800 that asserts that element is inside the viewport.

## Where this stops

**A row of at most 32 px does not license a target smaller than 24 px.** [`accessibility`](accessibility.md) condition 3 still holds inside a dense row.

**A decorative area is one that carries no information or action.** An empty state that tells the person what to do next is information, and [`screen-fidelity`](screen-fidelity.md) condition 2 requires it; a welcome card that only greets is not.

**DEN-2 reads one element per screen.** It does not say the rest of the screen fits; a long table below the fold is fine. Which element is the main one is the project's declaration, and a reviewer checks it is the right one.

**It reaches new and changed screens.** The legacy is held by the ratchet of the catalogue in #323 (limits bind new lines, and a total getting worse blocks).

**The detectors are not in this rule.** They belong to the frontend detectors of #323 (#333 for copy, density, themes and tokens; accessibility and screen-fidelity detectors have no issue yet), so the enforcement is `judgment` until they land.
