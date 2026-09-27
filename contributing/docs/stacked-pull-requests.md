---
id: stacked-pull-requests
type: doc
clade: contributing
title: Stacked pull requests
summary: Why stacking is a mode the rules detect rather than a practice they impose, how a stack lands on a squash-only trunk, and what was refused from the predecessor's six stacking artifacts.
references:
  - rules/stacked-pull-requests.md
  - rules/pr-quality.md
  - rules/protected-trunk.md
---

# Stacked pull requests

The reference for `rules/stacked-pull-requests.md`. The rule states what is checked; this states why stacking is optional, how a stack lands, and what came across from the predecessor.

## A mode, not a mandate

A stack is a way of splitting one change into layers that are reviewed separately and land in order. Each layer is a pull request whose base is the layer beneath it. Some changes want this and most do not. A repository that never stacks loses nothing under these rules, and a repository that does stack gains conditions for the failures stacking has.

So the framework imposes no stacking and asks for no declaration. The owner decided on #58 that a stack is **detected from base-branch chaining**: a pull request whose base is not trunk is read as a layer. That chain is GitHub's own record. Graphite, git-spice, Sapling and ghstack all produce it, and so does a person running `gh pr create --base <parent-branch>`. The framework reads the chain and adopts none of the tools. That follows the same line as the decision not to own MCP configuration, and as #22's state vocabulary being configuration.

The cost of detection over declaration is ambiguity. A pull request opened against the wrong base has the same shape as a layer. Condition 1 of the rule settles it: a layer's base is the branch of an open pull request, and a wrong base is the branch of nothing.

## The evidence, which is thin on purpose

On 2026-09-27 this repository had merged 25 pull requests and none of them was stacked. Every base was `main`. The rule therefore does not describe a practice; it is ready for one. Its conditions come from GitHub's mechanics rather than from failures observed here.

One of those mechanics was checked against this repository's own history before a condition was built on it. The commits on #79's branch, which reached trunk as the single squash `75481ca`, are still returned as belonging to #79 by `GET /repos/{repo}/commits/{sha}/pulls`. Condition 3 depends on exactly that.

## How a stack lands on a squash-only trunk

`ADR-001` makes every pull request land as one squash commit, and `protected-trunk.md` makes the forge enforce it. Squash and stacking interact in one way that matters, and it is the reason condition 3 exists.

The stack before anything lands:

```
main ── A1 ── A2          #80  feat/1-bottom  base main
               └── B1     #81  feat/2-top     base feat/1-bottom
```

#80 lands. Trunk receives one new commit, `S`, holding A1 and A2's changes. `feat/2-top` still holds A1 and A2 as they were, because a squash rewrites nothing on other branches:

```
main ── S
feat/2-top ── A1 ── A2 ── B1
```

If #81 is now pointed at trunk as it stands, its diff shows A1 and A2 again. Their content is already in `S`, so at best they are noise the reviewer has to ignore and at worst they conflict. Condition 3 fails the pull request and names #80 as the source of the commits it still carries. The restack drops them:

```sh
git fetch origin
git rebase --onto origin/main <tip-of-feat/1-bottom> feat/2-top
git push --force-with-lease
```

`<tip-of-feat/1-bottom>` is A2, the last commit #80 had. After the rebase `feat/2-top` is `S ── B1'`, and #81's diff is B1 alone.

The base has to move too. GitHub retargets the pull requests based on a branch when that branch is deleted after its pull request merges. This repository turned on `delete_branch_on_merge` on 2026-09-27, so landing #80 deletes `feat/1-bottom` and GitHub moves #81 to `main` by itself. A repository with it off keeps the branch, #81 stays based on it, and condition 1 fails #81 with "already landed. Retarget it to main"; `gh pr edit 81 --base main` fixes that by hand.

Then #81 is the bottom, and the same steps repeat up the stack.

## Reviewing a layer

A layer is reviewed against its parent, not trunk. `engineering/skills/reviewing-diffs` step 1 already fixes the base as the commit the change merges into, and for a layer that is the parent's branch. A finding on a line the layer did not touch belongs to the layer that did, and is raised there. Once a layer's parent lands and the layer is restacked, its base is trunk and its diff has changed, so a verdict given before the restack is given again.

## Refused from the predecessor

The predecessor carried six stacking artifacts, 1,523 lines: `codex-stacked-prs`, `kata-stacked-pr-create`, `kata-stacked-pr-merge`, `kata-stacked-pr-rebase`, `cry-new-stacked-pr` and `codex-git-spice`.

**git-spice as the mechanism.** `codex-git-spice` alone was 321 lines. git-spice is already refused, as maintainer infrastructure (#16), and the owner's decision to read the chain rather than adopt a tool refuses it again for its own reason. What a stack needs from any tool is an order of operations, and that order is tool-independent: `skills/stacking-pull-requests` states it with `git` and `gh` alone.

**Stack metadata in the pull-request body**, which some tools write, ghstack among them. A list of the stack's layers in each body is a second record of what the bases already record, and it drifts on every restack. The chain is read from the bases, so there is nothing to keep in sync.

**A separate decomposition checklist.** The predecessor built "when does one change become several" twice, for plans and for stacks, and the two drifted. Here it is built once, by the planning work in #45 that `ADR-004` gives its own sub-issue, and stacking cites it.

## Where this stops

**The rule is untested against a real stack.** Every condition is pinned by cases built from GitHub's documented and measured behaviour, and none has yet fired on a stack in this repository, because there has not been one. The first real stack is the rule's first real test, and whatever it finds is a new case in the suite.

**The retargeting behaviour was not reproduced here.** That GitHub retargets dependents when a merged branch is deleted comes from GitHub's own behaviour as documented, not from a measurement in this repository. The rule does not depend on it: whether or not the retarget happens, condition 1 names the state the pull request is left in.

**The forge is GitHub.** Other forges record a stack in their own way. The detector reads GitHub's API, and on another forge all three conditions report unchecked.
