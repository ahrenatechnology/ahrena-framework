---
name: stacking-pull-requests
description: Build, submit and land a GitHub stack of pull requests with gh stack, under this framework's rules. Use when a change has been split into layers that should be reviewed apart and land in order, when layers already opened by hand need to become a stack, or when a stack is ready to merge.
type: skill
clade: contributing
references:
  - rules/stacked-pull-requests.md
  - rules/branch-naming.md
  - rules/pr-quality.md
  - skills/opening-issues/SKILL.md
---

# Stacking pull requests

A stack is GitHub's own: an ordered set of pull requests, each based on the one below, linked as one stack on the forge. GitHub's `gh stack` does the mechanics. This skill adds what `gh stack` does not know: the rules every layer is still held to. [`docs/stacked-pull-requests.md`](../../docs/stacked-pull-requests.md) has what the first stack here showed.

Stack only when the layers are worth reviewing apart. Deciding how a change splits is the plan's job (#93), not this skill's.

## 1. Install GitHub's extension, and its skill for agents

```sh
gh extension install github/gh-stack
gh skill install github/gh-stack --agent claude-code --scope user
```

GitHub's skill covers every `gh stack` command and the flags to pass when nothing can prompt: `submit --auto`, `merge --yes`. Read it for the commands. This skill only says what to add.

## 2. One issue per layer

Every layer is a pull request, so each answers its own issue, written with `opening-issues`. The layers of one plan are sub-issues of the plan. Take ownership of each when its work starts: `gh stack` creates the branches, so `gh issue develop` does not, and nothing assigns anyone.

## 3. Name every branch yourself

Pass the name to `gh stack init` and `gh stack add`, in the shape `branch-naming.md` requires:

```sh
gh stack init feat/98-acceptance-criteria
gh stack add feat/99-trace-criteria
```

Never let `gh stack add -m` pick the name. It generates a date and a slug, such as `03-24-add_login`, which carries no issue number and fails the branch check on every layer.

## 4. Open each layer as a pull request the rules accept

`gh stack submit --auto` opens drafts with generated titles, and those fail `pr-quality.md`. Either open each layer yourself and link them, which is the path that gets every title and body right the first time:

```sh
gh pr create --base <branch-below> --title "<type>: <subject>" --body-file <body.md>
gh stack link <bottom-pr> <next-pr> <top-pr>
```

Or submit, then fix each title and body with `gh pr edit`. Each body closes its own layer's issue, `Closes #<its-issue>`, and never its parent's.

## 5. Keep the stack current

After a change on any layer, or when trunk moves:

```sh
gh stack sync
```

It fetches, rebases every layer onto the one below, and pushes. When a layer below merges, GitHub retargets and rebases the rest itself. `stacked-pull-requests.md` condition 3 exists for a branch that slipped out of that.

## 6. Land it through the stack

From the stack on github.com, or:

```sh
gh stack merge <top-ready-pr> --yes --squash
```

That lands the chosen layer and every unmerged one below it, in order, each as its own squash, each closing its own issue. Never merge a layer with `gh pr merge`, and never into its parent's branch. A layer merged into its parent never closes its issue.

## When this skill does not apply

A single pull request against trunk is not a stack. Neither is a chain of branches that was never put in a stack. `stacked-pull-requests.md` fails such a chain, and step 4's `gh stack link` is how to fix it.
