---
name: diagnosing-aws-deployments
description: Use when a deployment to AWS failed or a just-deployed service does not work - a CloudFormation or CDK stack in a failed or rollback state, an ECS task that stops, a Lambda function that will not update or errors on invocation, a CodeDeploy deployment that fails, an access-denied error from a service that used to work. Finds the first failure, reads what AWS recorded about it, names the cause and the smallest fix, and reports without copying account IDs, ARNs or policies out of the account.
type: skill
clade: engineering
subclade: aws
references:
  - rules/exposure.md
  - rules/least-privilege.md
  - docs/identity-and-access.md
  - docs/networking.md
---

# Diagnosing AWS deployments

The goal is the first thing that failed, the cause AWS recorded for it, and the smallest change that fixes it. Later failures in the same deployment are usually consequences; reading them first is the recurring way a diagnosis goes wrong.

Read-only throughout. This skill describes, lists and reads; it does not update a stack, restart a service or change a policy. The fix is proposed, and applied through the project's own pipeline.

## 1. Locate the failing layer

Name which of these failed, from the pipeline's output or the person's report: the stack (CloudFormation, which CDK and SAM deploy through), the container service (ECS), the function (Lambda), the deployment controller (CodeDeploy), or the running code's calls to AWS. A pipeline that failed before it called AWS — a build, a test, a lint — is not this skill's.

Record the account alias or environment name, the Region and the time window. Not the account ID: the report is an exit too.

## 2. Read the first failure event

`references/failure-signatures.md` has, per layer, where AWS records the failure and the signatures that recur, each with the AWS page it comes from. Open the section for the layer from step 1.

- **Stack:** read the stack events and find the earliest event whose status is a failure; its status reason is the cause, and everything after it is the rollback.
- **ECS:** read the stopped task's stop code and stopped reason, and each container's reason. Stopped tasks stay visible in the console for about an hour, so read them with the CLI if the window has passed.
- **Lambda:** decide whether the failure is in deployment (updating code or configuration) or invocation (running it), and read that page's signatures.
- **CodeDeploy:** read the deployment's failed lifecycle event and its log.

If no event explains the failure, widen to CloudTrail: event history holds 90 days of management events per Region, and is where a call that was denied or that changed a resource out of band appears.

## 3. If the cause is access denied, read the message

An access-denied message names the principal, the action, often the resource, and the type of policy that denied — explicit or implicit, and which of SCP, RCP, permissions boundary, session, resource-based, trust or identity-based policy. `docs/identity-and-access.md` has the anatomy and the evaluation logic.

The type decides where to look: an identity-based or implicit deny means the role lacks the grant; a resource-based one means the bucket, key or queue policy; a boundary, SCP or RCP means a guardrail the workload's owner may not control. Test the fix against the identity, boundary, SCP and resource policies with the IAM policy simulator; it does not evaluate RCPs, so a suspected RCP is a question to the account's owner.

The fix is the narrowest grant that lets the failing call through, under `rules/least-privilege.md`. Widening to a wildcard to make the error go away is the failure this rule exists for.

## 4. If the cause is the network, prove it

A task that cannot pull its image, a function that times out calling a service, a health check that never passes: check the route from the subnet (NAT or an endpoint), the security groups on both ends, and, when it is not obvious, the VPC Flow Logs for the interface. `docs/networking.md` has the paths a private subnet uses.

## 5. Name the cause and the fix

State: the layer, the first failure, the cause in one sentence, the evidence (the event, the stop reason or the message type — not its identifiers), and the smallest change that fixes it, as an edit to the infrastructure code or configuration. If a stack is stuck in a rollback-failed state, say so and name AWS's documented path (continue the rollback after fixing the cause, skipping a resource only as a last resort and knowing it leaves that resource inconsistent with the template); that operation is the owner's to run.

## 6. Report without exporting the account

The diagnosis goes into an issue, a pull request or a message to a person. It carries the environment name, the Region, the service and resource type, the action and the policy type — and no account ID, ARN, role or resource name beyond the project's own logical names, and no policy document (`rules/exposure.md`). Paste an error only after replacing those with placeholders.

## When this skill does not apply

**Designing the fix as a new architecture.** If the cause is that a service was the wrong choice — a Lambda that needs more than fifteen minutes — the diagnosis says so and the redesign is `skills/designing-on-aws/SKILL.md`.

**A defect in the application's own logic.** A function that runs and returns the wrong answer is the language plugin's diagnosis; this skill stops when AWS did what it was asked.

**An incident in production.** Restoring service is the on-call procedure's; this skill finds the cause of a failed deployment, and may be used after the incident to explain it.

**Changing anything.** Rolling back, redeploying, editing a policy or skipping a resource is the owner's action through the pipeline.
