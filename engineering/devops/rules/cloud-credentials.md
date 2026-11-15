---
id: cloud-credentials
type: rule
clade: engineering
subclade: devops
title: A workflow reaches a cloud by OIDC federation, not by a stored key
statement: A workflow authenticates to AWS, Google Cloud or Azure by OIDC federation; a long-lived key in a secret stays only with a recorded reason.
enforcement: judgment
references:
  - docs/cloud-authentication.md
  - ahrena-engineering-aws:docs/identity-and-access.md
  - ahrena-engineering-gcp:docs/identity-and-access.md
  - ahrena-engineering-azure:docs/identity-and-access.md
---

# A workflow reaches a cloud by OIDC federation, not by a stored key

GitHub issues each job a short-lived OIDC token, and each of the three clouds exchanges it for credentials valid for that job alone ([OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)). A key stored as a secret is valid until someone rotates it, works from anywhere, and is one leaked log line from being someone else's. GitHub's [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) says federation lets a project "stop storing these credentials as long-lived secrets". Each cloud plugin states its own side of the same rule: condition 3 of [`least-privilege.md`](../../aws/rules/least-privilege.md) for AWS, condition 4 of [`identity-and-access.md`](../../gcp/rules/identity-and-access.md) for Google Cloud, condition 3 of [`identity-and-access.md`](../../azure/rules/identity-and-access.md) for Azure. [`docs/cloud-authentication.md`](../docs/cloud-authentication.md) carries the setup for each.

## Conditions

A line that carries a decision-record pointer (`# ADR-12`) is skipped: the record names why federation does not serve, as the cloud plugins require.

1. **No cloud login action is given a long-lived key.** `aws-actions/configure-aws-credentials` with `aws-access-key-id` or `aws-secret-access-key`; `google-github-actions/auth` with `credentials_json`; `azure/login` with `creds`. Decided by `hooks/check-workflows.py`.
2. **No environment variable carries a cloud key from a secret.** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GOOGLE_CREDENTIALS`, `GOOGLE_CLOUD_KEYFILE_JSON`, `ARM_CLIENT_SECRET`, `AZURE_CLIENT_SECRET`, the certificate passwords and the like, at workflow, job or step level, whose value reads `secrets.`. Decided by `hooks/check-workflows.py`.
3. **No step signs in on the command line with a key file or a client secret.** `gcloud auth activate-service-account --key-file`, `az login --service-principal` with `-p` or `--password`. Decided by `hooks/check-workflows.py`.
4. **The cloud side of the federation is scoped to the repository and, for a deploy, to the environment.** The AWS trust policy conditions `token.actions.githubusercontent.com:sub`; the Google Cloud pool has an attribute condition on the repository owner or its ID; the Azure federated credential names the subject. Decided by review, with the cloud plugin's review skill, because the trust lives in the cloud and not in the workflow.

## Where this stops

**The hook reads names it knows.** A key under another variable name, or passed to a third-party action's input, passes it; `reviewing-secrets` sweeps every added line for a credential by its value.

**A self-hosted runner on the cloud's own compute** authenticates with the identity it runs under (an instance role, an attached service account, a managed identity), which is the cloud plugin's rule and passes this one: nothing is stored.

**A cloud this rule does not name** is held to the same principle by review, through `reviewing-secrets` and the supply-chain discipline.

**This rule declares judgment because condition 4 needs a reader.** `hooks/check-workflows.py` decides conditions 1 to 3 exactly, and its tests pin each; the statement reaches the agent's instruction file so the rest is read.
