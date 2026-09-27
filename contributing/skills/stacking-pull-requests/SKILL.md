---
name: stacking-pull-requests
description: Open, land and restack a stack of pull requests with git and gh alone. Use when a change has been split into layers that should be reviewed separately and land in order, when the bottom of a stack has just merged and the next layer must move onto trunk, or when a check reports that a pull request carries commits that already landed.
type: skill
clade: contributing
references:
  - rules/stacked-pull-requests.md
  - rules/branch-naming.md
  - rules/pr-quality.md
  - docs/stacked-pull-requests.md
---

# Stacking pull requests

A stack is a chain of pull requests, each based on the branch of the one beneath it. No tool is required and none is assumed; every step below is `git` and `gh`. [`docs/stacked-pull-requests.md`](../../docs/stacked-pull-requests.md) draws the chain before and after a layer lands, and is worth reading once.

Stack only when the layers are worth reviewing apart. Most changes are one pull request, and deciding how a change splits is the plan's job, not this skill's.

## 1. Give every layer its own issue

A layer is a pull request, so it answers an issue and its branch carries that issue's number, as `branch-naming.md` requires. Layers of one plan are usually sub-issues of the same parent. Create each branch from the issue, so the two are linked:

```sh
gh issue develop <issue> --name <type>/<issue>-<slug> --base <parent-branch>
```

The bottom layer's `--base` is trunk. Every other layer's is the branch beneath it.

## 2. Open each layer against the one beneath it

```sh
gh pr create --base <parent-branch> --title "<type>: <subject>" --body "Closes #<issue>"
```

The base is what makes it a layer. `stacked-pull-requests.md` condition 1 checks that the base is an open pull request's branch, so a layer opened against a branch nobody has a pull request for fails as a wrong base.

`pr-quality.md` holds each layer to the same body and title conditions as any pull request. Close each layer's own issue in its own body. A layer that closes its parent's issue closes it the moment that layer lands, which may be before the parent does.

## 3. Review and land from the bottom

Each layer is reviewed against its parent, which is its base. Land the bottom first, by squash, which is the only method the forge offers. A higher layer cannot reach trunk before it: merging it would land it on its parent's branch.

## 4. Restack the next layer

When the bottom lands, trunk has one new squash commit and the next layer's branch still holds the bottom's original commits. `stacked-pull-requests.md` condition 3 fails the layer until they are gone. Note the landed branch's last commit before anything else, then:

```sh
git fetch origin
git rebase --onto origin/main <landed-tip> <layer-branch>
git push --force-with-lease
```

Then point the layer at trunk, unless GitHub already did because the landed branch was deleted:

```sh
gh pr edit <layer-number> --base main
```

The layer is now the bottom. Any review given before the restack was of a different diff, so it is given again.

## 5. Repeat up the stack

Each landing is followed by one restack of the layer above it, and nothing above that layer moves until its own parent lands. If a restack conflicts, the conflict is between the layer and what landed. Resolve it on the layer's branch. Trunk stays untouched.

## When this skill does not apply

A single pull request against trunk is not a stack, and none of this is needed for it. A change split into branches that were never opened as pull requests is not a stack either, because nothing here can read a chain that has no pull requests in it.
