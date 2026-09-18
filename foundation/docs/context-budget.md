---
id: context-budget
type: doc
clade: foundation
title: The context budget
summary: What each artifact type costs a request, when each one loads, and why material that is copied rather than typed belongs outside the body.
references:
  - rules/progressive-disclosure.md
  - rules/frontmatter.md
---

# The context budget

Every artifact competes for the same finite context as the task. This is the accounting that keeps the competition honest.

## Three tiers, not two

The common mistake is to think of an artifact as either loaded or not. There are three tiers, and the difference between them is where the whole budget lives.

| Tier | What loads | When |
|---|---|---|
| **Always** | a skill's and agent's `description`, and a judgment rule's `statement` | every request, including the ones with nothing to do with it |
| **On trigger** | the `SKILL.md` or agent body | when the platform selects it |
| **On demand** | `references/` and `scripts/`, and any doc | when a step reads it |

A rule with `enforcement: hook` costs nothing in any tier. It is enforced by a script that runs, not by text an agent has to read, which is the strongest argument for writing the hook.

A doc is never injected. It is read at the moment a decision needs it, which is why a long doc is cheap and a long rule is not.

## The tier that actually hurts

The body of a `SKILL.md` is the tier people get wrong, because it feels free. It is not always loaded, so it escapes the scrutiny the `description` gets, and it is not on demand either, so it is paid in full every single time the skill fires.

That is the worst place for material the reader will copy rather than read. A 60-line template in the body is 60 lines the agent processes on every invocation, including the ones where the template is not the step being executed.

Moving it to `references/` costs one line in the body (the path) and loads the 60 lines only when the step that needs them runs. Same material, a fraction of the cost, and the procedure gets shorter and easier to follow as a side effect.

## Where the ten came from

The cap in `rules/progressive-disclosure.md` is not a round number picked for looking reasonable. It was measured against the corpus that already existed when the rule was written.

| | Value |
|---|---|
| Largest code block inline in a skill body | 2 lines |
| Smallest file in a `references/` directory | 27 lines |

Everything inline was a command being typed. Everything substantial was already outside. Ten sits in the empty span between the two, with five times the headroom over current practice and still well under anything that could be a template.

A threshold in a gap like that is cheap to keep: it fails nothing that exists, and it cannot be reached without a genuine change of kind.

## Why unreachable material also fails

The rule requires every file under a skill's `references/` and `scripts/` to be named in `SKILL.md`.

Progressive disclosure is not "put it in a file." It is a step that knows what to open. Material no step names is not deferred, it is unreachable, and it will drift out of agreement with the procedure because nothing brings the two together.

The check is deliberately lenient (a mention of the filename anywhere in the body satisfies it) because a false positive here blocks a correct skill, while a false negative just leaves a file the reviewer catches.

## Where this stops

The budget says nothing about whether the content is good. A tight, cheap, well-tiered skill can still describe the wrong procedure.

It also does not reach docs or rules. A doc is the material, so length is its job. A long rule is a defect, but the existing mechanism catches it: `statement` is capped at 160 characters, and rationale has a doc to go to.
