---
id: frontend-quality
type: doc
clade: engineering
subclade: frontend
title: Where the frontend limits come from
summary: The source of each frontend threshold, whether a standard, a standard read through a tool, a consumer file or maintainer policy, and how the six rules fit the epic's catalogue.
references:
  - rules/accessibility.md
  - rules/screen-fidelity.md
  - rules/design-system.md
  - rules/screen-text.md
  - rules/density.md
  - rules/themes.md
---

# Where the frontend limits come from

A limit that nobody can trace is a number someone will argue with. Each one in the six rules is one of four kinds: from a standard, from a standard read through a tool, read from a file the consumer provides, or declared maintainer policy (#34). This is the ledger. The catalogue is the first comment of epic #323; a condition keeps its id there.

## The ledger

| Id | Limit | Kind | Source |
|---|---|---|---|
| A11Y-1 | 0 serious or critical violations | Standard, through a tool | WCAG 2.2 A and AA, as encoded in the axe-core rules |
| A11Y-2 | score of at least 95 | Maintainer policy | Lighthouse accessibility audit, built on axe-core |
| A11Y-3 | keyboard, no trap | Standard | WCAG 2.2 SC 2.1.1 and 2.1.2 |
| A11Y-3 | focus visible, not obscured | Standard | WCAG 2.2 SC 2.4.7 and 2.4.11 |
| A11Y-3 | text contrast 4.5:1, controls 3:1 | Standard | WCAG 2.2 SC 1.4.3 and 1.4.11 |
| A11Y-3 | target of at least 24 by 24 px | Standard | WCAG 2.2 SC 2.5.8 |
| UI-1 to UI-3 | 100% of screens and states | Maintainer policy | Wireframe-first, with a tolerance each project declares |
| DS-1, DS-2, BRD-1 | 100% from tokens, library and brand files | Maintainer policy | The consumer's `docs/brand/` |
| VOZ-1 | 0 lint errors | Consumer's file | The tone-of-voice lint file the consumer provides |
| VOZ-2 | 3, 6 and 20 words | Maintainer policy | Usability: fewer words |
| VOZ-3 | 0 filler occurrences | Maintainer policy | Usability: no AI filler on screen |
| DEN-1, DEN-2 | 32 px rows, 1280 by 800 | Maintainer policy | Density for daily-use screens |
| THM-1 to THM-3 | both themes, 100% | Maintainer policy | Photosensitivity; contrast per theme under WCAG 2.2 SC 1.4.3 |

Maintainer policy is a decision, not a measurement. It can change by a decision record that replaces it, and until then it binds.

## Why both themes are not an extra

A person with photosensitivity can find a light screen painful across a working day. For that person the dark theme is how the product is usable at all, which puts it with accessibility, not with taste. That is why the theme conditions apply to every accessibility and visual-regression run, not only to a manual toggle: a theme that is never tested is a theme that drifts into failing the contrast limits.

## Why the voice is the consumer's

The framework can say that screen text is checked against a voice and how long it may be. It cannot say how a company sounds without becoming that company's voice, which would make the framework unusable for the next consumer. So the conditions read a file the consumer provides, and a project without one fails the check rather than passing for lack of rules.

## Where this stops

**It records sources, not the detectors.** Detectors for each condition are the frontend detectors of #323 (#333 and, for accessibility and screen fidelity, an issue not yet opened).

**It does not restate the rules.** When this ledger and a rule disagree, the rule wins and this doc is the one to fix.

**A policy on a tool is not a standard.** Lighthouse's 95 is maintainer policy chosen on top of a tool, and the ledger says so, so nobody mistakes it for a WCAG threshold.
