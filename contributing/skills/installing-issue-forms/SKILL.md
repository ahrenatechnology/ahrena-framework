---
name: installing-issue-forms
description: Copy Ahrena's default issue forms into a repository's .github/ISSUE_TEMPLATE, without overwriting the forms it already has. Use when a project adopts the framework, when a repository has no issue templates, or when it lacks a form for a type of work item such as spikes.
type: skill
clade: contributing
references:
  - skills/opening-issues/SKILL.md
---

# Installing issue forms

Agents write issues from the repository's templates, or from Ahrena's defaults when there are none, and they need nothing installed to do it (`opening-issues` step 3). Installing the forms is for people. It makes the same forms appear on the forge's "New issue" page, so an issue filed by hand has the same sections as one an agent writes.

The forms are the ones `opening-issues` uses: `references/issue-forms/` beside its `SKILL.md`. Every form carries `Acceptance criteria` and `Left to other issues`, which the framework's checks read.

## 1. See what the repository already has

```sh
gh api repos/<owner>/<repo>/contents/.github/ISSUE_TEMPLATE -q '.[].name'
```

A 404 means it has none. A form the repository already has is its own and is never overwritten, even when Ahrena's has the same name. Note which types it covers, so only the missing ones are added.

## 2. Get Ahrena's forms

From the installed plugin, the directory is `skills/opening-issues/references/issue-forms/` under the `ahrena-contributing` plugin. From the framework's repository, when the plugin files are not at hand:

```sh
gh api repos/ahrenatechnology/ahrena-framework/contents/contributing/skills/opening-issues/references/issue-forms -q '.[].name'
```

## 3. Copy what is missing into `.github/ISSUE_TEMPLATE/`

Copy each form whose type the repository does not cover. Copy `config.yml` only if the repository has no `config.yml`: it turns blank issues off, so every issue starts from a form. Add the repository's own discussion or support links to its `contact_links` if it has any.

## 4. Match each form's type to the organisation's

Each form sets a native issue type, `type: Epic`, `Task`, `Bug` or `Feature`. List the ones the organisation has:

```sh
gh api orgs/<org>/issue-types -q '.[].name'
```

Where a form names a type the organisation lacks, change the copy's `type:` to the nearest: `Feature` for an epic, `Task` for a spike. Where the repository is not owned by an organisation with issue types, remove the `type:` line.

## 5. Land it like any other change

Installing forms is a change to the repository, so it goes through the flow: a tech-task issue, written with `opening-issues`; a branch from it; a pull request that closes it. Never push to trunk. List in the pull request which forms were added, which the repository already had, and which types were changed.

After it merges, open the forge's "New issue" page and check each added form renders. The forge reports a form it cannot parse on that page, and nowhere else.

## When this skill does not apply

A repository whose issues are all written by agents gets nothing from this, because `opening-issues` reads the defaults directly. Changing a default form is `opening-issues` step 9.
