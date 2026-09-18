---
id: artifact-model
type: doc
clade: foundation
title: The artifact model
summary: Why the framework has five artifact types, how to choose between them, and why authority runs in one direction.
references:
  - rules/pilars.md
  - rules/naming.md
  - rules/frontmatter.md
  - rules/completeness.md
---

# The artifact model

This is the reference for four of the five foundation rules: `rules/pilars.md`, `rules/naming.md`, `rules/frontmatter.md` and `rules/completeness.md`. They state what is checked; this states why. The fifth, `rules/progressive-disclosure.md`, has its own companion in `docs/context-budget.md`.

## Five types, one job each

Every piece of content the framework ships is exactly one of five things.

| Type | Job | The question it answers |
|---|---|---|
| **rule** | An unbreakable guardrail. | What may I never do? |
| **doc** | A reference manual. | What do I need to know to decide? |
| **skill** | A repeatable procedure. | How do I carry this out? |
| **agent** | A specialist that orchestrates skills. | Who does this kind of work? |
| **command** | An entry point. | How does a person start it? |

The list is closed. A sixth type is not a gap to fill, it is a sign that something is being written at the wrong altitude.

## Choosing a type

Take the candidate and ask, in order:

1. **Can it be violated?** If the answer is "yes, and the result is defective," it is a rule. If the answer is "yes, and the result is merely different," it is not.
2. **Does it have steps?** A procedure with an order and an end state is a skill. A body of knowledge with no order is a doc.
3. **Does it choose between skills?** Something that decides which procedure applies, and in what sequence, is an agent.
4. **Is a person typing it?** An invocation surface is a command. It holds no logic of its own.

Most mistakes are a rule that should be a doc. The test is the first question. "Prefer composition over inheritance" fails it: both produce working code, so it is guidance, and guidance belongs in a doc. "A concrete type never raises `NotImplementedError`" passes it: the result is a type that lies about its interface.

## Authority runs one way

The five types form a hierarchy, and references may only run along it.

```
command  ──▶  skill, agent
agent    ──▶  skill, doc, rule, agent
skill    ──▶  rule, doc, skill
doc      ──▶  doc, rule
rule     ──▶  doc
```

Three consequences are worth naming.

**A command references no rule and no doc.** A command that reads a rule has become a procedure, and the procedure should have been a skill it invokes. Keeping commands thin is what makes them cheap to add.

**A rule references only a doc, and only for rationale.** Nothing may contradict a rule, so a rule that leans on a skill would invert the hierarchy: the guardrail would depend on the thing it constrains.

**A rule carries no rationale of its own.** Rationale is what makes a rule long, and a long rule is one nobody loads. The rule states the condition and links here. This document is that link for the three foundation rules.

## Why references are untyped

A reference is a path in the `references` list, with no verb attached. There is no `applies`, `consults` or `extends`.

The verb is already determined by the pair of types. A skill pointing at a rule applies it; there is nothing else a skill can do with a rule. A skill pointing at a doc consults it. Writing the verb down adds a second source of truth that can disagree with the first, and the gate would then have to decide which one is right.

If a pair of types ever admits two genuinely different relationships, the verb earns its place. Until then it is a field to maintain and a field to get wrong.

## Why some rules ship a hook and others do not

A rule is only as strong as what checks it. Two routes exist, and the rule declares which one it takes in its `enforcement` field.

**`enforcement: hook`** means the condition is mechanically decidable, and a script in `hooks/` decides it. The rule costs no context, and it cannot be skipped by an agent that did not read it.

**`enforcement: judgment`** means the condition needs a reader. The rule's one-line `statement` goes into the platform's instruction file with a link to its full text, and nothing else does.

Declaring `judgment` is allowed. Declaring `judgment` for something that is decidable is how a framework fills up with rules that nobody enforces, so the review question for every new rule is whether a script could have decided it.

## What makes an artifact complete

An artifact is authored by filling a template, and that decides which defects survive to review. They are not subtle ones: they are the parts of the template nobody filled.

**A leftover marker or bracket is the most common.** `TODO`, `TBD`, and an unreplaced `<noun phrase, title case>` in a title all pass a schema check, because the field is present and non-empty. Only reading catches them, and reading is the expensive thing. So `rules/completeness.md` makes the gate read for them instead.

The scan skips code, and that is not a compromise. `<plugin>` and `<name>` on a command line are what the reader is meant to substitute, and a backticked `TODO` is prose about markers rather than a marker. Every angle bracket in this corpus is one of those two, which is why scanning code would fail nothing real and reject everything honest.

**A missing section is the other.** Each type owes its reader a fixed set: a rule owes its conditions and its boundary, a skill owes the cases it does not handle, an agent owes what it refuses. These are not formatting preferences. The boundary section is what separates a rule from dogma, and the "does not apply" section is what stops a skill being reached for in the wrong situation. An artifact that drops them is not shorter, it is incomplete.

Fixed headings also let a reader skim a corpus they have never seen, and let the gate check presence without understanding content.

## Where this stops

The model governs artifacts, not code. A bounded context, a module layout or a class design is the subject of an artifact, never an artifact itself.

It also says nothing about quality. A rule that passes every check in `hooks/validate-artifacts.py` can still be a bad rule. The gate protects the shape of the corpus; the review protects its content.
