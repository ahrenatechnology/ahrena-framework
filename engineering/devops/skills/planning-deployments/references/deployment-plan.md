# Deployment plan

One plan per service and target environment. Every section is filled or says why it does not apply. Identifiers in the plan are placeholders (`ACCOUNT`, `PROJECT_NUMBER`, `SUBSCRIPTION`); the real values live in the environment's variables, never in the plan.

## 1. What is deployed
- Service, artifact type (image, package, bundle), how it is built once and identified (digest).
- Source: the cloud plugin's design document, by path, or the request it answers.

## 2. Where it runs
- Cloud, region, environment name(s) in promotion order.
- The managed service and the deployment strategy, with the reason and the case where it would be wrong (from `docs/releases-and-rollback.md`).

## 3. Infrastructure
- Terraform root(s) per environment, backend, the modules (from the Terraform plugin's writing skill).
- Resources the cloud design names, and which root creates each.
- Outputs the pipeline reads, each a named attribute with its consumer.

## 4. Identity
- The deploy identity per environment: role / service account or principal set / managed identity or app.
- The trust: issuer `https://token.actions.githubusercontent.com`, the subject it accepts (`repo:ORG/REPO:environment:NAME`), the audience.
- Its permissions, scoped to what the deploy calls (the cloud plugin's identity rule, by condition).

## 5. Pipeline
- Workflows and jobs: verify, build, deploy per environment, with triggers.
- Per deploy job: environment, concurrency group, timeout, permissions.
- Secrets and variables by name and level (environment, repository).

## 6. Gates
- Required checks; environment reviewers or the protected-branch substitute; wait timer; post-deploy health check.

## 7. Rollback
- How, who and from where, what it cannot undo, the signal that triggers it.

## 8. Order of work
- The pieces in the order they land (identity and state first, then infrastructure, then the pipeline, then the first deploy), each with its owner (cloud plugin, Terraform plugin, this plugin) and what is owed from the forge or a person.

## 9. Open questions
- Each question, and who answers it.
