# Bug

Something that does not match what was specified or promised. Native type: `Bug`.

Title: the defect as observed. "Confirmation email not sent when payment retries".

```markdown
## Impact

Who is affected, how many, since when, and what it costs them. Link the
incident, the report or the failing run.

## Expected and actual

Expected: <what should happen>
Actual: <what happens, with the exact error, log line or screenshot>

## Reproduction

1. <step>
2. <step>
3. <observe>

Environment: <where, and the commit if known>

## Severity

One of: blocker (no workaround, stops a release), critical (core flow broken,
painful workaround), major (non-core flow broken), minor (cosmetic or edge).

## Acceptance criteria

- AC-1: Given <the reproduction's state>, when <its action>, then <the expected behaviour>.
- AC-2: A regression test reproduces the defect, fails before the fix and passes after.

## Left to other issues

- <the root cause's other symptoms, or the hardening this does not do, each by number>
```

AC-1 is the reproduction turned into a criterion, so the regression test names it as `#<issue>/AC-1` and the trace is automatic.
