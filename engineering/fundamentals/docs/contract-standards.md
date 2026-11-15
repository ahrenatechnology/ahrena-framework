---
id: contract-standards
type: doc
clade: engineering
subclade: architecture
title: The open standards behind published contracts
summary: Which specification each of the event, HTTP and gRPC conditions cites, what its text actually says as read on 14 November 2026, and which thresholds are the specification's and which are maintainer policy.
references:
  - rules/contract-standards.md
  - rules/contract-first.md
  - docs/contract-first.md
---

# The open standards behind published contracts

This is the companion to [`rules/contract-standards.md`](../rules/contract-standards.md). Every standard the rule names is cited here to its primary text, read on 14 November 2026. A threshold is the specification's, or it is declared maintainer policy (#34), and the tables below say which.

## CloudEvents (EVT-1, EVT-2)

Source: CloudEvents specification, `cloudevents/spec`, `cloudevents/spec.md` (<https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md>).

- `id`, `source`, `specversion` and `type` are REQUIRED. `datacontenttype`, `dataschema`, `subject` and `time` are OPTIONAL.
- `subject` identifies the subject of the event in the context of the producer identified by `source`. Producers MUST ensure `source` plus `id` is unique per distinct event.
- The text read on `main` is headed 1.0.3-wip; the released line is 1.0. The rule says CloudEvents 1.0 and a project pins the exact release it validates against.

| Part | Threshold | Source |
|---|---|---|
| `specversion`, `id`, `source`, `type` present | 100% | the specification, REQUIRED |
| `time` and `subject` present, `subject` = root identity | 100% | maintainer policy: `rules/aggregates.md` already requires the root and time |
| `dataschema` and a validating test per `type` | 100% | maintainer policy, and `rules/contract-first.md` for a test per operation |

## OpenAPI (API-1 to API-4)

Source: OpenAPI Specification (<https://spec.openapis.org/oas/latest.html>).

- At the time of reading the latest is v3.2.1 (10 September 2026); 3.1.2 is the last 3.1 patch. The catalog named 3.1; the rule says 3.1 or later and leaves the exact version to the project.
- The `openapi` field MUST hold the version of the specification the document uses, and each `operationId` MUST be unique among the operations of the API. A document that sets it, and a route comparison that keys on it, is how API-2 is decided.
- Lint: Spectral, a linter for JSON and YAML with built-in OpenAPI support and the `spectral:oas` ruleset (<https://github.com/stoplightio/spectral>).
- Breaking changes: oasdiff compares two OpenAPI documents, its `breaking` command reporting only the changes that break clients, with 3.0 and 3.1 support confirmed on its page (<https://github.com/Tufin/oasdiff>). A project on 3.2 confirms the tool's 3.2 support before it relies on it.

| Part | Threshold | Source |
|---|---|---|
| a document for every route | 100% | maintainer policy; the direction is `rules/contract-first.md` condition 1 |
| served = declared | 0 divergences | maintainer policy |
| lint errors; responses validated | 0; 100% | maintainer policy; the ruleset is the project's |
| breaks without a version | 0 | the standard breaking set already named in `rules/contract-first.md` condition 5 |

## Protobuf and gRPC (RPC-1 to RPC-4)

Sources: the Protobuf Style Guide (<https://protobuf.dev/programming-guides/style/>), the Language Guide for proto3 (<https://protobuf.dev/programming-guides/proto3/>), buf's lint and breaking documentation (<https://buf.build/docs/lint/rules/>, <https://buf.build/docs/breaking/>), `google/rpc/status.proto` in `googleapis`, and the gRPC error guide (<https://grpc.io/docs/guides/error/>).

- The style guide gives `TitleCase` for messages, services and methods, `snake_case` for fields and package names as dot-delimited `lower_snake_case`, and an enum zero value with the `_UNSPECIFIED` or `_UNKNOWN` suffix. It names no version suffix and no request/response uniqueness rule. Those two come from buf's STANDARD lint category: `PACKAGE_VERSION_SUFFIX` (the last component of a package is a version) and `RPC_REQUEST_RESPONSE_UNIQUE` (every request and response message is unique across the schema). The rule therefore cites buf for those and the style guide for the naming.
- The language guide says a deleted field's number should be added to `reserved`, that the compiler rejects reuse, and that reusing a number makes decoding of wire-format messages ambiguous. It also requires the `syntax` or `edition` line to be the first non-empty, non-comment line, and the compiler assumes proto2 if it is absent, which is why RPC-1 states proto3 or an edition.
- `buf breaking` compares a schema with an earlier version and reports changes that break clients, servers or generated code, in the categories FILE, PACKAGE, WIRE_JSON and WIRE. The rule leaves the category to the project and requires 0 breaks in the category it chose.
- `google.rpc.Status` has `code`, `message` (developer-facing, English) and `details` (a list of messages). The gRPC guide describes the richer error model as extra details in trailing metadata and lists stack traces among the detail types it can carry. Nothing there bans them, so the ban in RPC-4 is maintainer policy and not a borrowed requirement.

| Part | Threshold | Source |
|---|---|---|
| `.proto` exists, code generated | 100% | maintainer policy; the direction is `rules/contract-first.md` condition 1 |
| lint errors | 0 | buf STANDARD category and the style guide |
| breaks without a version; reserved numbers | 0; never reused | the language guide for the reserved rule; buf breaking for the diff |
| status code and details, no stack | 100% | gRPC error model; the no-stack ban is maintainer policy |

## Where this stops

This document cites the specification text read on 14 November 2026 and does not track later versions; a reader re-checks the version a project pins. It covers the three standards named and not AsyncAPI, Avro or GraphQL; `skills/detecting-contract-breaks` in the quality plugin handles other published surfaces by the same breaking set.
