---
name: reviewing-security
description: Use when a change under review adds a credential-shaped literal, a dependency, a path from outside input to a query, command, file or URL, an access check, sensitive data, or a call to a language model. Opens only the checklists the routed lines call for; every finding names who gains what.
type: skill
clade: engineering
subclade: quality
references:
  - docs/review-findings.md
  - docs/review-routes.md
  - skills/reviewing-diffs/SKILL.md
---

# Reviewing security

One question, asked of a change that already exists: with this change, who that should not be able to can now read, alter, execute or take something down?

The conditions are checklists in `references/`, one file per subject, and a review opens only the files its routes name. Each condition gives the state, how it is detected, what exempts it and the change that corrects it. They are identified by a prefix and a number, and that identifier is what a finding cites.

## 1. Take the routes, and open nothing else

`skills/reviewing-diffs/SKILL.md` step 2 has already run the router. Read its output for the routes that select this skill.

| Route | Opens |
|---|---|
| `secrets` | `references/secrets-and-supply-chain.md`, conditions SEC-1 to SEC-4 |
| `supply-chain` | `references/secrets-and-supply-chain.md`, conditions SUP-1 to SUP-6 |
| `untrusted-input` | `references/untrusted-input.md` |
| `access` | `references/access-and-sensitive-data.md` |
| `language-models`, `agent-authority` | `references/language-models.md` |

`secrets` is a baseline: it fires on every authored file. When it is the only route that fired, sweep the added lines against SEC-1 to SEC-4 and stop. A change that touches no code, no manifest and no instruction file owes this skill nothing more.

The failure that recurs here is opening every reference because the change looks important. The drivers are what make two reviews of one diff read the same conditions.

## 2. Read the repository's own answers first

Before any checklist: how this repository authenticates a caller, where an owner or tenant identity comes from, which module reads secrets, which endpoints are public on purpose. Look in `AGENTS.md`, `CLAUDE.md`, the architecture document and the decision records.

Where the repository wrote an answer, it outranks the checklist. Where it wrote none and a condition depends on one, the finding is a **question** under `docs/review-findings.md`, naming the missing answer.

Then list the checks the pull request already passed. A green secret scan, dependency audit or security linter decides what it covers, and a condition a script already decided on this change is not reported again.

## 3. Map what enters and where it lands

For each line the routes point at, follow the value both ways, in the whole file and not only the hunk.

- **Where it enters.** A request, a queue message, a file, a webhook, a third party's response, a stored field somebody else wrote, a model's output.
- **Where it lands.** A query, a command, a path, a URL, a template, a log line, a response, a prompt, a tool call.

Write the pairs down. A finding in the next step is decided on a pair, read in the code, and not on a pattern match. The router's line drivers say where to look; they do not say anything is wrong.

## 4. Apply the routed conditions

Work condition by condition through each opened reference, looking for its state on the pairs from step 3.

For every candidate, name the party that gains and what they gain: an anonymous caller, a user of another tenant, a user without the role, whoever controls an input, whoever writes text a model reads, whoever reads a log or the repository, whoever publishes a dependency. A weakness nobody on that list profits from is not a security finding. It may be a correctness defect, and `skills/reviewing-diffs/SKILL.md` owns that.

Then read the condition's `Exempt` line and drop what it excludes.

## 5. Record what could not be seen

A scenario that depends on a network rule, a provider's policy, an identity provider's configuration or anything else outside the repository is an **unchecked** finding naming that configuration. Execution follows step 1 of `skills/reviewing-diffs/SKILL.md`: on an external fork nothing is installed, built or run, and no request is ever sent to a running system from this skill.

## 6. Write the findings

Each finding carries the four fields in `docs/review-findings.md`, with the condition identifier where the rule and condition number go, and one field more: the party and the gain from step 4.

The severity is assigned by that document's four tests and by nothing else. A grave finding on a line the change did not touch is still deferrable, and its body says how grave.

A credential that reached a commit is reported for rotation as well as removal, because deleting the line leaves it in history.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here.

## When this skill does not apply

**A defect nobody can exploit.** A wrong result, a crash or a race with no party who gains is read against the engineering rules by `skills/reviewing-diffs/SKILL.md`.

**Whether a published surface broke.** That is `skills/detecting-contract-breaks/SKILL.md`, which needs the base version of the surface.

**Whether an instruction file is clear, consistent or loaded at the right time.** That is `skills/reviewing-prompts/SKILL.md`. This skill reads the same file for one thing only: what the model that reads it is allowed to cause.

**An audit of the whole repository.** This follows the diff as far as a scenario needs, and marks what lies outside it deferrable.
