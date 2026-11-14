# Where AWS records a deployment failure, and the signatures that recur

Each section names where the first failure is recorded and the signatures AWS documents, with the page each comes from. Read on 2026-11-14; when a page has moved, the service's troubleshooting index is the place to start.

## CloudFormation, CDK and SAM

- **Where:** the stack's events. Find the failure event and "view the status reason for that event"; events carry operation IDs that can be filtered on. For a failure inside an EC2 instance, the cloud-init and cfn logs under `/var/log/` ([Troubleshooting CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/troubleshooting.html)).
- **`UPDATE_ROLLBACK_FAILED`:** fix the cause, then "continue rolling back the update" with `ContinueUpdateRollback`; if that fails, the rollback can be forced or resources skipped with `ResourcesToSkip`, which leaves them inconsistent with the template (same page). The operation belongs to the stack's owner.

## Amazon ECS

- **Where:** the stopped task. In the console, filter to stopped tasks and open the stopped status to see "the stopped reason"; stopped tasks appear in the console for one hour. With the CLI, `describe-tasks` returns `stopCode`, `stoppedReason` and each container's reason ([Viewing Amazon ECS stopped task errors](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/stopped-task-errors.html)).
- **Signatures:** the error-message categories include `ResourceInitializationError` and `CannotPullContainer`, each with its own troubleshooting page ([Amazon ECS stopped tasks error messages](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/stopped-task-error-codes.html)). When an image cannot be pulled from a private subnet, check the route to the registry — a NAT gateway or an interface endpoint — as `docs/networking.md` describes.

## AWS Lambda

- **Deployment** ([Troubleshoot deployment issues in Lambda](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-deployment.html)): `EACCES: permission denied` on a file in `/var/task` (file permissions in the package); `RequestEntityTooLargeException` from `UpdateFunctionCode` (the package exceeds the direct-upload limit).
- **Invocation** ([Troubleshoot invocation issues in Lambda](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-invocation.html)): `Task timed out after 3.00 seconds` (`Sandbox.Timedout`; the configured timeout, not the code, ended it); `Couldn't find valid bootstrap(s)` (`Runtime.InvalidEntrypoint`; handler or runtime mismatch).
- **Limits** that turn into failures: timeout up to 900 seconds, synchronous payloads up to 6 MB each way ([Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)).

## AWS CodeDeploy

- **Where:** the deployment's failed lifecycle event; the troubleshooting guide is split by compute platform (EC2 and on-premises, ECS, Lambda) and has an error-code reference ([Troubleshooting CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/troubleshooting.html)).

## Access denied

- **Shape:** "User {user} is not authorized to perform {action} on {resource} because {context}"; the context names the policy type, explicit or implicit, and only one type when several deny ([Troubleshoot access denied error messages](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html)).
- **A deploy that passes a role:** a stack update that creates or changes a function, task or instance which runs under a role fails when the deploying principal may not pass that role. The message names the action `iam:PassRole`, the role as resource and, typically, an implicit deny because no identity-based policy allows it; the fix is a grant of `iam:PassRole` on that role alone in the deploying principal's identity policy, never on `*` (IAM Access Analyzer policy validation warns on a wildcard resource for it, [check reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-reference-policy-checks.html)).
- **Test a fix:** the IAM policy simulator evaluates identity-based policies, permissions boundaries, SCPs and resource-based policies without a real request; it does not support RCPs ([IAM policy testing with the IAM policy simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html)).

## Across layers

- **CloudTrail event history:** "the past 90 days of management events" per Region; data events are not in it ([Working with CloudTrail event history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html)).
- **VPC Flow Logs:** the IP traffic to and from an interface, to tell "blocked" from "never sent" ([Logging IP traffic using VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)).
