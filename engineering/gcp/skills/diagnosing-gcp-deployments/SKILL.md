---
name: diagnosing-gcp-deployments
description: Use when a deployment to Google Cloud fails or a just-deployed service misbehaves - a Cloud Run revision that is not ready, a build or Infrastructure Manager run that fails, a pod in ImagePullBackOff or CrashLoopBackOff, a PERMISSION_DENIED, SERVICE_DISABLED, quota or organization-policy error. Finds the failing step, matches its signature, confirms the cause with the vendor's own tool before changing anything, and proposes the smallest fix that keeps to this plugin's rules.
type: skill
clade: engineering
subclade: gcp
references:
  - rules/identity-and-access.md
  - rules/exposure.md
  - docs/identity-and-access.md
  - docs/networking.md
---

# Diagnosing a Google Cloud deployment

The output is a diagnosis: the failing step, the evidence, the confirmed cause, and the fix, with what was ruled out. A fix that widens a grant to make the error go away is not a fix; step 5 says why.

## 1. Find the step that failed

A deployment is a chain: build, push, provision, deploy, start, serve. Find the first link that failed, from the pipeline's own output or the console, before reading any log. Record the resource, the project, the region, the revision or build ID, and the time.

## 2. Collect the evidence for that step

Read the logs for that resource around that time, filtered by resource type and `severity>=ERROR`; for a change of state, read the Admin Activity audit log for who changed what. Record the exact error message and code.

The evidence holds project IDs, service accounts and resource names. It stays in the diagnosis for the people who operate the project; it does not go into a ticket, a pull-request comment or a message outside them (`rules/exposure.md`).

## 3. Match the signature

Open `references/failure-signatures.md` and find the entry whose signature matches the error. If none matches, say so and take the error to the page of the service that raised it; do not guess a cause from a resemblance.

## 4. Confirm before changing anything

Run the confirmation the entry names: Policy Troubleshooter for a permission, the violation analyzer for a perimeter, `gcloud org-policies describe` for a constraint, the container contract for a start failure, quota usage for an exhausted quota. For a permission that was granted moments ago, wait out the propagation the entry states before concluding it is missing. A cause that the confirmation does not support is ruled out and recorded as such.

## 5. Propose the smallest fix within the rules

The fix is the narrowest change that removes the confirmed cause: the one permission on the one resource, the service account the deployer may act as, the port the container listens on. Never a basic role, a project-wide grant, a service account key, a public binding or an organization-policy override to get past an error: each is a violation of `rules/identity-and-access.md`, and an override is the organization owner's decision. Where the narrow fix needs a policy change, preview it with Policy Simulator or an organization policy in dry run first.

Hand back the failing step, the evidence (with identifiers kept to the operators' channel), the confirmed cause, what was ruled out, and the fix with the rule it keeps.

## When this skill does not apply

**A defect in the application's logic** that would fail the same way anywhere: that is the language plugin's diagnosis.

**A design question** (is Cloud Run the right runtime for this): `designing-on-gcp`.

**A Terraform plan or state problem** that is not about what Google Cloud refused: `ahrena-engineering-terraform` (issue 295).

**An incident in production with users affected.** Restore service first by the installation's own runbook; this skill is for finding the cause, and it can follow.
