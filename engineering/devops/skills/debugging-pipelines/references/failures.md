# Failure signatures for GitHub Actions runs

Each row: what the log shows, the likely cause, the first check, and the source. Match on the signature, then confirm the cause with evidence before changing anything. A row with no vendor page names the mechanism instead, and the confirmation step carries the weight.

## Identity and permissions

| Signature in the log | Likely cause | First check | Source |
|---|---|---|---|
| `Unable to get ACTIONS_ID_TOKEN_REQUEST_URL env variable`, or an auth action saying it did not receive the OIDC request variables | the job lacks `id-token: write`, or it runs on a pull request from a fork, whose token is read-only | the job's `permissions`, and the event | [OpenID Connect reference](https://docs.github.com/en/actions/reference/security/oidc): "Without `id-token: write`, the OIDC JWT ID token cannot be requested"; [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) for forks |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | the role's trust policy does not match the token's `sub` (environment segment missing, branch not listed, or the legacy name-only form against a repository emitting the immutable subject) | compare the trust condition with the job's subject: environment named? repository created after 15 July 2026? | [configure-aws-credentials README](https://github.com/aws-actions/configure-aws-credentials), "Immutable subject claims"; [Create a role for OIDC federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html) |
| `Credentials loaded by the SDK do not match` (AWS) | a second assume-role step without `role-chaining` | the action's inputs | configure-aws-credentials README |
| `Failed to generate Google Cloud federated token` | the provider's attribute condition rejects the token, or an attribute it uses is not mapped, or a case mismatch | the provider's `attributeCondition` against the token's claims, character for character | [auth TROUBLESHOOTING](https://github.com/google-github-actions/auth/blob/main/docs/TROUBLESHOOTING.md) |
| `Failed to generate OAuth 2.0 Access Token` (Google) | service-account impersonation: the federated principal lacks Workload Identity User on the service account | the IAM binding on the service account | same page |
| `The size of mapped attribute … exceeds the 127 bytes limit` | a long repository or branch name mapped into `google.subject` | the mapping; shorten with `extract` | same page; [Troubleshooting Workload Identity Federation](https://docs.cloud.google.com/iam/docs/troubleshooting-workload-identity-federation) |
| `AADSTS70021` | no federated credential matches the token's issuer, subject and audience; or a credential changed minutes ago | the credential's subject against the job (environment, branch, tag, `pull_request`), and the time since the change | [Workload identity federation considerations](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-considerations) |
| `AADSTS700213` / `AADSTS700211` | subject mismatch / issuer mismatch | as above, one field | [Troubleshoot a workload identity service connection](https://learn.microsoft.com/en-us/azure/devops/pipelines/release/troubleshoot-workload-identity) |
| `Resource not accessible by integration` (HTTP 403 from the GitHub API) | the `GITHUB_TOKEN` lacks the scope the call needs, or the run is from a fork | the job's `permissions` against the API call | [Workflow syntax, `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax): unlisted scopes are `none` |
| A cloud call returns access denied after a successful login | the federated identity lacks the role, or the role propagates slowly | the cloud plugin's diagnosing skill | `diagnosing-aws-deployments`, `diagnosing-gcp-deployments`, `diagnosing-azure-deployments` |

## Run and scheduling

| Signature | Likely cause | First check | Source |
|---|---|---|---|
| `The job running on runner … has exceeded the maximum execution time` | the job's `timeout-minutes` (or the 360 default) elapsed: a hang or a slow step | the last step's last output, and the job's usual duration | [Workflow syntax, `timeout-minutes`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) |
| A job stays `Waiting` with a review request | the environment's required reviewers have not approved | the run's pending deployments | [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments) |
| A run is `Pending` behind another, or `Canceled` with "higher priority waiting request" | its concurrency group; `cancel-in-progress` or the `queue` limit | the group key and the other run | [Workflow syntax, `concurrency`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) |
| A pull request waits for a required check that never starts | the check's job was renamed, matrixed or filtered by `paths:`, or does not run on `merge_group` | the ruleset's required checks against the job names | [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) |
| A deploy job is rejected before starting: branch not allowed | the environment's deployment branch policy | the policy against the ref | Deployments and environments |
| A secret is empty in a fork's run | forks receive no secrets but `GITHUB_TOKEN` | the event | Events that trigger workflows |

## Flaky runs

A run that fails and passes on rerun with no change is flaky. The classes, in order of how often they turn out to be the cause: a test that depends on time, order or a shared resource (the language plugin's debugging skill); a network call to a registry or an API that rate-limits; a cache restored from a different dependency set (a key that does not hash the lock file); a runner image update (the job log's "Runner Image" section names the version); a concurrency race between two runs touching the same external resource. Compare a failed and a passed attempt of the same commit (`gh run view <id> --attempt N --log`) step by step, and fix the class, not the symptom: a retry around a flaky test hides it.
