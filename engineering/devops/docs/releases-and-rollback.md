---
id: releases-and-rollback
type: doc
clade: engineering
subclade: devops
title: Releases, deployment strategies and rollback
summary: How a release is versioned and cut, the deployment strategies (all at once, rolling, blue-green, canary, behind a flag) with when each is the wrong choice, and what a stated rollback must say.
references:
  - rules/protected-deployments.md
  - docs/delivery-pipeline.md
---

# Releases, deployment strategies and rollback

The companion to conditions 2 and 4 of [`rules/protected-deployments.md`](../rules/protected-deployments.md).

## Versioning and cutting a release

A release is a name for an artifact that was built once ([`delivery-pipeline.md`](delivery-pipeline.md)). For a library or an API that others call, the name is a Semantic Versioning number, because the consumer decides from it whether an upgrade can break them ([Semantic Versioning 2.0.0](https://semver.org/)). For a service nobody depends on by version, the commit SHA or a date-stamped tag is enough, and a semantic number promises a compatibility nobody checks.

The release is cut by the pipeline, not by hand: a tag pushed by a workflow, or a release-automation action that opens a release pull request from conventional commits, whose merge tags and publishes. Either way the job that tags holds `contents: write` and nothing else, and a GitHub release that is published as immutable is one Scorecard counts as pinned for consumers who reference it ([Scorecard checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md)). A publish to a package registry uses the registry's trusted publishing by OIDC where it exists, which zizmor `use-trusted-publishing` reports when a token is used instead.

## Strategies, and when each is wrong

| Strategy | What it is | Wrong when |
|---|---|---|
| **All at once** | Replace every instance with the new version. | The service has more than one instance and users notice a failed request: there is no moment when old and new both serve. |
| **Rolling** | Replace instances in batches behind the load balancer. | The new version cannot run beside the old one: a schema change, a changed message format, a protocol bump. Both run during the roll. |
| **Blue-green** | Stand up the new version in full, switch traffic at once, keep the old one warm. | The data layer is shared and the migration is not backwards compatible: switching back reaches a schema the old version cannot read. Also when doubling capacity costs more than the risk. |
| **Canary** | Send a fraction of traffic to the new version, compare, widen. | There is no signal to compare (no error rate, no latency per version) or too little traffic for the fraction to mean anything. A canary nobody watches is a slow all-at-once. |
| **Behind a feature flag** | Deploy dark, turn the behaviour on separately. | The change is not a behaviour (a dependency upgrade, a runtime bump), or the flag would stay forever and become configuration nobody tests both sides of. |

The managed services of each cloud implement these natively; which one a service uses is the cloud plugin's design (`designing-on-aws`, `designing-on-gcp`, `designing-on-azure`), and the pipeline triggers it.

## What a stated rollback says

A rollback is stated before the deploy, in the workflow or in a runbook the workflow links, and says four things:

1. **How**: redeploy the previous artifact by digest (the usual case, and why artifacts are kept), switch traffic back (blue-green), set the canary weight to zero, turn the flag off.
2. **Who and from where**: the workflow input or the `workflow_dispatch` that redeploys a named version, under the same environment and its approval.
3. **What it cannot undo**: a destructive migration, a message already sent, data written in the new format. Where something cannot be undone, the strategy changes: expand the schema first, deploy, then contract in a later release, so every step has a way back.
4. **How you know to use it**: the health check or the signal after the deploy that decides.

A rollback that is "revert the commit and let the pipeline run" is a roll-forward, and is a valid statement when the pipeline is fast and the change carries no migration; it is written as such, with its duration.

## Where this stops

**Database migration tooling** is the language or data plugin's; this page asks only that a migration have a way back or be split until it does.

**Incident response after a failed deploy** is operations, out of this plugin.
