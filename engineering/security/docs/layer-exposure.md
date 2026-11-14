---
id: layer-exposure
type: doc
clade: engineering
subclade: security
title: Why nothing sensitive leaves its layer
summary: The incident behind rules/layer-exposure.md, why the condition is deny by default, why authorization and infrastructure configuration are sensitive, why a dependency's error is the case that recurs, and how the review route was fixed so the condition is reached.
references:
  - rules/layer-exposure.md
---

# Why nothing sensitive leaves its layer

This is the companion of [`rules/layer-exposure.md`](../rules/layer-exposure.md). The rule states the conditions; this says why they are these, and what changed in the review so they are read.

## The incident

On 2026-11-12 a client's engineer, using a product built with the agency, received an HTTP 500 from an endpoint that stores a credential on a third party's behalf. The body was the cloud SDK's access-denied message, verbatim. From it the client read the cloud account, the role the service assumes, the action that was denied, the path under which the third party's credential is kept, and that a permissions boundary governs the role. They diagnosed the configuration from outside and said which permission to grant. No credential leaked; the same line would have returned whatever the error carried.

The handler did one thing: it caught the provider's error and put its text in the response. [`hooks/fixtures/upstream-error-passthrough.py.txt`](../hooks/fixtures/upstream-error-passthrough.py.txt) keeps it, with invented identifiers.

Two layers failed. The builder wrote the line because nothing it read said not to. The review passed it, with both the routed security disciplines and the security guardian, which is the graver failure and the one the rest of this document is about.

## Why deny by default

A rule that says "do not emit sensitive data" asks the author to know, at the line, what the object holds. An error's text is written by the dependency, not by the author, and it changes when the dependency changes. A record grows a field after the serialiser was written. A configuration gains a secret after the line that prints it was reviewed. In each case the line was correct when read and wrong later, and no review of the line catches the later.

Naming the fields inverts that. The line that emits `code` and `correlation_id` emits exactly those whatever the error becomes, and the review checks a list it can see. So the violation is the whole thing, whether or not it holds something sensitive today.

## Why configuration is sensitive

The sensitive classes the review carried stopped at personal data, payment data and credentials. An access policy, a role, an account identifier and a resource path are none of those, so a reviewer following the condition passed the incident's body. They are sensitive for a different reason: they are the map. A caller who knows the role, the action and the boundary knows what the service may do and what it may not, and an attacker starts from exactly that. A network layout, a plan, a state and an internal hostname are the same map at another layer. The closed list puts them beside credentials, so the reviewer's question is the same for all three classes.

## Why a dependency's error is the case that recurs

An error from a cloud SDK, a database driver or a third party's API is written for the developer of that dependency, and it is generous: the resource, the principal, the query, the host. It is the most detailed text a service ever holds about its own configuration, and it arrives at the one place, the error path, that is written last and reviewed least. Passing it through is the shortest code that compiles, which is why it recurs.

The correction is the same at every boundary: a generic error and a correlation identifier to the caller, the detail to the layer's own log as named fields. The correlation identifier is what keeps the generic error diagnosable: the on-call engineer who receives it from the caller finds the log entry, and the caller learns nothing.

## Why the review missed it, and what changed

The route table decides which disciplines a review loads, from the paths and the added lines of a change. Run on the incident's change, it loaded `reviewing-access` because a line named a tenant, and `reviewing-sensitive-data` because a line named the secrets service, and pointed each at those lines. Neither was pointed at the line that returned the error, and no route keyed on it. A variant of the same handler that named no tenant and no secret reached no security discipline at all beyond the credential sweep. The route was firing on vocabulary that happened to be nearby, not on the shape that was dangerous.

Inside the disciplines the conditions stopped short in the same way. `ACC-8` named "a stack trace or a query", and an upstream message is neither; `DAT-1` named personal data, payment data and credentials, and configuration is none.

Three things changed. Two routes, `error-exposure` for `reviewing-access` and `layer-exposure` for `reviewing-sensitive-data`, fire on the shape: a caught error, a dependency's response, a policy or a whole configuration on a line that writes to an exit. `ACC-8` names the pass-through and `DAT-1` names the configuration class, each citing the rule. And Janus applies the rule at the threshold before a layer opens, so the guardian reads the condition whether or not a route fired. The router's own tests run the incident's fixture through the shipped table, so a later edit to the table that loses the route fails there.

## Why a hook, and why it decides so little

Three of the four conditions have a shape a script can see on one added line: an exit call, and a caught error, an upstream response or a policy handed to it whole. The hook decides those, change-scoped, with no dependency, so a consumer runs what the repository runs. What it cannot see — whether a field it does not recognise is sensitive, whether a whole object of some other type is a record — is condition 4, and it stays a reviewer's. The hook is written to miss rather than misfire, the same trade the backstage-language hook makes, because a detector that cries wolf on every log line teaches the author to ignore it.

## Where this stops

This document argues the rule; it does not define it. The conditions, the sensitive list and the exits are in the rule. How each language holds it is in each language plugin, and the infrastructure disciplines are the Terraform and cloud plugins'.
