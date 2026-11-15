---
id: design-system
type: rule
clade: engineering
subclade: frontend
title: Only design-system tokens, components and brand files
statement: New UI code takes colour, spacing, radius, shadow and type from tokens, elements from the design-system library, and logo, palette and fonts from brand files.
enforcement: judgment
references:
  - docs/frontend-quality.md
---

# Only design-system tokens, components and brand files

A screen that invents its own colour, spacing or button is a second design system. This rule keeps one. The catalogue ids (DS-1, DS-2, BRD-1) are those of epic #323. The brand files live under `docs/brand/` in the consumer, and the tokens in `docs/brand/tokens.json`; the framework names the place and ships no brand.

## Conditions

1. **DS-1: every colour, spacing, radius, shadow and type style in a new line comes from a token.** Threshold: 100% of new lines. Decided by a guard that rejects a hand-written colour literal and by a stylelint rule that rejects a value not in `docs/brand/tokens.json`.
2. **DS-2: only design-system components are used; a new component enters the design system first.** Threshold: 0 parallel components. Decided by a search for UI elements outside the library (a hand-built button, input or modal where the library has one).
3. **BRD-1: the logo, the palette and the fonts come only from the files in `docs/brand/`, without variation.** Threshold: 100%. Decided by comparing the logo, colour and font files the build ships with the brand files; a recoloured, stretched or substituted copy fails.

## Where this stops

**A token is checked by presence, not by fitness.** The guard sees that a value is a token; it does not see that the right token was chosen. A reviewer reads that.

**A component the library lacks is not a violation of DS-2 until it is built outside it.** The rule says where the new component goes, through the design system, not that it may not exist.

**A third-party widget that renders its own markup is read case by case.** The detector flags it; the project records the exception next to the component with the reason.

**It reaches new and changed lines.** Existing hand-written values are held by the [ratchet](../docs/frontend-quality.md#the-ratchet).

**The detectors are not in this rule.** They belong to the frontend detectors of #323 (#333 for copy, density, themes and tokens; accessibility and screen-fidelity detectors have no issue yet), so the enforcement is `judgment` until they land.
