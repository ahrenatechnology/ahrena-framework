---
name: stacking-pull-requests
description: Build, submit and land a stack of pull requests, with the forge's native stacks where it has them and by running the stack yourself where it does not. Use when a change has been split into layers that should be reviewed apart and land in order, when layers already opened need to become a stack, when a layer below has landed, or when a stack is ready to merge.
type: skill
clade: contributing
references:
  - rules/stacked-pull-requests.md
  - rules/branch-naming.md
  - rules/pr-quality.md
  - skills/opening-issues/SKILL.md
---

# Stacking pull requests

A stack is a set of pull requests, each based on the one below, landing on trunk in order. Where the forge has native stacks, the forge does the mechanics and this skill adds the framework's rules. Where it has none, you run the stack yourself, and this skill is the procedure. [`docs/stacked-pull-requests.md`](../../docs/stacked-pull-requests.md) draws both.

Stack only when the layers are worth reviewing apart. Deciding how a change splits is `planning-changes`, not this skill.

## 0. Find out which path applies

Ask the forge, rather than assuming:

```sh
gh api graphql -f query='{ __type(name: "PullRequestStack") { name } }' -q '.data.__type.name'
```

`PullRequestStack` means native stacks: take steps 1 to 6. An empty answer, or a forge without `gh`, means the framework runs the stack: take steps 1 to 3, then 7 and 8.

## 1. One issue per layer

Every layer is a pull request, so each answers its own issue, written with `opening-issues`. The layers of one plan are sub-issues of the plan. Take ownership of each when its work starts, with `gh issue edit <n> --add-assignee @me`.

## 2. Name every branch `type/N-slug`

`branch-naming.md` holds every layer to it. On the native path, pass the name to `gh stack init` and `gh stack add`, and never let `gh stack add -m` pick one: it generates a date and a slug, such as `03-24-add_login`, that carries no issue number. On the other path, create each branch from the one below it.

## 3. Each body closes its own layer's issue

`Closes #<its-issue>`, and never the parent's or the plan's. The title is the layer's trunk subject, held to `pr-quality.md` like any pull request's.

## 4. Native: build the stack with `gh stack`

Install GitHub's extension, and its skill, which covers every command and the flags to pass when nothing can prompt:

```sh
gh extension install github/gh-stack
gh skill install github/gh-stack --agent claude-code --scope user
```

Open each layer against the one below it, then link them, bottom to top:

```sh
gh pr create --base <branch-below> --title "<type>: <subject>" --body-file <body.md>
gh stack link <bottom-pr> <next-pr> <top-pr>
```

`gh stack submit --auto` also works, but it opens drafts with generated titles that fail `pr-quality.md`, so fix each with `gh pr edit` afterwards.

## 5. Native: keep it current

`gh stack sync` fetches, rebases each layer onto the one below, and pushes. When a layer merges, the forge retargets and rebases the layers above it. You do nothing.

## 6. Native: land it through the stack

A person lands it, never the agent (`gates.md` condition 3). Two ways, each layer closing its own issue.

**Layer by layer, each on its own green checks**, with `scripts/land-stack.py`. Bottom to top, it waits for each layer's base to become the stack's, waits for its checks and stops at the first red, stops at the first layer not `APPROVED`, and merges through the async merge API. A rerun skips what already landed. Run it without `--go` and hand the person the list it prints and the command:

```sh
python3 scripts/land-stack.py <owner/repo> <stack>
python3 scripts/land-stack.py <owner/repo> <stack> --go [--admin] [--method merge|squash|rebase]
```

`gh pr merge` refuses a layer: a stacked pull request lands only through `PUT /repos/{o}/{r}/pulls/{n}/merge-async`, whose status is read from `merge-async/{details.uuid}`. A merge the branch rules refuse comes back `failed` there, not on the `PUT`. The async API's admin override is `bypass_rules=true`, which `--admin` sends, as `--admin` does on `gh pr merge`. The method defaults to the one the repository allows and lands with, never a fixed squash. `scripts/test-land-stack.py` pins all of this.

**The whole stack in one operation**, from the stack on github.com, or with `gh stack merge <top-ready-pr> --yes --squash`. That lands the chosen layer and every unmerged one below it, in order, without waiting on each layer's checks.

## 7. Framework-run: chain the bases

Open the bottom against trunk and each layer against the branch below it, with `gh pr create --base <branch-below>` or the forge's own CLI. The base is what makes it a layer. `stacked-pull-requests.md` checks that each base is an open pull request's branch and that the chain reaches trunk.

## 8. Framework-run: land the bottom, then restack the next

Land the bottom alone, by squash. Before it lands, note its branch's last commit. Then move the next layer onto trunk past it:

```sh
git fetch origin
git rebase --onto origin/main <landed-tip> <layer-branch>
git push --force-with-lease
gh pr edit <layer-number> --base main
```

Skip the last line if the forge already moved the base, as GitHub does when the landed branch is deleted on merge. The layer is now the bottom, and any review given before the restack is given again. Repeat up the stack. `stacked-pull-requests.md` condition 3 fails a layer until its restack is done.

## Either way

Never merge a layer into its parent's branch to save a restack. Its `Closes` would never reach trunk, and its issue would stay open.

## When this skill does not apply

A single pull request against trunk is not a stack, and none of this applies to it. Neither does a change that has not been split: how to split one is `planning-changes`.
