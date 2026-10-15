---
name: driving-with-tdd
description: Use to drive out the inner backend layers with tests first — red, then green, then refactor — unit-first on the aggregates at the domain, use-case tests against test doubles for the ports, and integration tests against a real database at the OLTP. The test is written before the code it describes and fails before it passes.
type: skill
clade: engineering
subclade: backend
references:
  - ahrena-engineering-fundamentals:rules/aggregates.md
  - ahrena-engineering-fundamentals:rules/clean-code.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
---

# Driving with TDD

Test-driven development is the discipline that drives the inner three layers of an inside-out build. Each unit of behaviour is written as a failing test first, made to pass with the smallest change, then refactored under a green bar. The arc differs per layer in what it doubles and what it touches, but the order — red, green, refactor — does not.

## 1. Resolve the testing tools from the component map

Run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md) and read the backend component's `testing` lanes for the unit and integration tools. The runners named below are placeholders; the project's stated tool replaces them, and reading the map is step one, not an afterthought.

## 2. Write the test red, before the code

For the unit of behaviour you are about to build, write the test first and run it. Confirm it fails, and that it fails for the reason you expect — the type does not exist, the method is unimplemented — rather than a typo in the test. A test that passes the moment it is written tested nothing, or tested a placeholder.

The test names the behaviour in the project's domain vocabulary, per `ahrena-engineering-fundamentals:rules/clean-code.md`: a reader learns what the aggregate does from the test names before reading the code.

## 3. Domain — unit TDD on the aggregates, red-first

At the domain, drive each aggregate, value object and domain service from unit tests with no doubles and no IO: the domain imports no mechanism, so there is nothing to mock. Write the invariant as a failing assertion, then let the aggregate enforce it. The boundary each test exercises is the one [`ahrena-engineering-fundamentals:rules/aggregates.md`](../../../fundamentals/rules/aggregates.md) draws — one invariant inside one root — so a test that needs two roots to set up is a test telling you the boundary is wrong.

## 4. Use cases — tests against test doubles for the ports

At the use-case layer, the unit under test is the orchestration, and its dependencies are the ports the domain declares. Stand a test double in for each port — a repository, a clock, a publisher — so the use case is driven without a database or a network. The double asserts the use case called the port as the behaviour requires; the real adapter behind the port is the next layer's concern.

## 5. OLTP — integration tests against a real database with migrations

At the OLTP layer, the doubles come out. Drive the repository implementations against a real database instance with the migrations applied, because the defects this layer owns — a violated constraint, a transaction that does not isolate, a mapping that drifts from the aggregate — are exactly the ones a double cannot show. The test sets up through the schema and asserts through it, so a migration that is wrong fails here rather than in production.

## 6. Refactor under green

Once the bar is green, improve the code without changing behaviour: remove duplication, rename for the domain, collapse an abstraction that earned nothing. The tests are the safety net that makes this safe, and the refactor step is where the design is actually paid for — skipping it leaves the first green shape, which is rarely the right one.

## When this skill does not apply

**The API's acceptance arc.** The outermost layer is closed with behaviour scenarios and contract tests, not unit TDD; that is `specifying-with-bdd`'s subject, and this skill hands off to it there.

**Choosing the tools.** This skill drives tests in the tools the project named. Deciding what a project's testing lanes should be is a change to its component map, which the owner consents to, not something settled here.

**A change with no new behaviour.** A refactor or a dependency bump that changes nothing the system does opens no new test; it must keep the existing suite green, and that is all.

<!--
Directory layout:

skills/driving-with-tdd/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
