---
name: reviewing-artifacts
description: Review a rule, doc, skill, agent or command for the defects a gate cannot detect. Use when reviewing a pull request that adds or changes artifacts, when an artifact passes CI but reads wrong, or when auditing an existing corpus before building on it. Covers type choice, conditions versus maxims, missing thresholds, drift between an artifact's opening and its body, enforcement route, and always-loaded footprint.
type: skill
clade: foundation
references:
  - rules/pilars.md
  - rules/frontmatter.md
  - rules/progressive-disclosure.md
  - docs/artifact-model.md
  - docs/context-budget.md
---

# Reviewing artifacts

The gate protects the shape of the corpus. This protects its content. An artifact that passes every check in `hooks/validate-artifacts.py` can still be the wrong type, state a maxim nobody can apply, or quietly add a hundred tokens to every request.

## 1. Run the gate before reading anything

```sh
python3 <plugin>/hooks/validate-artifacts.py
```

Spending review attention on kebab-case is waste. If the gate is red, the review has not started yet.

It now also decides leftover markers, unreplaced placeholders and missing sections, so those are off your list. What it cannot decide is whether a section that exists says anything: a `Where this stops` reading "use judgment" passes the gate and fails step 9.

## 2. Challenge the type

This is where most defects are, so it comes first.

Take the artifact and ask the question from `docs/artifact-model.md`: **can it be violated, and is the result defective?** If violating it merely produces something different, it is not a rule, whatever the directory says.

| What you find | What it is |
|---|---|
| A rule whose body is mostly explanation | a doc with a rule-shaped title |
| A doc with numbered steps and an end state | a skill |
| A skill that only picks between other skills | an agent |
| A command with logic in it | a skill that was never written |

Reclassifying is cheap now and expensive after three artifacts reference it.

## 3. On a rule, hunt for maxims

A condition names a detectable state. A maxim names a virtue. They read the same to a careless eye and behave completely differently when an agent tries to apply one.

| Maxim | Condition |
|---|---|
| "A class should do one thing" | "LCOM4 above 1 marks a split candidate" |
| "Avoid deep nesting" | "A function with nesting depth above 3" |
| "Do not lie about the interface" | "`raise NotImplementedError` in a concrete type" |

Every numbered condition must say what decides it. A condition with no detector named is a maxim that has been numbered.

## 4. Put a number where a quantity word stands

"Many", "several", "fast", "simple", "complex", "reasonable", "large", "high latency", "low cost". Each of these sits in a place where a number belongs, and two readers will pick two different numbers and both be right.

This is not step 3 run again. A maxim has no measurable state behind it: "a class should do one thing" cannot be given a threshold, only rewritten into a different condition. An ambiguity has one and the author left it out: "the lookup is fast" is about latency, which is measured every day, and only the figure is missing. A maxim is replaced; an ambiguity is filled in.

Carry the number in the finding. A review that only circles the word hands the author the same blank page they already had. "Many cases" becomes "at least 80% of observed cases", "fast" becomes "p99 at or under 300ms". A proposal wrong by a factor of two is still progress, because it gives the author something to disagree with.

One case is legitimate: the number genuinely arrives in a later phase, after the load test or the pilot. That is acceptable only when the artifact says so and names what produces the figure. An ambiguity with its arrival declared is a plan. The same words without it are a gap.

## 5. Read the statement with no context

A rule's `statement` reaches the agent alone, with a link. Read it cold, as the only thing you know, and ask whether you could act on it. If it needs the body to make sense, it is a summary rather than a statement, and the rule will be ignored in exactly the situation it exists for.

## 6. Read the top against the bottom

What an artifact declares up front and what it does further down were written at different times, and only one of them gets edited when something changes.

| Declared | Read it against |
|---|---|
| The `statement`, or a skill's opening objective | the conditions or steps below it |
| A "correct" and "incorrect" pair | the rule the pair illustrates |
| Declared inputs and outputs | whether each input is consumed by a step, and each output produced by one |
| A count asserted in prose | the number of items actually present |

Each half reads fine alone, which is why these survive every review that reads the artifact once from the top. Reading the halves against each other is the only thing that catches them.

A drifted example is the worst of the four. When the rule and the example disagree, readers follow the example, so the defect ships as compliance.

## 7. Question the enforcement route

For every rule declaring `enforcement: judgment`, ask whether a script could have decided it.

This is the check that decays a corpus fastest if it is skipped. Writing a hook is work, declaring `judgment` is free, and the gap between them is where a framework accumulates rules that nobody enforces and everybody cites.

If the condition is decidable and the hook is missing, that is a finding, not a follow-up.

## 8. Check where the rationale sits

Explanation in a rule makes the rule long, and a long rule is one nobody loads. Explanation absent from the doc makes the rule arbitrary, and an arbitrary rule is one people route around.

Both failures are common. Look for the pair: the rule states, the doc explains, and the rule references the doc.

## 9. Demand a real "where this stops"

A section that says "use judgment" is not a boundary. A real one names the case where applying the artifact harder makes the outcome worse, and it is the section that separates a rule from dogma.

If the author could not find one, either the artifact is narrower than it claims or it has not been used yet.

## 10. On a skill or an agent, test the description

`description` is the only text a platform reads when deciding whether to load the artifact. It has one job: fire in the right situation and stay quiet otherwise.

Read it and ask what situations it names. A description that describes capability ("creates artifacts") rather than occasion ("when adding a new rule, doc, skill, agent or command") will not trigger, and the artifact might as well not exist.

## 11. Separate references from mentions

Every entry in `references` declares a dependency. Prose that names another artifact does not.

Over-declaring is the common direction, and it is not harmless: the graph is what a reader trusts to know what depends on what, and noise in it makes the real edges invisible.

## 12. Price the footprint

Ask what this artifact adds to a request that has nothing to do with it.

A hook rule costs zero. A judgment rule costs one line. A doc costs nothing until something reads it. A skill costs its `description` in every listing, and its body every time it fires.

The gate already decides two of these: the 10-line cap on code blocks in a body, and whether every file in a skill's body is reachable from a step. What is left for you is the part no threshold reaches. A body with no code at all can still be three times longer than the procedure needs, and material can sit in the right tier while being the wrong material. `rules/progressive-disclosure.md` states the mechanics; `docs/context-budget.md` gives you the accounting to argue with.

## 13. Report

Group findings by severity, and say plainly which are blocking.

Name the rule or the condition behind each one. A review that says "this feels heavy" cannot be acted on and will be argued with; a review that says "condition 3 names no detector, so `hooks/` cannot decide it" ends the discussion.

## When this skill does not apply

Reviewing code that an artifact governs. This reviews the artifact, not the codebase it constrains. Those reviews use the engineering rules, not this one.
