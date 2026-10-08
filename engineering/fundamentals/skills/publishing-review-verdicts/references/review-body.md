# Review comment body

The skeleton step 5 copies, followed by a filled example. Everything between
the rules is the body; the rules themselves are not part of it.

The order is fixed. A reader scanning three reviews should find the marker,
the verdict, the counts, the findings and the coverage statement in the same
places each time.

---

<!-- ahrena-review:PR-NUMBER:SHORT-SHA -->

**Verdict:** request changes | comment | approve — reviewed at commit `SHORT-SHA` against base `BASE-REF`.

**Findings:** N blocking · N deferrable · N question · N unchecked

## Blocking

| File and line | Rule and condition | Observed | Resolved by |
|---|---|---|---|

## Deferrable

| File and line | Rule and condition | Observed | Resolved by |
|---|---|---|---|

## Questions

| File and line | Rule and condition | What is missing | What would settle it |
|---|---|---|---|

## Not decided

| Condition | Why it was not decided |
|---|---|

---

## Filling it

**The marker line is first and it is an HTML comment**, so it does not render
and step 2 of the procedure can still find it on a re-run.

**Drop a section that is empty, except the last one.** A review with no
deferrable findings omits that heading. `Not decided` is always written; when
nothing was skipped its single row reads `none — every routed condition was
decided`. An absent coverage statement reads as full coverage, which is the
claim the whole procedure exists to avoid making by accident.

**Every row in the first three tables has all four cells filled.** A finding
that cannot name its file and line, its rule and condition number, the state
observed and the change that resolves it is not published short — it is
dropped, or rewritten as a question.

**Cite the condition by number.** `rules/kiss.md` condition 1, not
`rules/kiss.md`. The number is what turns a page into a sentence the author
can agree or disagree with.

## A filled example

---

<!-- ahrena-review:142:a1b2c3d -->

**Verdict:** request changes — reviewed at commit `a1b2c3d` against base `main`.

**Findings:** 2 blocking · 1 deferrable · 1 question · 5 unchecked

## Blocking

| File and line | Rule and condition | Observed | Resolved by |
|---|---|---|---|
| `src/billing/approve.py:45` | `rules/kiss.md` condition 1 | control flow nests 5 deep; the cap is 3 | lift the inner `for` into a named function |
| `docs/billing/openapi.yaml:88` | `rules/contract-first.md` condition 5 | `amount_cents` removed from the `Invoice` response, no version event in the change | restore the field, or ship the removal under a new version |

## Deferrable

| File and line | Rule and condition | Observed | Resolved by |
|---|---|---|---|
| `src/billing/repository.py:12` | `rules/cross-cutting-concerns.md` condition 2 | one function calls both `commit` and `rollback`; the line predates this change | let the body raise and leave the unit of work to the boundary |

## Questions

| File and line | Rule and condition | What is missing | What would settle it |
|---|---|---|---|
| `src/billing/ports.py:8` | `rules/yagni.md` condition 1 | `PricingProvider` has one implementation in the tree and no test binds a second | a second adapter, a test that fails without the seam, or a consumer outside this repository |

## Not decided

| Condition | Why it was not decided |
|---|---|
| `rules/solid.md` condition 3 | head is an external fork; the project's suite was not built or run |
| `rules/cross-cutting-concerns.md` condition 4 | the replay test needs the suite, which was not run |
| `rules/contract-first.md` condition 2 | the served-description diff needs the service started, which was not done |
| `rules/contract-first.md` condition 3 | the test per declared operation needs the suite, which was not run |
| `rules/contract-first.md` condition 4 | the envelope validation runs inside the contract test, which was not run |

---

## What is deliberately absent

**No summary sentence.** "Overall this looks reasonable" is the vague feedback
the procedure refuses, dressed as courtesy.

**No next-steps list.** The `Resolved by` cell already carries it, per finding,
where the author is reading.

**No threads from other reviewers.** Aggregating them is outside this
procedure, and a stale copy of somebody else's comment is worse than a link to
the live one.
