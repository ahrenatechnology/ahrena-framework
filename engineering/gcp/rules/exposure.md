---
id: exposure
type: rule
clade: engineering
subclade: gcp
title: No Google Cloud Detail in an Application's Output
statement: No IAM policy, binding, service account, project or org id, resource name, network layout or Google Cloud error reaches an output or an error.
enforcement: judgment
references:
  - docs/exposure.md
---

# No Google Cloud Detail in an Application's Output

This is the Google Cloud form of the framework's exposure rule, [`layer-exposure.md`](../../security/rules/layer-exposure.md): nothing sensitive leaves the layer that owns it, and what a layer emits is an allowlist of named fields. [`docs/exposure.md`](../docs/exposure.md) lists what a Google Cloud error and identifier carry, cites the page behind each, and gives the shape of the translation.

An **exit** here is a response body or header, an error message returned to a caller, standard output or error, a log line that leaves the project's own logging (to a client, a third party, a ticket, a pull-request comment), a trace or metric attribute, a CLI or tool result, and an infrastructure plan, output or pipeline log.

## Conditions

1. **No Google Cloud error reaches a caller as it came.** A handler, job or tool that catches an exception or error from a Google Cloud client library, or an HTTP error from a Google API, does not return, re-raise across the boundary, serialise or interpolate its message, its details, its `ErrorInfo` metadata or its stack trace into what the caller receives. It returns the application's own error: a code from the application's contract, a generic message, and a correlation identifier. Decided by a reviewer, on every catch of a Google Cloud error and every place such an error can propagate uncaught to a response.

2. **No access policy, binding or identity in an exit.** No exit carries an allow or deny policy, a role binding, an IAM Condition, a service account email, or a workload identity pool, provider or principal set. Decided by a reviewer.

3. **No account-level identifier or resource path in an exit.** No exit carries an organization ID, folder ID, project ID or number, billing account ID, or a full or relative resource name (a secret, a key, a bucket and object, a service, a Cloud SQL connection name), unless the field is part of the application's documented contract with that caller, as the project ID is in a tool built for the project's own operators. Decided by a reviewer.

4. **No network layout in an exit.** No exit carries a VPC, subnet or range, an internal IP address or hostname, a firewall rule or a VPC Service Controls perimeter. Decided by a reviewer.

5. **The detail goes to an internal log, by named fields, and stops short of policy.** What condition 1 keeps from the caller is logged inside the project, to Cloud Logging, as named fields taken from the error (its type, `reason`, `domain` and status code) with the correlation identifier. Never the whole error object, its message text, the request or the response; never a secret; and never an access policy, a role binding or a service account email, which no diagnosis needs and which Policy Troubleshooter and the audit logs already hold for those allowed to see them. Decided by a reviewer, with `ahrena-engineering-security:skills/reviewing-sensitive-data/SKILL.md` for the fields themselves.

## Where this stops

**A judgment rule, because the detail is a value and not a call.** Whether `str(err)` reaches a response depends on where the string flows, which a pattern over one line cannot decide. The vendor-agnostic rule, [`layer-exposure.md`](../../security/rules/layer-exposure.md), carries the detector for the cases a line can show, such as a caught error interpolated into a response; this rule adds the Google Cloud classes for the reviewer and does not ship a second detector.

**The project's own logging is an exit for policy, and not for the error's fields.** Cloud Logging and Error Reporting inside the project are where the error's named fields belong, under IAM; condition 5 still keeps policies, bindings and service account emails out of them. Their content becomes an exit of every class when it is copied outward.

**An operator tool that is about the infrastructure** may show project IDs and resource names to its operators, because that is its contract. It still never shows a policy, a credential or the provider's raw error to anyone outside the project's own administrators.

**What makes the error happen** (the missing permission, the wrong scope) is [`rules/identity-and-access.md`](identity-and-access.md). This rule is about what the caller is told when it happens.
