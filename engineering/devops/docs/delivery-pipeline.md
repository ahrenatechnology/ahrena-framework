---
id: delivery-pipeline
type: doc
clade: engineering
subclade: devops
title: The delivery pipeline, from commit to production
summary: The stages a change passes through - verify, build once, release, deploy to each environment in order - what gates each stage, how an artifact is promoted rather than rebuilt, and where infrastructure changes enter the same path.
references:
  - docs/github-actions.md
  - docs/environments-and-secrets.md
  - docs/releases-and-rollback.md
  - docs/repository-governance.md
  - rules/protected-deployments.md
---

# The delivery pipeline, from commit to production

This page argues the path a change takes and what gates each step. It is the frame the skills of this plugin plan and review against. The mechanics of each step are in [`github-actions.md`](github-actions.md), the controls in [`environments-and-secrets.md`](environments-and-secrets.md), and the release in [`releases-and-rollback.md`](releases-and-rollback.md).

## The stages

1. **Verify, on the pull request.** Build, test, lint, the language plugin's gate, the security scanners, `terraform plan` for an infrastructure change. Runs on `pull_request` with a read-only token and no secret, so it is safe on a fork ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)). Gate: the ruleset's required status checks ([`repository-governance.md`](repository-governance.md)).
2. **Merge, through review.** A pull request approved by a code owner, on a branch that blocks force pushes; with a merge queue, the checks run again on the merged result (`merge_group`). Gate: the ruleset.
3. **Build once, on the merge commit.** One artifact (an image by digest, a package, a bundle), with its provenance attested (`actions/attest`, [Using artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)), stored where every later stage reads the same bytes. Gate: the build's own tests.
4. **Deploy to the first environment**, usually staging, from that artifact. Gate: the environment's branch rule and concurrency group; a smoke test after the deploy.
5. **Promote to the next environment**, production last, with the same artifact. Gate: the environment's required reviewer, or the merge where the plan has none; the previous environment's health; a wait timer when a soak is wanted.
6. **Verify after the deploy**, and roll back on failure ([`releases-and-rollback.md`](releases-and-rollback.md)).

## Promote, do not rebuild

The artifact that reached production is the one that was tested in staging, identified by digest, not rebuilt from the same commit. A rebuild can resolve a different dependency, pick up a different base image, or run on a different runner; then what was tested is not what runs. Each environment's deploy job takes the digest as an input, and the attestation lets the deploy verify where it came from (`gh attestation verify`). Attestations alone give SLSA v1.0 Build Level 2, and a reusable workflow that builds helps reach Level 3 ([Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)).

## One job per environment

Each environment is its own job (or its own call of a reusable deploy workflow) with `environment:`, its own concurrency group and its own approval. A matrix over environments would share one approval and race. The jobs are chained with `needs:`, so production cannot start before staging succeeded; `concurrency` keyed on the environment name keeps one deploy per environment at a time ([`protected-deployments.md`](../rules/protected-deployments.md)).

## Infrastructure in the same path

An infrastructure change follows the same stages with Terraform's steps: plan on the pull request, apply after merge from the plan the review read, one environment at a time. The Terraform plugin owns the order and what the plan log may show ([`toolchain.md`](../../terraform/docs/toolchain.md)); the cloud plugin owns what is created. The pipeline's part is that the apply job references the environment, holds its concurrency group, federates to the cloud with the environment's subject, and does not cancel in flight. An application deploy that needs a new resource waits for the infrastructure deploy of the same environment, through `needs:` or a separate pipeline whose success the application's deploy checks.

## What gates are not

A gate decides from evidence: a check's result, a reviewer's approval, a health signal. A step that sleeps and hopes, or a manual `workflow_dispatch` to production with no environment, is not a gate. A required reviewer who approves without looking is the organisation's problem, not the pipeline's; the pipeline's job is to show them the version, the plan and the diff since the last deploy in the deployment's summary.

## Where this stops

**Operations after the deploy** (service-level objectives, alerts, incident response) are not this plugin's; `ahrena-engineering-reliability` and `ahrena-engineering-observability` hold the review side today.

**Container orchestration** as a target (a Kubernetes cluster's own rollout) is the cloud plugin's service and the project's choice; this page treats it as one deploy step among others.
