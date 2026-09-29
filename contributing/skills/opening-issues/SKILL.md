---
name: opening-issues
description: Open an issue from the repository's own issue template for its type, or from Ahrena's default when the repository has none, or find the issue that already owns the work. Use before starting any change, when work began without an issue and needs one before its pull request, or when a finding belongs to work that is not in front of you.
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

The repository's own issue templates come first. Where it has none for the type at hand, Ahrena's defaults in `references/` apply. This repository's `ADR-012` records both.

Everything here is `gh`. No MCP server is needed. Use what access is present, and say what could not be read rather than stopping.

## 1. Look for the issue that already owns the work

Search open and closed issues before writing one:

```sh
gh issue list --state all --search "<terms>" --limit 20
```

**The first issue that covers the work owns it.** Work from it, and add what you know as a comment. A second issue for the same scope splits the discussion, and one of the two goes stale.

Open a new issue beside an existing one only when the work is genuinely independent, or when the scope has grown enough to split. In both cases, say so in a comment on the original, naming the new issue.

## 2. Pick its type

| Type | It is | Ahrena's default: guide, and form |
|---|---|---|
| Epic | An outcome delivered by several items under it | [`references/epic.md`](references/epic.md), `references/issue-forms/epic.yml` |
| Feature request | A capability asked for, before it is shaped into stories | [`references/feature-request.md`](references/feature-request.md), `references/issue-forms/feature-request.yml` |
| User story, API | A behaviour a client of an API can see, in one pull request | [`references/user-story-for-api.md`](references/user-story-for-api.md), `references/issue-forms/user-story-for-api.yml` |
| User story, frontend | A behaviour a person can see on a screen, in one pull request | [`references/user-story-for-frontend.md`](references/user-story-for-frontend.md), `references/issue-forms/user-story-for-frontend.yml` |
| Tech task | Work with no behaviour a user sees: enabling, refactor, CI, docs | [`references/tech-task.md`](references/tech-task.md), `references/issue-forms/tech-task.yml` |
| Plan | One executable unit of a larger item, as its sub-issue | [`references/plan.md`](references/plan.md), `references/issue-forms/plan.yml` |
| Spike | A timeboxed question that must be answered before dependent work | [`references/spike.md`](references/spike.md), `references/issue-forms/spike.yml` |
| Bug | Something that does not do what was specified | [`references/bug.md`](references/bug.md), `references/issue-forms/bug.yml` |

If the item is two of these, it is two items. A story that needs an unknown answered first is a spike that blocks a story.

## 3. Find the template: the repository's, or Ahrena's

Read the repository's own templates first:

```sh
gh api repos/<owner>/<repo>/contents/.github/ISSUE_TEMPLATE -q '.[].name'
```

- **It has a template for this type.** Read it, `gh api repos/<owner>/<repo>/contents/.github/ISSUE_TEMPLATE/<file> -q .content | base64 -d`, and write the issue from it. A form (`.yml`) gives its fields in `body`; a Markdown template gives its headings.
- **It has templates, none for this type, or it has none at all.** Write the issue from Ahrena's default for the type, in `references/`.

## 4. Write the body from the template

Write every field as a `### <label>` heading followed by its answer, in the template's order. That is exactly what GitHub produces when a person fills the same form in, so issues written by an agent and by hand read alike. The `markdown` blocks of a form are instructions to the writer, not sections of the issue.

Fill every required field. An optional field with nothing to say is left out, not written empty. Start from the field's own text where it has one, and replace every placeholder.

The body must end up with an `### Acceptance criteria` section, in the shape `writing-acceptance-criteria` gives, because `traceability.md` reads it. Ahrena's defaults carry one. If the repository's template has no such field, add the section after its last field, and add `### Left to other issues` after it when there is anything to leave. Everything else in the repository's template stays as it is.

Write the body to a file, so it can be read back before it is sent. The title follows the template's `title`.

## 5. Create it with its type, and no owner yet

```sh
gh issue create --type <type> --title "<title>" --body-file <body.md>
```

The type is the template's own `type`. Check that the organisation has it, `gh api orgs/<org>/issue-types -q '.[].name'`, and use the nearest otherwise: `Feature` for an epic, a feature request or a story, `Task` for a tech task, a plan or a spike, `Bug` for a bug. Where the forge has no issue types, drop `--type` and open the body with one line, `**Type:** <type>`.

Leave the assignee empty. An owner named when the issue is filed, before anyone has started, is an owner nobody is holding to anything. Labels are the project's own configuration (#80), and this skill applies none unless the repository's template does.

## 6. Place it

If the work belongs to a larger item, make it a sub-issue of that item. The parent then shows it, and nothing has to keep a separate list in sync:

```sh
gh api -X POST repos/<owner>/<repo>/issues/<parent>/sub_issues \
  -F sub_issue_id="$(gh api repos/<owner>/<repo>/issues/<new> -q .id)"
```

The field is the issue's `id`, not its number. If it waits on another item, `planning-changes` step 5 records that.

## 7. Start the work from the issue

When somebody actually starts, create the branch from the issue and take ownership at that moment:

```sh
gh issue develop <n> --name <commit-type>/<n>-<slug> --base main --checkout
gh issue edit <n> --add-assignee @me
```

`gh issue develop` links the branch to the issue, and GitHub closes a linked issue when the branch's pull request merges, whatever the body says. So never develop from an epic, or from any issue that should stay open after this one change. Develop from the sub-issue the change finishes.

## 8. When the work began without an issue

The work cannot land until the issue exists, so write it before the pull request opens. Search first (step 1); the work may already have an owner.

**The issue meets the same bar as any other.** It has its type and its template filled in full. The only difference is the order of events, and the body says so in one line: that the work started on its branch before the issue was written. A lighter shape for late issues would become the form every skipped step gets filed under.

Then give the branch the issue's number. Locally, before anything is pushed:

```sh
git branch -m <commit-type>/<n>-<slug>
```

If the branch is already on the forge, rename it there. GitHub moves an open pull request along with it:

```sh
gh api -X POST repos/<owner>/<repo>/branches/<old-name>/rename -f new_name=<commit-type>/<n>-<slug>
```

## 9. Changing the defaults

Ahrena's defaults are GitHub issue forms in `references/issue-forms/`, adapted from the predecessor framework's own. Each `references/<type>.md` is generated from its form, and CI fails when one is stale. Change the form, never the `.md`, then regenerate:

```sh
python3 scripts/render_issue_forms.py
```

`references/issue-forms/config.yml` turns blank issues off, so every issue on the forge starts from a form. `installing-issue-forms` copies the forms and it into a repository, for the people who file issues by hand.

## When this skill does not apply

The shape of acceptance criteria is `writing-acceptance-criteria`. Splitting one issue into several, or a backlog of epics into items, is `planning-changes`. This skill writes one issue well.
