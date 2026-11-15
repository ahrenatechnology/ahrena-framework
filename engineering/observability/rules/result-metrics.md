---
id: result-metrics
type: rule
clade: observability
title: A story declares the metrics of its result
statement: A story declares the metrics of its result (name, type, unit, success); the pull request that delivers it emits them and tests that each is emitted.
enforcement: judgment
references:
  - docs/opentelemetry.md
---

# A story declares the metrics of its result

Two conditions, MET-1 and MET-2 of the PR quality rubric (#323). A story is done when the result it was written for is measurable, not when the code runs. `docs/opentelemetry.md` cites the OpenTelemetry metrics text behind the fields.

None of these conditions adds an abstraction, so the abstraction trigger of `rules/yagni.md` in the fundamentals plugin does not gate them. Both are decided by the consuming project: MET-1 by the issue template's field, MET-2 by a test with an in-memory exporter.

## Conditions

1. **MET-1. The story's issue declares the metrics that measure its result: for each, a name, an instrument type, a unit and what success means.** The threshold is a field filled with at least one metric. The name follows the OpenTelemetry instrument-name syntax, the type is one of counter, histogram, gauge or up-down counter, the unit is a case-sensitive string such as `s` or `{order}`, and success is a sentence or a threshold a person can check. A story whose result is not measurable says so in the field and names who accepted that. Decided by the issue's field. The detector does not exist yet: today's issue forms carry the metrics as optional free text, so the field with type, unit and success, and the check that fills it, are tracked in the detectors sub-issue of #323 and, until then, a reviewer reads the issue.

2. **MET-2. The pull request that delivers the story emits each declared metric, and a test confirms each is emitted.** The threshold is 100% of the declared metrics. The test drives the story's flow with an in-memory metric reader and asserts one data point of the declared name, type and unit. Decided by the set difference between the declared names and those the tests assert.

## Where this stops

**MET-1 does not choose the thresholds of success.** It requires them to be written; the product owner decides them.

**MET-1 does not ask a metric for a technical task with no user-visible result.** A refactor's result is not a business metric; the field says "none" and the type of the issue explains why.

**MET-2 does not ask the delivering pull request to build a dashboard or an alert.** It emits and tests the data point.

**In a story delivered across several pull requests, MET-2 binds the one that makes the result occur;** the others cite it.

**These conditions are judgment, and the detectors are named rather than shipped.** The issue template's field belongs to the contributing plugin and the in-memory reader to the project.
