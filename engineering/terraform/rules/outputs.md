---
id: outputs
type: rule
clade: engineering
subclade: terraform
title: An output is an allowlist, and nothing sensitive leaves it unmarked
statement: A Terraform output that can carry a secret, a policy or a connection string is sensitive; a root output is a named attribute a known consumer reads.
enforcement: judgment
references:
  - docs/modules.md
  - docs/state.md
  - docs/toolchain.md
---

# An output is an allowlist, and nothing sensitive leaves it unmarked

This is the Terraform form of the exposure rule, [`layer-exposure.md`](../../security/rules/layer-exposure.md) (issue #294): nothing sensitive leaves the layer that owns it, and what a layer emits is an allowlist of named fields. For a Terraform configuration the layer is the root module and its exits are its outputs, the plan and apply log, `terraform output`, and whatever reads its state. The sensitive classes are the ones #294 lists: credentials and tokens, personal data, and authorization and infrastructure configuration, which means an access policy, a role, an identifier that locates an account or a resource, network topology and deployment state.

Two of HashiCorp's statements set the stakes. A `sensitive` output is redacted in plan and apply, and is still stored in state and printed in plain text by `terraform output -json` and `-raw` ([Output block](https://developer.hashicorp.com/terraform/language/block/output)). And `terraform show -json` prints sensitive values from state in plain text ([`terraform show`](https://developer.hashicorp.com/terraform/cli/commands/show)); the JSON format marks which values are sensitive in a separate structure and does not mask them ([JSON output format](https://developer.hashicorp.com/terraform/internals/json-format)). So `sensitive` keeps a value out of the log a person reads over a shoulder, and an output is still a door into whatever can read it. The door is opened on purpose or not at all.

## Conditions

1. **An output whose name or value can carry a secret, a policy or a connection string is marked `sensitive = true`.** Decided by `hooks/check-terraform.py`, in root and child modules alike, because a child's unmarked output is how a secret reaches the root's. The hook reports an output that is not marked `sensitive` or `ephemeral` when its name names a secret, a `policy`, a `kubeconfig` or a `dsn`; when its value holds a URL with credentials in it (`postgres://user:pass@host`); when it references an attribute so named (`aws_iam_policy.x.policy`, `module.db.password`), an attribute of a resource whose type is so named (`random_password.db.result`, `data.<type>_policy_document.x.json`), or a variable declared sensitive. An output named for what locates something (`_id`, `_arn`, `_name`) is left to condition 4. An ephemeral output (child modules only, Terraform 1.10 and later) never reaches state and is the stronger choice where the caller reads the value only during the run ([Output block](https://developer.hashicorp.com/terraform/language/block/output)).

2. **A root module exports no whole object.** Decided by `hooks/check-terraform.py`. `value = aws_db_instance.main` or `value = module.network` exports every attribute that object has today and every one a provider upgrade adds tomorrow: a password, a connection string, a policy document. The allowlist is the named attributes a consumer reads, `value = aws_db_instance.main.address`. A child module returning a whole object to its caller is composition and passes; the root is where values leave the configuration.

3. **No script or pipeline prints outputs or a plan as JSON to its log.** Decided by `hooks/check-terraform.py`, which reports `terraform output -json`, `terraform output -raw` and `terraform show -json` (and `tofu` alike) on a line that neither redirects to a file nor captures into a variable. Each of the three prints sensitive values in plain text, for the reasons above; a pipeline log is an exit that more people read than the state. `docs/toolchain.md` says what the plan log of a pipeline may show.

4. **An output that describes access or topology is exported only when a named consumer reads it.** Decided by review. A role or policy identifier, an account id, a subnet layout, an internal hostname, a security rule: each is the reconnaissance #294 began from, and an output that nothing reads is exposure with no purpose. The reviewer asks which configuration, pipeline step or person reads it, and the answer is a name. Where the consumer is another configuration, HashiCorp recommends publishing the value to a separate store rather than letting the consumer read it through `terraform_remote_state`, because that data source needs access to "the entire state snapshot", sensitive values included ([`terraform_remote_state`](https://developer.hashicorp.com/terraform/language/state/remote-state-data)).

5. **No error message carries a sensitive value or a whole object.** Decided by review. A `validation`, `precondition`, `postcondition` or `check` message, and a test's assertion message, go to the plan log; Terraform evaluates variable validations, preconditions and postconditions while it plans ([Validate your infrastructure](https://developer.hashicorp.com/terraform/language/validate)). The message names the rule that failed. Interpolating the value that failed it is an exit for that value.

## Where this stops

**Condition 1 reads names and shapes, not values.** An output named `endpoint` whose value happens to embed a token from an unmarked local passes. A value derived from a sensitive variable through a local is followed only one step: the hook sees `var.x` in the output, not `local.y` that was built from it. Terraform's own propagation covers part of the rest, because it treats any expression that references a sensitive variable or output as sensitive itself ([Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)). What it cannot cover is a value it has no reason to think is sensitive, such as a policy document or an endpoint with credentials in it, and that is most of what this condition is for.

**Condition 2 reads the expression's shape.** `value = { for k, v in aws_x.y : k => v }` exports the same whole objects through a comprehension and passes. So does a `jsonencode()` of a resource. Both are condition 4 for the reviewer.

**Condition 3 accepts a pipe.** `terraform output -json | jq -r .vpc_id` prints one non-sensitive field and is the allowlist done right; `| tee` prints everything. The hook cannot tell them apart and leaves both to review.

**`sensitive` is not secrecy.** It is redaction in one place. A value that must not reach state is ephemeral or write-only, and `rules/secrets.md` and `docs/state.md` say when. This rule governs what the configuration emits; it does not make state safe to share.

**This rule declares judgment because conditions 4 and 5 need a reader.** Three of five conditions have a script. The fourth is the exposure rule's core, the allowlist with a reason for each entry, and a hook that checked shapes while dropping the question "who reads this" would ship the half of #294 that was never the incident.
