---
id: layer-exposure
type: rule
clade: engineering
subclade: security
title: Nothing sensitive leaves the layer that owns it
statement: Nothing sensitive leaves the layer that owns it - an exit emits named fields, never a whole object, configuration, error or upstream response.
enforcement: judgment
references:
  - docs/layer-exposure.md
---

# Nothing sensitive leaves the layer that owns it

What a layer emits is a list of named fields. Emitting a whole object, a whole configuration, a whole error or a whole response received from a dependency is the violation, whether or not it holds something sensitive today. The rule holds at write time and in every layer: domain, use case, persistence, API, interface, data pipeline, infrastructure and the build itself. [`docs/layer-exposure.md`](../docs/layer-exposure.md) carries the incident behind it and the argument.

## What is sensitive

The list is closed, so a reader can check a field against it.

1. **Credentials and tokens:** a password, an API key, an access, refresh or session token, a private or signing key, a connection string that carries a credential.
2. **Personal and payment data:** anything that identifies a person or can be tied to one, and card, account and payment details.
3. **Authorization and infrastructure configuration:** an access policy, a role, an identifier that locates an account or a resource, network topology, deployment state, an internal hostname or path, a stack trace, a query.

The third class reads, item by item: a policy document, a permissions boundary or a role binding; a role's name or identifier; a cloud account, project or subscription identifier, a resource name or ARN, a secret or parameter path, a bucket, queue or table name; addresses, ranges, subnets, security groups and routes; a plan, a state, an output, an environment variable, the version of an internal component; a host or service name that resolves only inside the network, a filesystem path; the frames of a stack; the text of a database query.

## What an exit is

Standard output and standard error; a log; a trace or metric attribute; an error message; an API response; the result of a CLI or a tool; a pipeline log; an infrastructure plan or output; a build artefact; a comment on a pull request. A datum crosses an exit when a reader who is not the layer's owner can read it there.

## Conditions

1. **No caught error reaches an exit whole.** Not the error value, its text, its message or its stack. Decided by [`hooks/check-exposure.py`](../hooks/check-exposure.py) over the lines `--changed` scopes it to.
2. **No dependency's response reaches an exit whole.** Not the body, text, content or decoded JSON of what an upstream call returned. Decided by [`hooks/check-exposure.py`](../hooks/check-exposure.py).
3. **No access policy and no whole configuration reaches an exit.** Not a policy document, the whole process environment or an object's whole attribute map, and no infrastructure output whose value is a policy or a whole resource or module. Decided by [`hooks/check-exposure.py`](../hooks/check-exposure.py).
4. **Every other exit the change writes emits a list of named fields, and no field is in the sensitive list unless its reader needs it and may read it.** A whole record, request or object handed to a logger or a serialiser; a resource identifier or an internal hostname in an error a caller sees; a plan or state printed to a pipeline log. Decided by a reviewer, with `DAT-1` of `reviewing-sensitive-data` and `ACC-8` of `reviewing-access`.

**The correction at a boundary is the same in every layer.** The caller receives a generic error and a correlation identifier. The detail goes to the layer's internal log as named fields: the error's code, the operation, the provider's request identifier, the correlation identifier, and no secret.

## Where this stops

**The hook decides three shapes and is written to miss rather than misfire.** It recognises an exit by its call or its shape and a caught error by its binding, so an error renamed into a plain variable, a logger it does not know, or a whole object of any other kind passes it. A pass from the hook is not a pass from the rule: condition 4 is the larger half.

**A named field the reader needs is not a leak.** A role identifier handed from the infrastructure layer to the application as one configuration input, an output marked sensitive and read by the one module that needs it, an error code returned to a caller: each is a field, named, crossing to a reader that needs it. The rule forbids the whole thing and the field nobody asked for, not the field.

**A recorded decision is exempt.** A line carrying an `ADR-N` pointer records why its reader is inside the layer — a command-line tool that reports its own failure to the operator who ran it, on input that operator supplied. The hook skips that line, and a reviewer reads the record.

**The logger's exception facility is read, not refused.** `logger.exception` and `exc_info` in Python write the stack trace to the owning layer's log without the line naming the error, so the hook does not see them. They are permitted only into a log whose readers are the layer's owners, and a reviewer checks where that log goes; a pipeline log or a third party's sink is an exit.

**Detail behind a development switch** that cannot be turned on in production is outside the rule, as `ACC-8` already says.

**A test is not an exit.** A test that asserts on an error's text reads it where it was raised. A fixture that reproduces a violation on purpose is stored so that nothing gates it as source.

**What the rule does not decide.** Who may reach an entry point is `reviewing-access`. Whether a recipient may receive a category of data at all is the organisation's question, in `DAT-5`. How each language holds the rule — a redacting representation, a logger given named fields, an error translated before it crosses — is each language plugin's; the infrastructure disciplines are the Terraform and cloud plugins'.
