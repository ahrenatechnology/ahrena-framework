---
id: pull-requests-and-trunk
type: doc
clade: contributing
title: Issues, pull requests and trunk
summary: The measurements behind the issue, pull-request and trunk rules, why most of their conditions run against the forge rather than the tree, and what was left out and why.
references:
  - rules/issue-quality.md
  - rules/pr-quality.md
  - rules/protected-trunk.md
---

# Issues, pull requests and trunk

The reference for three rules. `issue-quality.md` is what an issue says, `pr-quality.md` is how a pull request links an issue to trunk, and `protected-trunk.md` is how the forge keeps anything else off trunk. The rules state what is checked; this carries the evidence and what was refused.

## The chain, finished

```
issue  →  branch  →  commits  →  pull request  →  trunk
```

`contribution-flow.md` covers the first three links and stops at the pull request. These three rules cover the rest. Every condition in them is a link between two steps of that chain, and every one was found written wrong in this repository.

## Where the detector runs

Almost nothing here is in the tree. A pull request's title and body, the issues it closes, the repository's merge settings, and the rulesets on trunk all belong to the forge. A hook that reads the tree cannot see any of them, and a hook that asks the forge needs a token and a network, which the framework's offline hooks do not have.

So both hooks are declared `enforced-in: forge`, the tier `ADR-002` added for this case. They run in CI with the default `GITHUB_TOKEN`. Offline they report what they could not ask about as unchecked, never as failed, and they still decide whatever the event payload itself carries. `pr-quality.md` conditions 1 to 3 need only the payload. Everything else needs the forge.

This is the answer #39 asked for: each condition says what decides it and where it runs, and none of them is a hook that does not exist.

## The measurements

On 2026-09-26, over 22 merged pull requests and 55 issues.

**A list after a closing keyword closes one issue.** #33's body read `Closes #4, #5, #6, …` and closed #4. The others it declared closed stayed open until somebody closed them by hand. #21 wrote `Closes #6`, `Closes #7` and `Closes #17` on three lines and closed all three. That difference is `pr-quality.md` condition 2.

**A pull request closed an issue its body said it would not close.** #77's body opened "Part of #45. Does not close it." Its branch had been created with `gh issue develop 45`, which links a branch to an issue, and GitHub closes a linked issue when a pull request from that branch merges. #45, the epic the pull request belonged to, was closed on merge and had to be reopened. The forge knew this before the merge: `closingIssuesReferences` on #77 listed #45. That is `pr-quality.md` condition 5, and running the hook over #77 reports it.

**Seven titles would not have fit trunk.** A squash's subject is the title plus ` (#N)`. Measured over the 22 merged pull requests, #31, #33, #49, #50, #63, #76 and #77 would have landed at 73 to 88 characters, over `commit-format.md`'s 72. They did not, for a reason that is its own defect. The forge's `squash_merge_commit_title` was `COMMIT_OR_PR_TITLE`, so a pull request with one commit landed under that commit's subject rather than its title. #76's title was 71 characters and trunk has its 48-character commit subject instead. The title a reviewer approves and the subject trunk receives were two different strings. `protected-trunk.md` condition 1 makes them one, and `pr-quality.md` condition 3 then checks the one that lands.

**`ADR-001` was not enforced.** The record was accepted on 2026-09-25 and decided on the squash. The repository still allowed all three merge methods, no ruleset covered `main`, and `main` was not protected. Of the seven pull requests merged since #68, four landed as squashes (#68, #69, #71, #76) and three by rebase, all on 2026-09-26: #74, the pull request that carried `ADR-001` itself, then #77 and #78. The three rebased commits carry no signature and no ` (#N)`. #75 reported this. `protected-trunk.md` conditions 1 and 2 are that report as a check, and they fail on this repository until an owner changes the settings.

**Every issue has a body.** None of the 55 has fewer than 40 characters. That is why `issue-quality.md` has no hook: its one mechanical candidate holds everywhere.

## What an owner has to do

Two settings, neither of which a pull request can make:

1. Under **Settings → General → Pull Requests**, allow squash merging only, and set the default squash commit title to the pull request title.
2. Under **Settings → Rules → Rulesets**, add a ruleset targeting the default branch with **Require a pull request before merging**.

Until both are done, `protected-trunk.md` fails in every run, on every pull request and on trunk. That is the intended state. A check that stays green while the decision it enforces is not in force would claim something false.

## Refused, with the reason

**Size labels and state labels.** Both are detectable. A size label either matches the computed diff or it does not, and a work item either carries exactly one state from an axis or it does not. Both are left out because the labels are configuration: the owner decided that the state vocabulary belongs to each consuming project (#22), and all four places it could live, labels, a project field, the native issue type or nowhere on the forge, are valid. A condition over labels the framework cannot name has no detector. Once the configuration surface exists, both conditions can be written against it.

**Every review thread has a reply.** Readable through the API, and left out, because a thread resolved without a reply is often the right answer to a nit. The condition would fail correct work.

**Issue templates.** A form makes the fields of `issue-quality.md` visible and proves nothing about what is written in them. A project may add one; the rule does not require it.

**The history.** Rebased commits already on trunk are measured above and not judged. Rewriting trunk to make them squashes would cost more than the signatures are worth, and a condition that failed on them permanently would fail every run from now on.

## The three things a reviewer still has to do

**Does the body describe the change in the diff?** A body that names the right issue and closes it correctly passes every condition while describing something else.

**Does the verification section show anything was verified?** "Tests pass" passes; the output of the run that shows it is what a reviewer asks for.

**Is this one change?** If the pull request were reverted, would anything unrelated go with it?

## Where this stops

**The measurements are one repository's, over one month.** 22 pull requests and 55 issues. The defects they show are real, and each is pinned by a test case named for the pull request it came from, but their rates are not a claim about any other project.

**The forge is GitHub.** Both hooks read GitHub's REST and GraphQL APIs, and the closing keywords, `closingIssuesReferences`, rulesets and merge settings are GitHub's. A project on another forge gets conditions 1 to 3 of `pr-quality.md` unchanged, since they read only the title, body and branch, and every other condition reports unchecked. Porting the rest is a detector per forge, not a change to the rules.

**Stacking is #58's.** Nothing here reads a pull request's base, so a stack passes or fails exactly as its parts would alone.
