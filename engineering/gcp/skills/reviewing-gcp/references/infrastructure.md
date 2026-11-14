# Google Cloud infrastructure

Opened by step 2 of `SKILL.md` when the `gcp-infrastructure` route fired: a change that declares or grants something on Google Cloud, in Terraform, a `gcloud` script, a Cloud Build or Cloud Run file, or a Config Connector manifest. Each condition gives the state, how it is detected, what exempts it, and the correction. `hooks/check-gcp-grants.py` has already reported the literal forms of GCI-1, GCI-3 and GCI-4 on the changed files; a grant it let through because of a `gcp-grant-allowed:` comment is read here for whether the reason holds. The detector named after each is the vendor's, which reports the same state on a deployed project; the reviewer is the one that reads it in the change.

### GCI-1 A basic role

- **State:** a binding of `roles/owner`, `roles/editor` or `roles/viewer`; or a workload configured to run as a default service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`, or no service account set where the default applies).
- **Detect:** every IAM binding in the change; every compute resource's service account field.
- **Exempt:** a sandbox project with no client data, said so in the change.
- **Correct:** the predefined role whose permissions the principal uses; a dedicated service account per workload. Rule: `rules/identity-and-access.md` conditions 1 and 3. Vendor detector: `PRIMITIVE_ROLES_USED`, `ADMIN_SERVICE_ACCOUNT`, `DEFAULT_SERVICE_ACCOUNT_USED`.

### GCI-2 A grant wider than the resource

- **State:** a role granted at project, folder or organization level for a principal that acts on one resource; `roles/iam.serviceAccountUser` or `roles/iam.serviceAccountTokenCreator` granted on the project.
- **Detect:** the resource each binding is attached to (a `google_project_iam_*` where a `google_secret_manager_secret_iam_*`, `google_storage_bucket_iam_*` or `google_service_account_iam_*` would serve).
- **Exempt:** a principal that acts on every resource of that kind in the project, said so.
- **Correct:** bind on the resource. Rule: `rules/identity-and-access.md` condition 2. Vendor detector: IAM role recommender, `OVER_PRIVILEGED_SERVICE_ACCOUNT_USER`.

### GCI-3 A service account key

- **State:** a `google_service_account_key` resource, `gcloud iam service-accounts keys create`, a key uploaded, or a key placed in a CI secret for a platform that supports Workload Identity Federation.
- **Detect:** key resources and commands; CI configuration that authenticates to Google Cloud.
- **Exempt:** a key the change names with the reason no attached identity, Workload Identity Federation or impersonation serves.
- **Correct:** attach the service account; for CI or another cloud, Workload Identity Federation; for a person, impersonation. Rule: `rules/identity-and-access.md` condition 4. Vendor detector: `iam.disableServiceAccountKeyCreation`, `USER_MANAGED_SERVICE_ACCOUNT_KEY`.

### GCI-4 Something public

- **State:** a binding to `allUsers` or `allAuthenticatedUsers`; a bucket without uniform bucket-level access or with public access prevention set to `inherited` where nothing enforces it above; Cloud Run with `--allow-unauthenticated` or the invoker check disabled; a BigQuery dataset readable by everyone.
- **Detect:** the principals of every binding; bucket, dataset and Cloud Run settings.
- **Exempt:** content meant for anyone on the internet, said so in the change, and served through the load balancer where it is HTTP.
- **Correct:** grant to the callers that need it; `uniform_bucket_level_access = true`, `public_access_prevention = "enforced"`. Rule: `rules/identity-and-access.md` condition 5. Vendor detector: `storage.publicAccessPrevention`, `PUBLIC_BUCKET_ACL`, `PUBLIC_DATASET`.

### GCI-5 An open network door

- **State:** a firewall rule allowing `0.0.0.0/0` to anything but the load balancer's ports; SSH or RDP open to the internet; a VM with an external IP; a Cloud SQL instance with a public IP or `0.0.0.0/0` authorized; Cloud Run ingress `all` for a service that only the load balancer or internal callers need; the default network used.
- **Detect:** firewall rules, network interfaces, Cloud SQL `ip_configuration`, Cloud Run `ingress`.
- **Exempt:** the external load balancer's own forwarding.
- **Correct:** IAP TCP forwarding for admin access, Cloud NAT for egress, private IP for Cloud SQL, ingress `internal-and-cloud-load-balancing` or `internal`, a custom-mode network. Doc: `docs/networking.md`. Vendor detector: `OPEN_FIREWALL`, `OPEN_SSH_PORT`, `OPEN_RDP_PORT`, `PUBLIC_IP_ADDRESS`, `SQL_PUBLIC_IP`, `DEFAULT_NETWORK`.

### GCI-6 An unencrypted path the platform leaves to the customer

- **State:** a Cloud SQL instance whose SSL mode allows unencrypted connections while clients connect without the Auth Proxy or a connector; a VM on an external IP serving plaintext; a load-balancer backend carrying client data over HTTP.
- **Detect:** Cloud SQL `ssl_mode`, how clients connect, backend protocols.
- **Exempt:** a connection through the Cloud SQL Auth Proxy or a language connector.
- **Correct:** `ENCRYPTED_ONLY` or the connector; TLS to the backend. Rule: `rules/data-protection.md` conditions 1 and 2. Vendor detector: `SSL_NOT_ENFORCED`.

### GCI-7 A key without rotation, a secret in the wrong place

- **State:** a Cloud KMS symmetric key with no rotation period; a credential in a Terraform variable default, a `.tfvars`, a manifest, a build file, or a plain environment variable; `roles/secretmanager.secretAccessor` on the project; `latest` referenced in production.
- **Detect:** KMS key resources; every place a credential-shaped value or name appears.
- **Exempt:** a secret reference that the platform resolves from Secret Manager at run time.
- **Correct:** set `rotation_period`; move the value to Secret Manager and grant access on the secret; pin a version. Rule: `rules/data-protection.md` conditions 3 and 4. Vendor detector: `KMS_KEY_NOT_ROTATED`.

### GCI-8 Unattributable spend

- **State:** a billable resource with no owner label; a new project, or the first billable resource of a project, with no budget covering it.
- **Detect:** `labels` on each new resource and inherited defaults; budget resources.
- **Exempt:** a resource that does not take labels.
- **Correct:** add the installation's owner label; add or name the budget and its alert recipient. Rule: `rules/cost-attribution.md`.

### GCI-9 Infrastructure detail printed

- **State:** a Terraform output, a script's `echo`, or a pipeline step that prints a policy, a key, a secret value, or a whole resource.
- **Detect:** `output` blocks and pipeline logging in the change.
- **Exempt:** an output that holds only the names a downstream step consumes, marked sensitive where it carries a credential.
- **Correct:** output the named fields needed; never a key or a policy. Rule: `rules/exposure.md`; the vendor-neutral side is `ahrena-engineering-terraform` (issue 295).
