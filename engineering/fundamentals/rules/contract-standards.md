---
id: contract-standards
type: rule
clade: engineering
subclade: architecture
title: Published contracts follow the open standards
statement: An event is CloudEvents 1.0 with a versioned data schema, an HTTP API is OpenAPI first, a gRPC API is Protobuf first, and a break ships as a new version.
enforcement: judgment
references:
  - docs/contract-standards.md
  - docs/contract-first.md
---

# Published contracts follow the open standards

Ten conditions in three groups, EVT-1 and EVT-2, API-1 to API-4 and RPC-1 to RPC-4 of the PR quality rubric (#323). They name the standard each surface follows; `rules/contract-first.md` owns the direction (the contract is authored, the code derived from it) and this rule does not restate it. `docs/contract-standards.md` cites the specification behind each group, with the text read on 14 November 2026, and says which thresholds are the specification's and which are declared maintainer policy (#34).

None of these conditions adds an abstraction, so the abstraction trigger of `rules/yagni.md` does not gate them. Each is decided by a job the consuming project runs; the detectors are tracked in the detectors sub-issue of #323.

## Conditions

1. **EVT-1. Every published event is a CloudEvents 1.0 event carrying `specversion`, `id`, `source`, `type`, `time` and `subject`, where `subject` is the identity of the aggregate root.** The threshold is 100% of published events. The first four are required by the specification; `time` and `subject` are optional there and required here as policy, because `rules/aggregates.md` requires the root identity and the time on every domain event. Condition 4 of `rules/contract-first.md` already requires the four; this one adds the two. Decided by validating a captured event against the CloudEvents JSON schema inside the contract test, which also asserts `time` and `subject` are present and `subject` equals the root's identity.

2. **EVT-2. Every event `type` has a versioned schema, named by `dataschema`, and a test validates the event's `data` against it.** The threshold is 100% of types. A change to the schema that is not additive ships under a new `type` or a new schema version. Decided by the set difference between the types the project publishes and the schemas its tests validate against.

3. **API-1. Every HTTP API is described by an OpenAPI document, version 3.1 or later.** The threshold is 100% of routes. Decided by the existence of the document for each served route; the direction (authored first) is condition 1 of `rules/contract-first.md`.

4. **API-2. A route served and a route declared match in both directions.** The threshold is 0 divergences: no served route missing from the document and no declared operation unserved. Decided by a job that compares the router's route table with the document's paths and methods.

5. **API-3. The document passes the project's lint ruleset with 0 errors, and a test validates each response against it.** The ruleset extends `spectral:oas`; the test validates the status code, the headers and the body of each declared response. Decided by the Spectral run and the response-validating test.

6. **API-4. A change that breaks the HTTP contract is detected in the pull request and passes only with a new version.** The threshold is 0 breaking changes without a version. Decided by a breaking-change diff of the base document against the head, `oasdiff breaking` or equivalent.

7. **RPC-1. Every gRPC API is described in a `.proto` file of proto3 or an edition, and the code is generated from it.** The threshold is 100% of services. Decided by the build configuration: the generator's inputs are `.proto` files and its outputs are not committed by hand.

8. **RPC-2. Every `.proto` file passes `buf lint` with 0 errors.** The project's lint configuration uses the standard category, which requires a versioned package such as `acme.orders.v1`, a request and a response message named for the RPC and unique to it, and an `_UNSPECIFIED` zero value on every enum. The names follow the Protobuf style guide: `TitleCase` messages, services and methods, `snake_case` fields. Decided by `buf lint`.

9. **RPC-3. A change that breaks the `.proto` contract is detected in the pull request, and a removed field's number is `reserved` and never reused.** The threshold is 0 breaking changes without a new version and 0 reused numbers. Decided by `buf breaking` against the base commit, and by the compiler, which rejects a reserved number.

10. **RPC-4. A gRPC error leaves with a gRPC status code and standard details in `google.rpc.Status`, and never with a stack trace.** The threshold is 100% of error paths. The `message` is developer-facing and carries no stack, in line with condition 2 of `rules/result-errors.md`. Decided by a test per RPC that forces an unexpected failure and inspects the status.

## Where this stops

**EVT-1 does not reach an event that never leaves the process.** An in-memory domain event raised and consumed in one deployment unit may be a plain object; the condition applies when the event is published to another consumer, and `rules/aggregates.md` still requires the root and the time.

**EVT-2 does not freeze a schema.** An additive change is compatible and ships in the same version; the condition is that a change is visible, not that it is forbidden.

**API-1 does not require a document for an internal route.** A route no one outside the deployment unit calls is not a published surface; the line is the one `docs/contract-first.md` draws.

**API-1 names 3.1 or later on purpose.** The catalog fixed 3.1; the specification has moved on, so later versions satisfy it, provided the project's lint and diff tools support the version it picks. Which tools do is stated in the doc and re-read when the project upgrades.

**API-4 and RPC-3 do not classify a break by themselves.** The tools apply the standard breaking set; a reviewer decides the remainder, as `skills/detecting-contract-breaks` in the quality plugin does for any surface.

**RPC-2 does not rewrite a vendored `.proto`.** A file the project imports from a third party is excluded by path; the lint covers files the project wrote.

**RPC-4 does not forbid detail.** Standard details such as a bad-request field list are the point; only the stack and the raw upstream error are forbidden.

**These conditions are judgment, and no detector ships here.** Each needs the project's router, schema directory or proto module, which this plugin cannot know.
