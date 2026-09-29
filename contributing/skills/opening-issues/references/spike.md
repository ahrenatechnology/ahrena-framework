<!-- Generated from issue-forms/spike.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# Spike 🔎

A timeboxed question that must be answered before the work that depends on it can be planned or built

Native issue type: `Task`. Title: `{{ the question, ending in a question mark }}`.

Use this template when something is not known well enough to plan or build: whether an approach works, what a system can take, which option to pick.
A spike produces a decision, not a feature. It is timeboxed, and it blocks every item that waits on its answer.
Per Ahrena's `issue-quality` rule, every issue states why, what done looks like, and what it leaves to other issues.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### Question

The one question this spike answers. If there are two, it is two spikes.

For example:

> e.g. Can the ledger take 5,000 writes a second on the current schema?

Required.

### Why it blocks

What cannot be planned, estimated or built until this is answered, each by number. Those items are blocked by this spike.

For example:

> e.g. #140 (partition the ledger) and #141 (bulk import) both depend on the answer.

Required.

### Timebox

The most time the answer is worth. When it runs out, the decision is taken on what is known by then.

For example:

> e.g. 2 days

Required.

### Approach

How the question will be answered: the measurement, the prototype, the documentation to read, the people to ask.

For example:

> e.g. Load-test a copy of the schema with the production write mix, at 1k, 5k and 10k writes a second.

Optional.

### Acceptance criteria

A spike's criteria are judged by a reader, because what it produces is a decision, not code.

Starts as:

```markdown
- AC-1: The question is answered, with the evidence that answers it. (checked by review)
- AC-2: The decision is recorded, as a decision record when it will be questioned later, or as a comment here when it will not. (checked by review)
- AC-3: The items it blocked are updated, or new ones opened, to match the answer. (checked by review)
```

Required.

### Left to other issues

The work this spike informs but does not do, each by number.

Optional.

> A spike's code is thrown away, or rewritten under its own issue. Nothing it produces lands on trunk as a feature.
