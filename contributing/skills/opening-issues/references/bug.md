<!-- Generated from issue-forms/bug.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# Bug 🐞

Report a defect: code, behavior, or documentation that does not match the declared specification

Native issue type: `Bug`. Title: `{{ brief bug summary }}`.

Use this template for defects: code, behavior, or documentation that does not match the declared specification.
Per Ahrena's `issue-quality` rule, every issue states why, what and how — for bugs, Why is the impact, What is the observable defect, How is the verification path.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### Why (impact)

Who is affected and what is the consequence? Link to incident, customer report, or failing test if applicable.

Starts as:

```markdown
Who is affected and what breaks?
```

For example:

> e.g. Payment confirmation emails dropped for ~2% of orders since 2026-05-09; customers re-submit payment thinking it failed.

Required.

### What (observable defect)

Describe what is happening vs. what should happen. Include exact error messages, log lines, or screenshots.

Starts as:

```markdown
Expected behavior:

Actual behavior:
```

For example:

> Expected: 200 OK with confirmation_id in response.
> Actual: 500 Internal Server Error; log line "NoneType has no attribute 'send'".

Required.

### How (reproduction + verification path)

Minimum steps to reproduce; environment (prod/staging/local); commit SHA if known; how a fix will be verified.

Starts as:

```markdown
Steps to reproduce:
1.
2.
3.

Environment:

Verification:
```

For example:

> Steps to reproduce:
> 1. POST /v1/payments with valid body
> 2. Wait 2s
> 3. Observe 500
>
> Environment: production, commit abc1234, region us-east-1
> Verification: integration test in tests/payments/test_confirmation_email.py

Required.

### Severity

Select the dominant severity (a label may be applied accordingly per future governance).

One of:

- blocker — blocks release, no workaround
- critical — broken core flow, workaround exists but painful
- major — broken non-core flow or degraded UX
- minor — visual/typo/edge case

Required.

### Acceptance criteria

One observable behaviour per line, numbered AC-1 upward and never renumbered, so a test can name it as #<issue>/AC-<n>. End a criterion no test can decide with (checked by review).

Starts as:

```markdown
- AC-1: Given <the reproduction>, when <its action>, then <the expected behaviour>.
- AC-2: A regression test reproduces the defect, fails before the fix and passes after.
```

Required.

### Left to other issues

Decisions already made, work blocked elsewhere, and parts another issue owns, each by number.

Optional.

### Additional Context

Screenshots, links, related issues, logs, or any other relevant context.

Optional.

> To track progress, follow this issue right here on GitHub.
