<!-- Generated from issue-forms/tech-task.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# Tech Task ♻️

Well-defined small task: chore, refactoring, maintenance, documentation fix, CI change

Native issue type: `Task`. Title: `{{ brief task summary }}`.

Use this template for small, well-scoped tasks that do not justify a full feature request, epic, or user story.
Per Ahrena's `issue-quality` rule, every issue states why, what done looks like, and what it leaves to other issues.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### Why

State the motivation. What problem does this solve, what gap does it close, what risk does it remove?

Starts as:

```markdown
Why is this task needed?
```

For example:

> e.g. The tech-task template is referenced by the contribution guide but does not exist, so contributors cannot follow it.

Required.

### What

State the objective and scope. What changes? What stays out? Be specific enough that a reviewer can tell when the task is done.

Starts as:

```markdown
What needs to change?
```

For example:

> e.g. Add tech-task.yml under .github/ISSUE_TEMPLATE/ with Why/What/How sections; do not change existing templates.

Required.

### How

State the implementation approach or definition of done. List concrete steps, files involved, or success criteria.

Starts as:

```markdown
How will this be implemented or verified?
```

For example:

> e.g. Create the markdown source under framework/templates/contributing_templates/, then the GitHub Issue Form .yml.

Required.

### Task Type

Select the dominant type of this task (a project may map it to its own labels).

One of:

- evolvability ♻️ — refactoring, clean code, framework maintenance
- documentation 📃 — docs improvements or additions
- ci 🏗️ — CI/CD pipeline enhancements
- enhancement 🔝 — incremental improvement to existing feature

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

Screenshots, links, related issues, or any other relevant context.

Optional.

> To track progress, follow this issue right here on GitHub.
