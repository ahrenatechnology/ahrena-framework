---
name: opening-issues
description: Open a typed issue (epic, user story, tech task, spike or bug) written to its template, or find the one that already owns the work. Use before starting any change, when work began without an issue and needs one before its pull request, or when a finding belongs to work that is not in front of you.
type: skill
clade: contributing
references:
  - rules/issue-quality.md
  - rules/branch-naming.md
  - rules/pr-quality.md
  - skills/writing-acceptance-criteria/SKILL.md
---

# Opening issues

Every change starts from an issue. `branch-naming.md` makes the branch carry its number, and `pr-quality.md` checks that the issue exists and is open. This skill is how the issue gets written, and how to find one that already exists.

Everything here is `gh`. No MCP server is needed. Use what access is present, and say what could not be read rather than stopping.

## 1. Look for the issue that already owns the work

Search open and closed issues before writing one:

```sh
gh issue list --state all --search "<terms>" --limit 20
```

**The first issue that covers the work owns it.** Work from it, and add what you know as a comment. A second issue for the same scope splits the discussion, and one of the two goes stale.

Open a new issue beside an existing one only when the work is genuinely independent, or when the scope has grown enough to split. In both cases, say so in a comment on the original, naming the new issue.

## 2. Pick its type

Five types, each with a template in `references/`. This repository's `ADR-012` records why these five.

| Type | It is | Template |
|---|---|---|
| Epic | An outcome delivered by several items under it | [`references/epic.md`](references/epic.md) |
| User story | A behaviour a user can see, in one pull request | [`references/user-story.md`](references/user-story.md) |
| Tech task | Work with no behaviour a user sees: enabling, refactor, CI, docs | [`references/tech-task.md`](references/tech-task.md) |
| Spike | A question that must be answered before dependent work, timeboxed | [`references/spike.md`](references/spike.md) |
| Bug | Something that does not do what was specified | [`references/bug.md`](references/bug.md) |

If the item is two of these, it is two items. A story that also needs an unknown answered is a spike that blocks a story.

## 3. Write it to its template

Copy the template's body and fill every section. A section that does not apply is deleted, not left empty. Each template already carries what `issue-quality.md` asks for: the evidence, what done looks like as `## Acceptance criteria` in the shape `writing-acceptance-criteria` gives, and what it leaves to other issues.

The title follows the template's guidance for its type. Write the body to a file, so it can be read back before it is sent.

## 4. Create it with its type, and no owner yet

```sh
gh issue create --type <type> --title "<title>" --body-file <body.md>
```

`--type` is the forge's native issue type. Ask the organisation which it has, with `gh api orgs/<org>/issue-types -q '.[].name'`, and use the exact name when there is one. Otherwise use the nearest: `Feature` for an epic or a story, `Task` for a tech task or a spike, `Bug` for a bug. Each template names its match. Where the forge has no issue types, drop `--type` and open the body with one line, `**Type:** <type>`.

Leave the assignee empty. An owner named when the issue is filed, before anyone has started, is an owner nobody is holding to anything. Labels are the project's own configuration (#80), and this skill applies none.

## 5. Place it

If the work belongs to an epic, make it a sub-issue of that epic. The parent then shows it, and nothing has to keep a separate list in sync:

```sh
gh api -X POST repos/<owner>/<repo>/issues/<epic>/sub_issues \
  -F sub_issue_id="$(gh api repos/<owner>/<repo>/issues/<new> -q .id)"
```

The field is the issue's `id`, not its number. If it waits on another item, `planning-changes` step 5 records that.

## 6. Start the work from the issue

When somebody actually starts, create the branch from the issue and take ownership at that moment:

```sh
gh issue develop <n> --name <commit-type>/<n>-<slug> --base main --checkout
gh issue edit <n> --add-assignee @me
```

`gh issue develop` links the branch to the issue, and GitHub closes a linked issue when the branch's pull request merges, whatever the body says. So never develop from an epic, or from any issue that should stay open after this one change. Develop from the sub-issue the change finishes.

## 7. When the work began without an issue

The work cannot land until the issue exists, so write it before the pull request opens. Search first (step 1); the work may already have an owner.

**The issue meets the same bar as any other.** It has its type, its template filled, evidence, done and what it leaves, in full. The only difference is the order of events, and the body says so in one line: that the work started on its branch before the issue was written. A lighter shape for late issues would become the form every skipped step gets filed under.

Then give the branch the issue's number. Locally, before anything is pushed:

```sh
git branch -m <commit-type>/<n>-<slug>
```

If the branch is already on the forge, rename it there. GitHub moves an open pull request along with it:

```sh
gh api -X POST repos/<owner>/<repo>/branches/<old-name>/rename -f new_name=<commit-type>/<n>-<slug>
```

## When this skill does not apply

The shape of acceptance criteria is `writing-acceptance-criteria`. Splitting one issue into several, or a backlog of epics into items, is `planning-changes`. This skill writes one issue well.
