<!-- Generated from issue-forms/plan.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# Plan 📋

Sub-issue representing an executable unit of work inside a parent Issue (User Story / Bug / Tech Task)

Native issue type: `Task`. Title: `{{ brief plan summary }}`.

Use this template to file an executable unit of work as a sub-issue of a parent Issue (User Story, Bug, or Tech Task).
A Plan is the atomic chunk that produces one or more PRs and closes when its scope is delivered. The parent Issue closes when all its Plans close.

Per Ahrena's `issue-quality` rule, every issue states why, what done looks like, and what it leaves to other issues.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### Parent Issue

Issue number of the parent (User Story / Bug / Tech Task). The agent links this Plan as a sub-issue of that parent.

For example:

> e.g. #140

Required.

### Why

What problem does this Plan close inside the parent's scope? Tie it to the parent's Definition of Done.

Starts as:

```markdown
Why is this Plan needed within the parent Issue?
```

For example:

> e.g. Without renaming simple-task → tech-task, every subsequent Plan that depends on the new template name is blocked.

Required.

### What

Concrete deliverable. What files change? What stays out (handled by sibling Plans)?

Starts as:

```markdown
What changes? What stays out?
```

For example:

> e.g.
> - Rename .github/ISSUE_TEMPLATE/simple-task.yml → tech-task.yml
> - Rename framework/templates/contributing_templates/simple-task.md → tech-task.md
> - Add bug.yml and plan.yml templates
> - Out of scope (sibling Plans): governance lexis rewrite, kata updates

Required.

### How

Implementation approach + Definition of Done. Concrete steps, files involved, success criteria.

Starts as:

```markdown
Steps + Definition of Done:
```

For example:

> e.g.
> - Branch tech/{N}-rename-templates-add-bug-plan
> - git mv preserves history
> - DoD: bug and plan templates render in the GitHub UI

Required.

### Estimated PRs

How many PRs do you expect to close this Plan? A plan that needs many is a sign it should be split further.

One of:

- 1 — single atomic PR
- 2–3 — small chain, possibly stacked
- 4–6 — medium chain; consider further decomposition
- 7+ — too large; re-decompose into more Plans

Required.

### Acceptance criteria

One observable behaviour per line, numbered AC-1 upward and never renumbered, so a test can name it as #<issue>/AC-<n>. End a criterion no test can decide with (checked by review).

Starts as:

```markdown
- AC-1: 
```

Required.

### Left to other issues

Decisions already made, work blocked elsewhere, and parts another issue owns, each by number.

Optional.

### Additional Context

Dependencies on sibling Plans, blocking external work, links to designs/docs, or any other relevant context.

Optional.

> After creation, link this Plan as a sub-issue of the Parent Issue (`gh api -X POST repos/{owner}/{repo}/issues/{parent}/sub_issues -F sub_issue_id={this_id}`).
