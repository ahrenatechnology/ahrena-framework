# Failure signatures on Google Cloud

Opened by step 3 of `SKILL.md`. Each entry is a signature as it appears in an error or a log, what it means, where to confirm it, and the page that says so. Pages were read on 2026-11-14 under `docs.cloud.google.com`. A signature that matches is a hypothesis until step 4 confirms it.

## Access

| Signature | Meaning | Confirm with | Page |
|---|---|---|---|
| `PERMISSION_DENIED`, "does not have PERMISSION access to", "Permission 'PERMISSION' denied on resource (or it may not exist)" | the principal lacks the permission, a deny policy or principal access boundary blocks it, or the resource does not exist; the message carries a unique error ID and a Policy Troubleshooter link | Policy Troubleshooter with the principal, resource and permission; it needs `roles/iam.securityReviewer` and does not cover Cloud Storage ACLs or VPC Service Controls | [Permission error messages](https://docs.cloud.google.com/iam/docs/permission-error-messages); [Troubleshoot access](https://docs.cloud.google.com/iam/docs/troubleshooting-access) |
| the grant was just made and access still fails | IAM is eventually consistent: a policy change typically takes 2 minutes and potentially 7 or longer; a group membership change several minutes, potentially hours | wait and retry before changing anything else | [Access change propagation](https://docs.cloud.google.com/iam/docs/access-change-propagation) |
| `Permission 'iam.serviceaccounts.actAs' denied on service account` on a Cloud Run or Cloud Build deploy | the deployer may not act as the runtime service account | grant the deployer the right to act as that one service account, not on the project | [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting); [Cloud Build troubleshooting](https://docs.cloud.google.com/build/docs/troubleshooting) |
| "Request is prohibited by organization's policy", with a `vpcServiceControlsUniqueIdentifier` | a VPC Service Controls perimeter blocked the request | the audit log entry, then the violation analyzer with that ID | [VPC Service Controls troubleshooting](https://docs.cloud.google.com/vpc-service-controls/docs/troubleshooting); [Violation analyzer](https://docs.cloud.google.com/vpc-service-controls/docs/violation-analyzer) |
| "Organization Policy check failure", naming a constraint | an organization policy refuses the configuration | `gcloud org-policies list --project=PROJECT_ID` and `describe` for the constraint; it may be inherited from a folder or the organization | [Troubleshoot organization policies](https://docs.cloud.google.com/organization-policy/troubleshoot-policies) |
| a build suddenly runs as a different identity | since May–June 2024 Cloud Build may use the Compute Engine default service account for new projects; the default depends on organization policy | the build's service account; specify your own | [Cloud Build service account](https://docs.cloud.google.com/build/docs/cloud-build-service-account); [Service account updates](https://docs.cloud.google.com/build/docs/cloud-build-service-account-updates) |

## Service and quota

| Signature | Meaning | Confirm with | Page |
|---|---|---|---|
| `SERVICE_DISABLED`, "API has not been used in project ... before or it is disabled" | the API is not enabled in the project; after enabling, wait a few minutes | `gcloud services enable` with Service Usage Admin | [Service Health troubleshooting](https://docs.cloud.google.com/service-health/docs/troubleshooting); [Enable and disable services](https://docs.cloud.google.com/service-usage/docs/enable-disable) |
| `429`, `QUOTA_EXCEEDED`, `ResourceExhausted`, "Quota QUOTA_NAME exceeded. Limit: ..." | a quota is exhausted | Quotas & System Limits for current and peak usage; request an adjustment | [Troubleshoot quota errors](https://docs.cloud.google.com/docs/quotas/troubleshoot); [VM creation troubleshooting](https://docs.cloud.google.com/compute/docs/troubleshooting/troubleshooting-vm-creation) |

## Cloud Run

| Signature | Meaning | Confirm with | Page |
|---|---|---|---|
| container failed to start; "Revision REVISION_NAME is not ready and cannot serve traffic" | the container did not listen on the injected `PORT` (requests go to 8080 by default) on `0.0.0.0` within the startup window (4 minutes) | the revision's logs in Cloud Logging; the container contract | [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting); [Container runtime contract](https://docs.cloud.google.com/run/docs/container-contract) |
| "was found to be using too much memory" | the instance exceeded its memory limit; files written to the in-memory filesystem count | memory metric; raise the limit or fix the leak | [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting) |
| image pull failure | wrong image URL, or a cross-project or perimeter restriction on the registry | the image URL in Artifact Registry; audit log for `VPC_SERVICE_CONTROLS` | [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting) |
| 401 or 403 on invoke, "The request was not authenticated" | the caller lacks `run.routes.invoke` or sent no identity token | the caller's identity and its Cloud Run Invoker grant | [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting) |
| liveness probe failure in the logs | the configured probe failed | the probe configuration | [Health checks](https://docs.cloud.google.com/run/docs/configuring/healthchecks) |

## GKE

| Signature | Meaning | Confirm with | Page |
|---|---|---|---|
| `ImagePullBackOff`, `ErrImagePull` | the kubelet cannot pull: 403 is access to the image, 401 the node service account; private clusters need Private Google Access | `kubectl describe pod`; node pool scopes; image and tag exist | [Image pull troubleshooting](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/image-pulls) |
| `CrashLoopBackOff` | the container keeps exiting; the status itself names no cause | `kubectl logs` and `describe` | [Deployed workloads](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads) |
| Pod `Pending`, insufficient resources | not enough CPU or memory, or the node pool is at its maximum | `kubectl describe nodes` | [Deployed workloads](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads) |
| Workload Identity Federation for GKE: access denied right after start, or timeouts reaching the metadata server | a grant still propagating, or the metadata server not ready for a few seconds; egress to `sts.googleapis.com:443` blocked | retry with a delay; egress rules | [GKE authentication troubleshooting](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/authentication) |

## Infrastructure as code

| Signature | Meaning | Confirm with | Page |
|---|---|---|---|
| Infrastructure Manager revision `REVISION_FAILED` | the Terraform run failed | the revision's `stateDetail`, `errorCode`, `tfErrors` and the Cloud Build ID it names; the error logs in the artifacts bucket; a 403 in `tfErrors` is the service account's permission | [Infrastructure Manager troubleshooting](https://docs.cloud.google.com/infrastructure-manager/docs/troubleshoot-deployments) |
| a Cloud Deploy rollout `FAILED` | a job failed and was not ignored | `gcloud deploy rollouts describe`; retry or ignore the job | [Manage rollouts](https://docs.cloud.google.com/deploy/docs/deployment-strategies/manage-rollout) |

## Where to look

- **Logs Explorer**: a query is a Boolean expression; filter on the monitored resource type first, then `severity>=ERROR` ([Logging query language](https://docs.cloud.google.com/logging/docs/view/logging-query-language); [Logs Explorer](https://docs.cloud.google.com/logging/docs/view/logs-explorer-interface)).
- **Admin Activity audit logs** are always written and record who changed what: `protoPayload.methodName` names the operation and `protoPayload.authenticationInfo.principalEmail` the principal ([Audit logs](https://docs.cloud.google.com/logging/docs/audit); [Understanding audit logs](https://docs.cloud.google.com/logging/docs/audit/understanding-audit-logs)). Data Access logs are off by default except for BigQuery.
- **Error Reporting** groups errors from the logs by cause ([Viewing errors](https://docs.cloud.google.com/error-reporting/docs/viewing-errors)).
- **Before a fix that changes policy**: Policy Simulator replays up to 90 days of access against a proposed allow policy ([IAM Policy Simulator](https://docs.cloud.google.com/policy-intelligence/docs/iam-simulator-overview)); an organization policy can run in dry-run mode, which logs violations without blocking ([Dry-run organization policy](https://docs.cloud.google.com/resource-manager/docs/organization-policy/dry-run-policy)).
