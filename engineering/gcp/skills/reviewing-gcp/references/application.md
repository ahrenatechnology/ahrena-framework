# Google Cloud in application code

Opened by step 2 of `SKILL.md` when the `gcp-application` route fired: a changed source file that calls a Google Cloud client library or handles its errors. Each condition gives the state, how it is detected, what exempts it, and the correction. The rule behind them is `rules/exposure.md`; `docs/exposure.md` says what a Google Cloud error and identifier carry. Step 1 of `SKILL.md` ran the security plugin's `hooks/check-exposure.py`, which decides the line-level shapes of the vendor-agnostic rule (a caught error or an upstream response reaching an exit whole); what it reported is already a finding, and these conditions read the Google Cloud classes it does not name.

### GCA-1 A Google Cloud error returned to the caller

- **State:** a handler, job or tool catches an exception from a Google Cloud client library (`google.api_core.exceptions.*`, `googleapi.Error`, an `ApiError` from `@google-cloud/*`, a gRPC `status` from a Google API) and puts its message, `details`, `ErrorInfo` metadata or stack trace into the response, the returned error, a CLI result, or an error it re-raises across the boundary; or lets such an error propagate uncaught to a framework that renders it.
- **Detect:** every `except`/`catch`/`if err != nil` around a call into a Google Cloud client, and what reaches the response from it: `str(e)`, `e.message`, `err.Error()`, `fmt.Errorf("...: %w", err)` returned to an HTTP layer, `JSON.stringify(err)`, a default error handler that prints the exception.
- **Exempt:** an error mapped to the application's own code and generic message before it leaves, with the detail logged internally.
- **Correct:** at the boundary, map the error to the application's contract (refused, not found, unavailable and retryable), return a generic message with a correlation identifier, and log the detail as named fields with that identifier. Rule: `rules/exposure.md` condition 1. **Severity:** blocking when the line is in the diff.

### GCA-2 An access policy, binding or identity in an exit

- **State:** an exit (response, returned error, CLI or tool result, a log line that leaves the project) carries an IAM policy, a role binding, an IAM Condition, a service account email, or a workload identity pool or provider.
- **Detect:** any value read from the IAM, Resource Manager or Policy APIs, or from the metadata server's service account endpoint, and where it flows.
- **Exempt:** an operator tool whose documented contract is to show IAM to the project's own administrators.
- **Correct:** emit only the named fields the caller's contract needs. Rule: `rules/exposure.md` condition 2.

### GCA-3 A project, organization or resource path in an exit

- **State:** an exit carries an organization, folder or billing account ID, a project ID or number, or a full or relative resource name (`projects/.../secrets/...`, a bucket and object path, a Cloud SQL connection name), including one assembled into a message such as "could not read projects/acme-prod/secrets/stripe-key".
- **Detect:** the configuration values that hold these (`GOOGLE_CLOUD_PROJECT`, a connection name, a bucket name) and every message or response that interpolates them.
- **Exempt:** a field that is part of the application's documented contract with that caller.
- **Correct:** name the failure in the caller's terms ("the payment provider is unavailable"), and log the resource name internally. Rule: `rules/exposure.md` condition 3.

### GCA-4 Network layout in an exit

- **State:** an internal IP or hostname, a VPC or subnet name, a firewall rule or a VPC Service Controls perimeter name in an exit, often from a connection error's text.
- **Detect:** errors from database drivers, HTTP clients and the Cloud SQL connector reaching a response.
- **Exempt:** none outside an operator tool.
- **Correct:** as GCA-1. Rule: `rules/exposure.md` condition 4.

### GCA-5 A whole error or object logged

- **State:** a log call handed a whole client-library exception, request, response or resource object rather than named fields, or a log line holding a secret read from Secret Manager.
- **Detect:** each log call near a Google Cloud call.
- **Exempt:** a log call into Cloud Logging inside the project that passes named fields taken from the error (its type, `reason`, `domain`, status code) with the correlation identifier.
- **Correct:** log named fields with the correlation identifier; never the message text, the secret's payload, a policy, a binding or a service account email. Rule: `rules/exposure.md` condition 5, with `ahrena-engineering-security:skills/reviewing-sensitive-data/SKILL.md` for the fields.

### GCA-6 A credential or key file in the application

- **State:** the code loads a service account key file (`from_service_account_file`, `GOOGLE_APPLICATION_CREDENTIALS` pointing at a key shipped with the code) where it runs on Google Cloud or can use federation; or reads a secret from an environment variable the change sets in plain text.
- **Detect:** credential construction in the change.
- **Exempt:** Application Default Credentials, which resolve to the attached service account; a key the change names with the reason no alternative serves.
- **Correct:** use Application Default Credentials and the attached service account; read secrets from Secret Manager. Rules: `rules/identity-and-access.md` condition 4, `rules/data-protection.md` condition 4.

### GCA-7 A secret or project fixed in the code

- **State:** a Secret Manager reference to `versions/latest` in code that runs in production, or a project ID, project number or full resource name written as a literal in source.
- **Detect:** string literals beginning `projects/`, `//`-prefixed resource names, and values of the project-holding settings set in code rather than read from configuration.
- **Exempt:** a test fixture with an invented project; a version alias the installation records as its rotation mechanism.
- **Correct:** pin the secret version and read it, and the project, from configuration. Rules: `rules/data-protection.md` condition 4, `rules/exposure.md` condition 3 (a literal resource name is one interpolation away from an exit).
