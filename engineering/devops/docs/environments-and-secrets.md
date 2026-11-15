---
id: environments-and-secrets
type: doc
clade: engineering
subclade: devops
title: Environments, secrets and what a pipeline log may show
summary: What a GitHub environment attaches to a deploy and on which plans, where a secret, a variable and a cloud identifier each belong, how redaction works and where it fails, and what a step may print.
references:
  - rules/protected-deployments.md
  - rules/log-exposure.md
  - rules/cloud-credentials.md
  - docs/cloud-authentication.md
  - ahrena-engineering-security:docs/layer-exposure.md
---

# Environments, secrets and what a pipeline log may show

The companion to [`rules/protected-deployments.md`](../rules/protected-deployments.md) and [`rules/log-exposure.md`](../rules/log-exposure.md).

## What an environment attaches

An environment is a name a job references with `environment:`, and the place GitHub hangs a deploy's controls ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)):

- **Required reviewers**: up to six users or teams, of whom "only one … needs to approve"; with "Prevent self-review", the person who triggered the run cannot approve it ([Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)).
- **A wait timer**, from 1 to 43,200 minutes, which does not bill.
- **Deployment branches and tags**: no restriction, protected branches only, or selected patterns. "Protected branches only" lets every branch deploy when no branch is protected, so it is only as strong as the ruleset behind it.
- **Environment secrets and variables**, which only jobs referencing the environment receive, and which a job "cannot access … until one of the required reviewers approves it".
- **Custom deployment protection rules**, which GitHub still calls public preview.

**Availability decides the design.** On Free, every environment feature is for public repositories. On Pro and Team, a private repository gets branch rules, environment secrets and variables, but not required reviewers, wait timers or custom rules. A private repository on those plans therefore approves a deploy at the merge: production deploys only from a protected branch, the branch's ruleset requires an approved pull request ([`repository-governance.md`](repository-governance.md)), and the deploy job says in a comment that the merge is its approval. That is the substitute [`protected-deployments.md`](../rules/protected-deployments.md) condition 3 accepts, and it is weaker: nobody looks at the deploy itself, only at the change.

## Where a value belongs

| Value | Belongs in | Why |
|---|---|---|
| A credential the cloud can replace with federation | nowhere: OIDC | [`rules/cloud-credentials.md`](../rules/cloud-credentials.md) |
| A credential with no federation (a third-party API key, a registry token) | an environment secret for the environment that uses it | only approved jobs of that environment read it |
| A cloud identifier the login needs (role ARN, workload identity provider, client and tenant ID) | an environment variable; an environment secret on a public repository | not a credential, but the third class of the exposure rule; Microsoft's guide puts the Azure ones in environment secrets on public repositories ([Authenticate to Azure from GitHub Actions by OpenID Connect](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)) |
| A setting that is neither (a region, a feature flag) | a variable | readable, auditable, not masked |

Repository secrets are for what every job may read; organisation secrets for what every repository may read. A production credential is neither.

## How redaction works, and where it fails

The runner replaces the values of registered secrets in the log with `***`. GitHub's own page says "automatic redaction is not guaranteed", warns against a secret held as a blob of JSON, XML or YAML, says a transformed value (Base64 of a secret) has to be registered too, and says values that are not GitHub secrets are masked with `::add-mask::VALUE` ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). The mask is per value per job, and must be set "before outputting it" ([Workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)). Three consequences:

1. **A token a step mints is printed in clear** unless the step masks it first. `gcloud auth print-access-token` in a log is a working credential until it expires.
2. **A secret used as structured data is not redacted field by field**; zizmor `unredacted-secrets` reports `fromJSON(secrets.X)`.
3. **Masking hides; it does not stop the value leaving.** A step that writes a secret to an artifact, a pull-request comment or a cache sends it somewhere the mask does not reach.

So the control is not printing, which [`log-exposure.md`](../rules/log-exposure.md) states condition by condition, and redaction is what catches a mistake.

## What a step may print

A pipeline log is an exit in the sense of [`layer-exposure.md`](../../security/rules/layer-exposure.md), whose doc companion carries the incident behind it. A step prints named fields a reader needs: the version deployed, the environment, the duration, a link to the run or the deployment, the count of resources changed. It does not print an account, project or subscription identifier, a role or a policy, a resource identifier, a hostname that resolves only inside the network, or a cloud SDK's whole error. A failure prints the error's code and the operation; the detail goes to the cloud's own log, which only its owners read. The Terraform plan is governed by the Terraform plugin's [`toolchain.md`](../../terraform/docs/toolchain.md): the human-readable plan may be printed and posted, the JSON plan and the outputs never, and the plan file is an artifact with the state's sensitivity, kept out of public artifacts.

Debug logging (`ACTIONS_STEP_DEBUG`, `ACTIONS_RUNNER_DEBUG`) is enabled by a secret or variable of that name ([Enabling debug logging](https://docs.github.com/en/actions/how-tos/monitor-workflows/enable-debug-logging)). The page gives no assurance about what debug output contains, so it is turned on for a private rerun and off again.

## Where this stops

**Secret stores beyond GitHub** (a cloud's secret manager, read at run time through the federated identity) are the cloud plugin's design; a pipeline that reads one is held to the same printing rules.

**Who may read a log** is the repository's visibility and the organisation's settings, not a workflow's.
