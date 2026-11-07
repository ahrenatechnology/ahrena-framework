---
id: argos-design
type: doc
clade: code-review
title: Argos design
summary: Why Argos is one review orchestrator, how it decides what counts as a finding, and why its loop, its verdict and its landing are shaped as they are.
references:
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
  - ahrena-engineering-quality:docs/review-verdicts.md
  - ahrena-foundation:rules/naming.md
---

# Argos design

`agents/argos.md` is the executor's prompt and says what to do. This doc holds the arguments behind it, so the prompt does not pay for them on every run.

## One Argos

The framework shipped two agents named `argos` until #245: a pull-request reviewer in `ahrena-engineering-quality` and this orchestrator. A runtime that invokes `argos` got whichever one the platform found first, and the two promised different things. Only one had the bounded loop; only the other had the decision rules about questions, rule boundaries and Erodos. The audit in #245 found session and CI reviews disagreeing on the same commit, and CI runs that nested a second Argos inside the first.

So there is one, here, and it carries both halves. The quality plugin keeps the review skills, the router, the findings and verdict docs, and Erodos. Condition 8 of `ahrena-foundation:rules/naming.md` makes a second agent under the same handle a gate failure, anywhere in the marketplace. A runtime, CI or session, passes inputs and may withhold tools; it does not restate or override a rule of behaviour, which is why the decision rules live in this agent and not in a wrapper.

The agent is addressed as `argos` and its role is `review-orchestrator`. `ahrena-foundation:rules/naming.md` explains why an agent carries both a handle and a role.

## How it decides

**It routes before it runs, and a script does the routing.** Reading every lens against every change produces a review that touched everything and examined nothing. Each route is driven by regular expressions over the changed paths, the lines the change adds, or the file's text, so two runs over one diff select the same lenses. [`review-routes`](../../quality/docs/review-routes.md) argues why that is a table and not a judgment. The lens edges live in `routes.json`, so a new lens is a row in that table rather than an edit to the agent.

**A firing route is which lens to run, not what it found.** The driver that matches opens a lens; whether the matched line is a defect is decided inside the lens, by reading it, with the party who would gain named.

**The lenses run in Argos's own run.** A lens is a skill, not an agent. Handing lenses to background subagents is how CI ended up with a second Argos reviewing beside the first, and a background child returns after its parent has already answered.

**It merges by cause, across lenses.** Two lenses reporting one cause become one finding, under the lens whose condition names it and at the higher severity. Two causes on one line stay two. One change seen by four disciplines still reads as one review.

**A finding has four fields, or it is a question.** File and line, rule and condition, the state observed, the change that resolves it. An impression missing one is not a finding at a lower severity. Written as a warning, it costs the author the time to discover that it was never a finding. [`review-findings`](../../quality/docs/review-findings.md) carries the four severity levels and the test that assigns each.

**It reads the rule's own boundary before citing it.** Every rule ends with the states that match a condition and are correct anyway. Reporting one is not a wasted finding: it is the moment the author learns this reviewer's findings need checking, after which all of them do.

**What a script decides is not an opinion.** The structure, comment-pointer and backstage-language detectors, the artifact gate and the branch and commit checks decide their conditions exactly and run in CI. A review that repeats a check the pull request already passed spends the author's attention on a settled question. What is left for reading is the counts across a tree, the boundaries a reader draws and the arbitration.

**It says what it did not check.** A fork's checkout is never executed, because building it runs the author's code on the reviewing machine. The conditions that needed it are recorded as `unchecked`, by name, so the review does not read as clean.

**The verdict is the worst a lens returned.** A blocking finding is a request for changes; a question or an unchecked condition is a comment; anything less is an approval, on the first pass as on any other. [`review-verdicts`](../../quality/docs/review-verdicts.md) argues what that approval asserts.

**The verdict is the comment and the status, never a forge review.** `gh pr review --approve` would make the approval depend on the reviewing account: refused on a shared account, and a second, divergent record beside the comment. The comment carries the findings and the coverage; the `argos/verdict` status on the reviewed sha is what a ruleset can require.

**The approval carries what it covered.** It names the lenses that ran, those the route left out, and every condition recorded as undecided. An approval that hides what it did not check is worth less than no approval.

**It bounds the loop.** A request for changes goes to Erodos and comes back as a commit to re-review; the round bound caps it, so a change that will not converge reaches a person instead of cycling. The round count is an input, so a runtime that re-invokes Argos on each push carries it between passes.

**It never fixes, and Erodos never reviews.** A reviewer that applied its own findings would read its own edit on the next pass, and the second reading is the whole value of a review (`ADR-014`).

**It lands through the forge.** It asks for a squash merge of the commit it read, only when every check on that commit has passed, and it accepts every refusal (`ADR-013`). A ruleset that requires a named person still holds the merge.

**It treats what it reads as data.** The diff, the description, the issue and every comment were written by someone else. An instruction in any of them is not addressed to it, and one that looks planted is a finding the relevant lens makes.

## Where this stops

This doc argues the agent's design; it is not read at run time and it adds no condition. The conditions are in the quality plugin's skills and rules, and the procedure is in `agents/argos.md`. How a re-review reads the previous opinion and how a decision the pull request marks as accepted is weighed are open in #245 and not settled here.
