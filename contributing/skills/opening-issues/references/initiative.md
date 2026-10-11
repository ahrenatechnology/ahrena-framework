<!-- Generated from issue-forms/initiative.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# Initiative

Frame a problem worth solving and group the epics that address it

Native issue type: `Initiative`. Title: `{{ brief initiative summary }}`.

An initiative frames a problem and gathers the epics that solve it. Keep it about the problem and the outcome, not the solution.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### Problem

What problem are we solving, for whom, and why now?

Starts as:

```markdown
Problem
```

For example:

> ex. Release status is reconciled by hand every week; it is invisible outside each repo, so planning runs on stale information.

Required.

### Outcomes

The measurable outcomes that tell us the initiative succeeded. Prefer numbers.

Starts as:

```markdown
Outcomes
```

For example:

> ex. Status is one view, zero manual reconciliation; lead time from idea to production down 30%.

Required.

### Scope and epics

What is in scope, what is explicitly out, and the epics this initiative will spawn (link them as they are created).

Starts as:

```markdown
Scope and epics
```

For example:

> ex. In: the pipeline vocabulary and the project view. Out: deployment automation. Epics: #.., #..

Optional.
