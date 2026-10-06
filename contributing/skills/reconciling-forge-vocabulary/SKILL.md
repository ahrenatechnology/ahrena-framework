---
name: reconciling-forge-vocabulary
description: Make a repository's labels and its organisation's issue types match the files that declare them, .github/labels.yml and .github/issue-types.yml, or Ahrena's defaults where the project has none. Use when either file is found in a project, when a label or issue type a skill needs is missing on the forge, when a project adopts the framework, or after either file changes.
type: skill
clade: contributing
references:
  - skills/opening-issues/SKILL.md
---

# Reconciling forge vocabulary

Everything the framework puts on the forge is declared as code. Two files hold it, and each is read on its own:

| File | Declares | Where the default is |
|---|---|---|
| `.github/labels.yml` | The labels: status, size, quality and security, and GitHub's own | `references/labels.yml` |
| `.github/issue-types.yml` | The native issue types, on the organisation | `references/issue-types.yml` |

A project's file replaces Ahrena's default whole, file by file. A project that keeps only `labels.yml` gets its own labels and Ahrena's issue types. A `labels.yml` already written for `crazy-max/ghaction-github-labeler`, a list of `name`, `color` and `description`, works unchanged.

The type of an issue is never a label. It is the forge's native issue type, and `opening-issues` sets it.

## 1. Run the reconciler, without applying

From the project's root, with `gh` authenticated:

```sh
python3 scripts/reconcile-vocabulary.py
```

`scripts/reconcile-vocabulary.py` is beside this file. It names the repository from `gh`, or takes `owner/repo` as its first argument, and reads `.github/` under the current directory, or under `--root`.

It writes nothing. It lists every declared label and issue type the forge lacks, or holds with a different name, color or description, and says what would change. A file outside the subset it reads is refused with its line number, before the forge is asked anything: fix the line and run it again.

## 2. Show the plan

Put the listing in front of whoever asked, as it was printed. Say which file each part came from, the project's or Ahrena's default, and that nothing will be deleted.

When the listing is empty, the forge already matches and there is nothing to apply.

## 3. Apply it

```sh
python3 scripts/reconcile-vocabulary.py --apply
```

It creates what is missing and updates what differs. It never deletes. A label the forge holds that no file declares, such as `client:acme` or a size label a bot applies, stays exactly as it is.

Issue types live on the organisation, and only an organisation admin can create them. A token that cannot read or write them is reported, and the labels are reconciled anyway; the run does not fail for it. Pass the report on, naming the types the organisation lacks, so an admin can run step 3 or create them by hand.

The run fails, exit 1, only when a file is refused or a write to the repository's labels is.

## 4. Use the status family

The default `labels.yml` carries the status of a work item as labels: `status: todo`, `status: development`, `status: to review`, `status: to release` and `status: done`, plus `blocked`. An item carries one status at a time, and whoever moves the work moves the label. `blocked` sits beside a status rather than replacing it, and the issue says what it waits on.

Mirroring the status into a Project's Status field is something a project turns on for itself. It is not done here.

## 5. Changing the vocabulary

A project changes its own vocabulary by editing its own file and running steps 1 to 3. To start from Ahrena's, copy `references/labels.yml` or `references/issue-types.yml` into `.github/` and edit the copy.

Changing Ahrena's defaults is a change to this plugin. Both files must stay in the subset the reconciler reads: a list of mappings of scalar fields, quoted or not, with comments. `scripts/test-reconcile-vocabulary.py` reads them, and runs the reconciler against a fake `gh`:

```sh
python3 scripts/test-reconcile-vocabulary.py
```

## When this skill does not apply

Applying a label to one issue or pull request is ordinary work, done with `gh issue edit` or `gh pr edit`, and needs no reconciling. Removing a label or an issue type from the forge is never done here; it is a deliberate change somebody makes by hand. Renaming is the same: a name changed in the file reads as a new label, and the reconciler creates it beside the old one. Rename it on the forge by hand, `gh label edit`, before the next run.
