---
name: specifying-with-bdd
description: Use at the API layer of an inside-out build, to close the capability on behaviour. Turns the story's acceptance criteria into Given/When/Then scenarios, names each scenario with its criterion token so a script can trace it, and verifies the API against a consumer-driven contract — the acceptance gate the stack goes green at.
type: skill
clade: engineering
subclade: backend
references:
  - ahrena-engineering-fundamentals:rules/contract-first.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-python:skills/reviewing-python/SKILL.md
  - ahrena-contributing:skills/writing-acceptance-criteria/SKILL.md
---

# Specifying with BDD

Behaviour-driven development is how the outermost layer of an inside-out build is closed. The story's acceptance criteria become executable scenarios, written in Given/When/Then, run against the assembled API. This is where the behaviour the whole stack was driven toward goes green, and where it is tied back to the requirement it satisfies.

## 1. Read the component map and the story's criteria

Run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md) for the backend component's acceptance and contract-test tools. Take the story's acceptance criteria from the issue, where [`ahrena-contributing:skills/writing-acceptance-criteria/SKILL.md`](../../../../contributing/skills/writing-acceptance-criteria/SKILL.md) says they live and nowhere else — each one numbered `AC-n`.

## 2. Write each criterion as a Given/When/Then scenario

For every acceptance criterion, author one scenario: Given the state the criterion assumes, When the action it describes, Then the outcome it requires. The scenario is phrased in the project's domain vocabulary, not in the shape of the handler, so it reads as a statement of behaviour a non-engineer could check against the story.

The recurring failure is covering only the happy path. A criterion with an error or a boundary — a rejected request, an absent record, an unauthorised caller — is its own scenario, because those are the behaviours a consumer depends on and the API most often gets wrong.

## 3. Name each scenario with its criterion token

Tag each scenario with the token `#<issue>/AC-n` naming the criterion it covers, anywhere the scenario's file allows. This is the framework's traceability convention, which `ahrena-contributing:rules/traceability.md` enforces: a script reads the issue's criteria and the tokens in the tree and fails when a live criterion has no test or a test names a criterion that is not there. A scenario with no token is a scenario the trace cannot see.

## 4. Verify the consumer-driven contract

Capture the contract the API's consumers depend on and verify the API against it, rather than asserting whatever the handler currently returns. The contract is authored and the code is validated against it, per [`ahrena-engineering-fundamentals:rules/contract-first.md`](../../../fundamentals/rules/contract-first.md): a generated contract agrees with the code by construction and cannot catch the change that breaks a consumer. Every operation the contract declares is exercised by at least one contract test.

## 5. Take the stack green

Run the scenarios and the contract tests against the fully assembled API. This is the point the behaviour scenario that led the build is satisfied end to end, and the stack is green from the domain's first unit test to here. A red scenario at this layer whose domain and use-case tests are green is an integration or contract defect, not a model defect — it is this layer's to fix.

## 6. Hand the per-language discipline to the specialist

The scenario and contract code is still code, and it is reviewed in the language it is written in. The specialist invokes the per-language review skill for the stack — [`ahrena-engineering-python:skills/reviewing-python/SKILL.md`](../../../python/skills/reviewing-python/SKILL.md) for Python, and the TypeScript, Go and Rust equivalents in their own plugins — so the acceptance layer is held to the same idioms and contracts as every other layer.

## When this skill does not apply

**The inner layers' tests.** The domain, use-case and OLTP arcs are unit and integration TDD, which is `driving-with-tdd`'s subject. This skill is the API layer's acceptance gate, not a replacement for the tests below it.

**Writing the criteria.** This skill turns existing acceptance criteria into scenarios. Authoring the criteria themselves, and settling what done looks like, is the issue owner's, through `ahrena-contributing:skills/writing-acceptance-criteria/SKILL.md`.

**A change with no new behaviour.** A refactor or a dependency bump that changes nothing a consumer observes opens no new scenario; it keeps the existing acceptance suite and contract green, and that is all.

<!--
Directory layout:

skills/specifying-with-bdd/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
