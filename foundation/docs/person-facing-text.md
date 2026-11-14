---
id: person-facing-text
type: doc
clade: foundation
title: Writing for the Person Who Decides
summary: Why an agent's text for a person has its own rule, the measurements that asked for it, and what each of the three voices it was merged from contributed.
references:
  - rules/person-facing-text.md
---

# Writing for the Person Who Decides

This is the companion of [`rules/person-facing-text.md`](../rules/person-facing-text.md). The rule states what a text must do; this document says why each part is there and where it came from.

## The gap the rule closes

Until this rule, every agent in the framework was written to be called. Its output section defines what it returns to a caller: a first line (`DONE`, `BLOCKED`, `NEEDS_APPROVAL`) and a list of `key: value` fields. That is the right shape for another agent to read. No artifact said what happens next, when the session's agent turns that block into something a person reads and decides from. The person got a summary of a protocol, with the protocol's identifiers still in it.

## What was measured

The owner's prompts were read in every session that launched the tech-lead agent, on the owner's machine and on the remote workstation, opening briefs not counted. A keyword classifier sorted each one by the time it was sent; every slice is approximate. Measured on 14/11/2026. The boundary between the two windows is 12/11/2026 at 02:10 (UTC-3), the time of the measurement reported in #262: a prompt sent before it is in the first row, one sent after it in the second. The first row is not #262's own count (63 sessions, 974 interventions): this measurement ran the classification again over every session that launched the agent, the coordinating sessions included, which #262 had left out.

| Window | Sessions | Interventions classified | Asking the agent to explain what it proposed |
|---|---|---|---|
| 20/10/2026 until the boundary | 67 | 955 | 346 (~36%) |
| The boundary until 14/11/2026 | 45 | 168 | 74 (~44%) |

Over the second window the agency got faster and needed fewer interventions per session. The share of interventions that were requests for explanation did not fall. Speed was not the problem those requests point at; the text was.

One session in the second window shows the cost at its worst: 39 prompts from the owner to get a single message for a third party into a state that could be sent. Read in order, the corrections repeat five things. Each became a condition.

| What the draft did | The condition it became |
|---|---|
| Opened with the mechanism | 1, business impact first |
| Used terms the reader does not use | 2, the reader's words |
| Skipped how the thing is done today | 3, today before the change |
| Opened by defending what the system does not do | 6, the proposal before the defence |
| Cited internal records the reader could not open | 9, no internal identifiers |

The owner ended up rebuilding the explanation by asking basic questions one at a time: what the thing is for, what it configures, what happens next. Those questions are the outline the agent should have answered before writing, and condition 5 asks for it.

## Three voices, merged

The rule was not written from nothing. Two projects built on this framework already had a written brand voice, and the owner's corrections formed a third.

| Source | What it contributed |
|---|---|
| The first brand voice | Affirmative statements; every text serves a decision; a technical term always comes with its translation; a claim rests on a number or a reference |
| The second brand voice | The text is about the reader's journey, not about how the platform works inside; know who reads before writing; the number before the adjective; recommend, and say what is lost; a tone for each moment |
| The owner's corrections | Business impact first; a proposal with every problem; a real reference for a technical term, so a reader who does not know the subject can learn it; the reader's native language |

The two brand voices agree almost everywhere. Where a project has one, it still wins over this rule on vocabulary and tone, as the rule's last section says; the rule keeps only what both share and what the measurements asked for.

## Why the reader's language is a premise

A person reading a second language spends part of their attention translating, and that part is taken from the decision. The framework already keeps the user's language for what a person reads and English for everything behind the scenes ([`backstage-language`](../../engineering/fundamentals/rules/backstage-language.md)). This rule states the first half as a premise, because every condition after it assumes the reader is not also translating.

The framework's own artifacts stay in English. A model reads them. Their examples are in the reader's language, because an example shows what the person will read.

## Why the examples are invented

The patterns were learned from real sessions. The examples were then written on an invented case, a shop and its invoices. A rule is loaded into other projects' sessions, and a real example would carry one project's systems, numbers and people into all of them. The pattern travels; the case does not.

## Running the rule

A rule a model follows is observed in what the model writes, so this rule ships with a prompt test a reviewer can run:

```sh
python3 foundation/prompt-tests/run.py foundation/prompt-tests/person-facing-text/cases.json
```

It gives a model the rule and one of five situations (a plan for approval, an escalation, a block, a result, and a person who writes in English), each built around a block an agent returned to its caller. It takes the text the model writes for the person and decides it twice.

| Decided by | What |
|---|---|
| The script | the text's language; a protocol field pasted into it; a decision-record number, a file and line, a path or an agent's name; a reference the person need not open; a closing with more than one question or an offer of further help; an adjective in a number's place |
| A second model call, the judge | conditions 1 to 10, one verdict each, with the words that decided it |

Each case runs three times and passes when two samples pass. The command exits 0 when every case passes, 1 when one fails, and 2 when the model could not be reached, which a reviewer records as not run. `--baseline` writes without the rule, to see what the rule changes; `--out` saves the report, which prints every output.

The script's own checks are tested in `foundation/prompt-tests/test-run.py`, which CI runs. The model calls are not in CI: they need a credential, and a rule's review is the moment they are for.

The judge is a model and can be wrong in both directions. The report shows each output beside its verdicts so that a reviewer reads the text and does not take the verdict alone. Condition 11 is not judged: it binds a step before the draft, which a single output does not show.

## Why judgment and not a hook

Whether a first sentence states a business impact, whether a word is the reader's, whether an example teaches: each needs a reader. The decidable fragments are too small to carry the rule. The fragments a script can decide (the language, a pasted protocol field, an internal identifier) are decided by the prompt test above, over a model's output. A hook over the text of a live session would need to see that session, which no hook does.

## Where this stops

This document does not define the escalation card (its five parts belong to #262), does not say which decisions reach a person, and does not describe how an agent takes a session's role. It explains one rule.
