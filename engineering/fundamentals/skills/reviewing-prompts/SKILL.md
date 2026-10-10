---
name: reviewing-prompts
description: Use when a change under review edits text a model reads as instructions - a CLAUDE.md or AGENTS.md, a system prompt in a file or built in code, or an agent, skill or command definition. Reads the prompt as its reader will, with nothing but the page; every finding names the line and the behaviour it produces.
type: skill
clade: engineering
subclade: quality
references:
  - docs/review-findings.md
  - docs/review-routes.md
  - skills/reviewing-diffs/SKILL.md
  - skills/reviewing-security/SKILL.md
---

# Reviewing prompts

A prompt is code whose interpreter is a reader with no memory of the author's intent. The defect this procedure looks for is a line that will make that reader do something the author did not mean, and the finding says which line and what it will do.

The conditions are checklists in `references/`, identified by a prefix and a number. A finding cites the identifier.

## 1. Take the routes, and open nothing else

`skills/reviewing-diffs/SKILL.md` step 2 has already run the router. Read its output for the routes that select this skill.

| Route | What fired it | Opens |
|---|---|---|
| `instruction-files` | an instruction file, a prompt file or a prompt template | `references/instructions.md` |
| `prompts-in-code` | an added source line that writes instructions for a model | `references/instructions.md` |
| `agent-definitions` | an agent, skill or command definition | `references/instructions.md` and `references/agent-definitions.md` |

The same file usually fires `agent-authority` in `skills/reviewing-security/SKILL.md` too. That skill decides what the model may cause. This one decides whether the model will understand what it is asked.

## 2. Establish who reads the prompt, and when

Three facts, because every condition is applied against them.

- **The reader.** Which model or platform loads this text, and through which mechanism: always in context, loaded when a description matches, or passed to a subagent that sees nothing else.
- **What else the reader holds.** The other instruction files in force, the tools it has, and what the caller will have told it. For a prompt built in code, read the builder and every variable it interpolates.
- **What the prompt is for.** From the pull request's description and the linked issue. A prompt is right or wrong only against a job.

For a prompt built in code, reconstruct the text as the model receives it for one concrete input before going on. Reviewing the template with its holes still open misses what the filled-in page says.

## 3. Read it cold, once, as the reader

Read the whole text top to bottom with only what step 2 says the reader holds. Mark every place where you had to use knowledge the reader lacks: a term never defined, a file or tool named but not available, a "the above" with nothing above, a standard referred to and not stated.

The failure that recurs here is reading as the author. The reviewer has the pull request, the issue and the repository; the model has the page.

## 4. Apply the routed conditions

Work condition by condition through each opened reference. For each candidate, state the behaviour the line produces: what the reader will do, on what input, that the author did not want.

Where the repository has examples of the prompt's output, a transcript, an evaluation or a test, read them. They decide a condition that reading alone leaves a question.

Then read the condition's `Exempt` line and drop what it excludes.

## 5. Read what the change removed

Open the base version of the file. A deleted sentence is invisible in the new text and is often the one that held a behaviour in place: a constraint, a stop condition, the reason beside a rule.

For each removed instruction, find where the new text carries it or why it is no longer needed. Neither is a **question** for the author, naming the sentence.

## 6. Run it, or record that you did not

When the repository declares an evaluation or a prompt test, and step 1 of `skills/reviewing-diffs/SKILL.md` permitted execution, run it with the command the project declares.

When there is none, or execution was not permitted, record one **unchecked** finding: the prompt was read and not run. A prompt's behaviour is observed in outputs, and a review that only read says so.

## 7. Write the findings

Each finding carries the four fields in `docs/review-findings.md`, with the condition identifier where the rule and condition number go. The state observed is the quoted line and the behaviour it produces. The change that resolves it is replacement text, written out, and not advice to clarify.

Severity follows that document's four tests. A condition whose state depends on what the author intended is a **question**, and most findings from a first reading of somebody else's prompt are.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the prompt.

## When this skill does not apply

**An artifact of this framework.** A rule, doc, skill, agent or command that declares a clade is routed to `ahrena-foundation:skills/reviewing-artifacts/SKILL.md`, which asks whether it is the right type and whether its conditions can be decided. An agent or skill of the framework fires both routes, and both run: that one reads the artifact's shape, this one reads the text a model will follow.

**What the model is allowed to cause.** Tool grants, permissions and injected instructions are `skills/reviewing-security/SKILL.md`, conditions LLM-1 to LLM-11.

**Writing or improving a prompt.** This reads one that exists and reports. Rewriting it is the author's work, from the findings.

**Copy written for people.** Interface text, documentation and messages a person reads are not instructions to a model.
