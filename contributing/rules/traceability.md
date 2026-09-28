---
id: traceability
type: rule
clade: contributing
title: Every acceptance criterion is traced to a test
statement: Every issue a pull request closes lists numbered criteria, a test names each one that is not checked by review, and no test names a criterion that is not there.
enforcement: hook
enforced-by: hooks/check-traceability.py
enforced-in: forge
---

# Every acceptance criterion is traced to a test

Three conditions, all decided by `hooks/check-traceability.py`. The criteria are read from each issue's body, which is their only home (this repository's `ADR-007`), and the tests from the checkout. Without a token all three are reported unchecked rather than failed.

A criterion is written in the issue under `## Acceptance criteria` as `AC-<n>: <behaviour>`, and `skills/writing-acceptance-criteria` gives the shape. A test names the criterion it covers with the token `#<issue>/AC-<n>`, anywhere in the file and in any language. This is the "trace to a requirement" family of correctness, which #34 registered as its Q9 and waits on this rule for.

## Conditions

Each of these is decided by `hooks/check-traceability.py`.

1. **Every issue the pull request closes lists its criteria, numbered without gaps or repeats.** The issues are the ones the body closes with a keyword, and any the forge will close through a linked branch. The body is read as `pr-quality.md` reads it, because it is the text that lands on trunk. GitHub's own list is empty for a layer of a stack, even once the layer is based on trunk, and fills only when it merges. So the body is the record. An issue with no `Acceptance criteria` heading fails, and so does a heading with no items under it. So does a list that skips a number or uses one twice. A dropped criterion stays in the list, marked `(removed: why)`, so its number is never reused.

2. **Every live criterion of those issues is named by a test in the tree.** A criterion is live unless it is removed or ends with `(checked by review)`. A file counts as a test when a directory in its path is named `test`, `tests`, `spec`, `specs` or `__tests__`. It also counts when its name marks it as one: `test_x`, `test-x`, `x_test`, `x-test`, `x.test` or `x.spec`, with any extension. A token in any other file, a document or a comment in source, names nothing.

3. **Every criterion a changed test names exists and has not been removed.** Only the test files this pull request changes are read for this. A name in an old test pointing at a criterion that was later removed is found when somebody touches that test, not in every pull request after.

## Where this stops

**A name is not a proof.** The token says which criterion a test is meant to cover. Whether the test asserts the behaviour the criterion describes, or passes at all, is not read here. The quality gate runs the tests; a reviewer judges whether they prove the criterion.

**`(checked by review)` is the author's claim.** It is how a criterion no test can decide leaves the trace honestly: a decision recorded, a document written, a gate passed. It is also how a criterion somebody did not want to test leaves it. The detector cannot tell those apart, and a reviewer can.

**Only the issues a pull request closes are traced.** A pull request with `Part of #N` and no closing keyword traces nothing, because it finishes nothing. The criteria of #N are traced by the pull request that closes it, over the tree as it is then.

**The test-file conventions are the common ones, not every one.** A project whose tests live somewhere these patterns do not reach sees condition 2 fail on criteria its tests do name. The patterns grow when a real layout needs them, with the case that forced it.

**The criteria are read when the check runs.** Editing an issue changes what its pull request is held to, and the next run reads the edit. The issue's edit history is the only record of the change, which `ADR-007` accepts as the cost of one home.

**A pull request that closes an issue from before this rule inherits it.** Such an issue has no criteria section and fails condition 1 until somebody writes one. That is intended: closing an issue is claiming it is done, and done has to be written down to be claimed.
