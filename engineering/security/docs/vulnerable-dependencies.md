---
id: vulnerable-dependencies
type: doc
clade: engineering
subclade: security
title: Where the dependency thresholds come from
summary: The origin of the zero-critical-CVE limit, the lockfile condition and the record-every-CVE condition, and why none depends on a particular security monitor.
references:
  - rules/vulnerable-dependencies.md
---

# Where the dependency thresholds come from

This document explains `rules/vulnerable-dependencies.md`: SEC-1, SEC-2 and SEC-5 of the PR quality rubric of epic 323.

## The figures

None is measured. All are maintainer policy (the standard of issue 34), declared on 14 November 2026: zero critical or high CVEs in development, and every CVE found in production recorded as an issue unless something already records it. The `critical or high` cut-off follows the `--audit-level=high` convention of the npm audit command, which is the one most ecosystems' scanners offer.

## Why development and production are separate

A pull request can be held to zero because it chooses its dependencies. Production is already shipped: a new advisory against it appears without a change, so the condition cannot block a pull request, and what it can ask for is that the finding is not lost. Recording it as an issue gives a person an owner and a date, and the check for an existing record avoids a second issue for what Dependabot or another monitor has already raised.

## Why no condition names a monitor

Projects differ: one runs Dependabot, one a code-scanning product, one nothing. A condition that required one would fail the others for what they chose not to buy and would couple the framework to a vendor. SEC-5 reads whatever exists and still works with nothing, so the framework asks for the outcome, every CVE recorded, rather than for a tool.

## Why pinning is a condition

A dependency resolved to a range can change between the scan that passed and the install that ran. A lockfile entry with a version and a hash is what the scan checked, and an install script runs code at install time before any test does, which is why one that nobody reviewed is a failure of its own.

## Where this stops

This document does not choose a scanner. It also does not cover reviewing whether a dependency is trustworthy, which is `skills/reviewing-supply-chain`.
