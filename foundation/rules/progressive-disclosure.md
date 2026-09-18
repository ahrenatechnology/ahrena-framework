---
id: progressive-disclosure
type: rule
clade: foundation
title: Progressive disclosure
statement: A code block in a skill or agent body is at most 10 lines, and every file in a skill's body is named by a step.
enforcement: hook
enforced-by: hooks/validate-artifacts.py
references:
  - docs/context-budget.md
---

# Progressive disclosure

## The cap

A fenced code block in a `SKILL.md` or an agent body holds at most **10 lines** between its fences.

A block under the cap is a step's invocation, the line a person types. Anything longer is material that is copied and edited rather than typed, and it belongs in `references/`. Anything that runs belongs in `scripts/`.

The body pays its cost every time the artifact fires. `references/` and `scripts/` are read only by the step that names them. `docs/context-budget.md` works the accounting and shows where the 10 came from.

## Reachability

Every file under a skill's `references/` and `scripts/` is named somewhere in its `SKILL.md`.

Deferring material to a file is only disclosure if a step knows to open it. A file no step names is not deferred, it is unreachable.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. No fenced code block in a skill or agent body exceeds 10 lines.
2. Every file under a skill's `references/` or `scripts/` appears by name in its `SKILL.md`.

## Where this stops

**Docs and rules are out of scope.** A doc is the material, so its length is its job. A long rule is already caught by the 160-character cap on `statement` in `rules/frontmatter.md`.

**The cap counts lines, not intent.** It cannot tell a legitimate eleven-line invocation from a template. If a step genuinely needs to type eleven lines, that is a script, and `scripts/` is where it goes; the gate pushing you there is the rule working, not a false positive.

**The reachability check matches on filename, anywhere in the body.** It will accept a mention in prose that no step acts on. That leniency is deliberate: blocking a correct skill costs more than letting a reviewer catch a stray mention.

**Nothing here bounds the body itself.** A skill with no code at all can still be far too long. That is a judgment call, and `skills/reviewing-artifacts/SKILL.md` carries it.
