---
id: screen-text
type: rule
clade: engineering
subclade: frontend
title: Screen text is short, in the brand voice and free of filler
statement: Screen text passes the consumer's tone-of-voice lint, stays within the word limits for its role, and carries no AI filler.
enforcement: judgment
references:
  - docs/frontend-quality.md
---

# Screen text is short, in the brand voice and free of filler

Fewer words is the usability bet: a person scanning a dense screen reads a label, not a paragraph. The catalogue ids (VOZ-1 to VOZ-3) are those of epic #323. The text in question is what the person sees, in pt-BR or the product's language; names behind the scenes follow the project's own convention.

The framework ships the shape of the voice check and no voice. VOZ-1 reads a tone-of-voice lint file that the consumer provides (see #54); the framework never decides how a consumer sounds.

## Conditions

1. **VOZ-1: screen text passes the consumer's tone-of-voice lint.** Threshold: 0 errors. The lint file carries a list of forbidden terms and a list of preferred terms, and the project names where it lives. Decided by Vale, or the equivalent the project chose, run on the screen strings. A project with no lint file fails this condition: absence is not a pass.
2. **VOZ-2: text stays within the limit for its role.** Threshold: a button or label has at most 3 words, a title at most 6, supporting text at most 20, and no screen carries an explanatory paragraph. These limits are maintainer policy (#34). Decided by a word count over the screen strings, by role, where the role is the one the string key declares (button, label, title, support). Legal text is marked in the strings file with a `legal` role.
3. **VOZ-3: no AI filler.** Threshold: 0 occurrences. The framework owns only the language-neutral baseline: a decorative emoji, an exclamation mark, and a string that repeats a label on the same screen. The consumer's lint file owns the rest: its list of enthusiasm phrases and filler words, in the product's language (the doc gives examples). Decided by the same lint as condition 1 for the lists, and by a duplicate-string check against the labels on the same screen for repetition. A lint file with no filler list fails this condition, as a missing file fails condition 1.

## Where this stops

**A triad of adjectives is read by a reviewer.** No pattern decides it without false alarms, so it is a review finding, not a detector failure.

**The lint fires on the word, not the use.** A forbidden term in a quotation, or inside a user's own data shown back to them, is not screen copy. The lint file lists its exemptions; a detector that fires too often teaches people to switch it off, which is a defect of the detector, not a licence to skip it.

**A word count is a proxy for effort.** Three words can still be unclear. The limit catches length, and clarity stays with the reviewer.

**Legal and regulatory text is exempt from the VOZ-2 length limits.** A required disclosure may be longer than 20 words; it still passes VOZ-1 and VOZ-3.

**Names behind the scenes are out of scope.** Identifiers, routes and keys are not screen text and are not counted.

**The detectors are not in this rule.** They belong to the frontend detectors of #323 (#333 for copy, density, themes and tokens; accessibility and screen-fidelity detectors have no issue yet), so the enforcement is `judgment` until they land.
