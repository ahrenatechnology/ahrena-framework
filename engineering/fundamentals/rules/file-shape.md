---
id: file-shape
type: rule
clade: engineering
subclade: quality
title: One problem per file
statement: A source file exports one public concept and is named after it; a file over 300 lines is reported as an indicator, not a failure.
enforcement: judgment
---

# One problem per file

Two conditions. A file that holds one concept is found by its name, changes for one reason and is reviewed in one reading. The first condition decides that; the second is a size indicator that points at files probably breaking the first.

## Conditions

1. **CLN-15. A source file exports one public concept, and the file is named after it.** A concept is a class, a type together with the functions that operate on it, or a function. The state that is a finding is a file with two or more exported concepts that are not one type and its own functions, or a file whose name differs from its single concept's name once case and separators are normalised (`order-total.ts` holds `orderTotal`). Threshold: 1 concept per file. Detector: a script over the exports of each file added or changed; the TypeScript detector is owned by the clean-code detectors issue #330. A re-exporting index file exports no concept of its own and is not counted.

2. **CLN-16. A source file is at most 300 lines.** Threshold: 300 lines, declared maintainer policy recorded under #34. The finding is a file this change adds or grows above 300 lines whose pull request description does not say in one line why it is one problem; the author owes that line. A file above the limit with the line is reported as an indicator and passes, because a file can be long for one good reason.

## Where this stops

**CLN-15 does not reach a file of tests.** A test file is named after the unit it tests and holds many cases by design; the condition applies to production source.

**CLN-15 does not reach a language where the file is not the unit.** In a language whose convention is several types per module, the project's component map names the unit and the rule follows it.

**One concept is not one export statement.** A type with its constructor, its guards and its pure functions is one concept; two unrelated types exported from one file are two, however short.

**CLN-16 counts lines, [`clean-code.md`](clean-code.md) condition 1 counts statements.** The two answer different questions, and a file can pass one and fail the other.

**This rule declares judgment because no detector ships yet.** It moves to `hook` in the change that lands the script.
