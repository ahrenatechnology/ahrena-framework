---
name: writing-hooks
description: Turn a rule's conditions into a script that decides them. Use when a rule declares enforcement hook, when a review finds a judgment rule that a script could have decided, or when an existing hook needs a new condition. Covers detector choice, the test-first fixture pattern, failure messages and the no-dependency constraint.
type: skill
clade: foundation
references:
  - rules/frontmatter.md
  - rules/pilars.md
  - docs/artifact-model.md
  - skills/reviewing-artifacts/SKILL.md
---

# Writing hooks

A rule that nothing checks is a claim. This is how a claim becomes a guardrail.

## 1. Start from the rule's conditions, and refuse if they are not there

Open the rule and read its numbered conditions. Each one must name a detectable state.

If they are maxims, stop. The hook cannot be written and pretending otherwise produces a script that approximates the rule, which is worse than no script: it passes things the rule forbids and fails things it allows, and people learn to distrust the gate rather than the rule.

Send it back to `skills/reviewing-artifacts/SKILL.md` and get the conditions stated first.

## 2. Pick a detector per condition

One condition, one detector, named in the rule. The cheapest detector that is exact beats the sophisticated one that is approximate.

| Shape of condition | Detector |
|---|---|
| a value's format | a regular expression |
| a file's location or name | a path walk |
| a reference that must resolve | a lookup against an index built first |
| a structural property of code | the language's own AST module |
| a dependency that must be acyclic | a graph built from imports, then a cycle search |

Reach for an AST before a regular expression whenever the subject is code. A regular expression over source is a detector that silently stops matching when somebody reformats.

## 3. Write the failing fixture first

Build the smallest tree that violates the condition, run the hook against it, and watch it fail for the reason you intend.

`references/test-template.py` is the pattern: a temporary directory, the files written into it, the hook invoked as a subprocess, and an assertion on both the exit code and the message. Running it as a subprocess is deliberate. It tests the thing CI runs, including the exit code, rather than a function that happens to live in the same file.

Write the passing fixture too. A detector that never accepts anything is as broken as one that never rejects, and only the pair catches it.

## 4. Implement, with no dependencies

`references/hook-template.py` is the skeleton: discover, parse, check, report, exit non-zero.

**Standard library only.** The hook ships inside the plugin, so a consumer runs the same check CI runs with nothing to install. A dependency turns that into an install step, and an install step turns the gate into something people skip locally and discover in CI.

When a format is hard to parse without a library, constrain the format instead of taking the dependency. That is why frontmatter is a flat map of scalars and lists.

## 5. Make the message do the work

A failure message is read by somebody who is blocked and wants to stop being blocked. It names three things:

- **where**, as a path and a line where a line exists
- **which rule**, by id, so the full text is one search away
- **what is wrong**, in the rule's own vocabulary

Compare. `invalid frontmatter` sends the reader to the source of the hook. `[frontmatter] line 8: 'enforced_by' is not a valid field name` sends them to the fix.

Never make the message advise a workaround that defeats the rule.

## 6. Run both, then wire it in

```sh
python3 <plugin>/hooks/<name>.py           # the gate
python3 <plugin>/hooks/test-<name>.py      # the fixtures
```

Add both to the workflow, tests first. A gate whose own tests are not in CI stops being trustworthy the first time somebody edits it in a hurry.

Then set `enforced-by` on the rule to the hook's plugin-relative path. The gate checks that the file exists, so a rule claiming an enforcement it does not have fails immediately.

## 7. Record what resisted

Some conditions do not fully reduce to a script. Say so, in the rule's "where this stops", with the reason and the cost of closing it.

A documented limit with a test pinning the current behaviour is honest and survives contact with the next contributor. An undocumented one gets read as an oversight and "fixed" by somebody who does not know why it was left.

## When this skill does not apply

Hooks that react to platform events (a `PreToolUse` in Claude Code, for instance) rather than deciding a rule's conditions. Those are configuration for a platform's lifecycle, and the platform's own documentation governs them.
