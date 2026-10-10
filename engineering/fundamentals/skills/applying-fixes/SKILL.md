---
name: applying-fixes
description: Use when a review has published findings on a pull request and the mechanically applicable ones should be applied so the review can run again. Selects the findings whose correction is a concrete instruction in an applicable discipline, applies the smallest change each names, commits and pushes, and hands the pull request back. It does not review, decide a verdict or merge.
type: skill
clade: engineering
subclade: quality
references:
  - docs/review-findings.md
  - skills/reviewing-diffs/SKILL.md
---

# Applying fixes

A review has run and published its findings. This procedure applies the ones that can be applied without a person, so the review runs again on the result. It writes code; it does not judge it. This repository's `ADR-014` argues why the agent that runs this is not the agent that reviews.

## 1. Fix the facts

Read the repository, the pull request, the base, and the head the review looked at, from the task or from the review's own marker. Collect the findings from the review Argos published — the comment carrying the marker for this pull request, each finding with its discipline, severity, file, line and correction.

If the head has moved since the review, stop: the findings are about a commit that is no longer the tip, and applying them to a different state is guesswork. Say so, and let the review run again first.

## 2. Decide whether anything may be executed

Execution is permitted only when the head is a branch in the same repository as the base, the same test as step 1 of `skills/reviewing-diffs/SKILL.md`. Applying a fix to an external fork's checkout and running its suite would run the author's code on this machine. When the head is a fork, apply nothing, and hand the findings back for the author.

## 3. Select the applicable findings

A finding is applicable when all three hold:

- its severity is `blocking` or `deferrable` — never a `question` or an `unchecked`, which carry no correction that can be made without a decision;
- its correction is a concrete instruction: it names the file, what to replace, and what to replace it with, so applying it needs no choice;
- its discipline is one where applying that instruction changes only what the finding named — `reviewing-sensitive-data`, `reviewing-untrusted-input`, the language reviewers (`reviewing-python`, `reviewing-typescript`, `reviewing-go`, `reviewing-rust`), clean-code, and `reviewing-secrets` under step 5.

Leave every other finding untouched and record why. Architecture, contract and scope findings are not applicable even when their correction reads mechanical, because what they resolve turns on a judgment this procedure cannot make.

## 4. Apply the smallest change each finding names

Work one finding at a time. Apply exactly the correction it states and nothing more: do not reformat the file, rename around the change, or fix a neighbouring fault the review did not raise. A fix that reaches beyond the finding is a change nobody reviewed.

Where two findings touch the same lines, apply them in one edit that satisfies both. Where a correction does not in fact resolve the finding — the state it describes is not what the code does — leave it and record it as not applied, rather than guessing.

## 5. Apply a secret's code change, and flag the rotation

For a `reviewing-secrets` finding, apply the code change: the literal becomes a read from the secret store or the environment, through the module the repository already uses. Then, when the credential reached a commit, record that it is live in history and must be rotated — an action outside the diff that this procedure does not perform and that keeps the change from landing until a person has done it. Removing the line does not resolve the leak.

## 6. Confirm the fix, or say you could not

When execution is permitted and the project declares a test or a check command, run it over the change to confirm the fix compiles and passes. When it does not build, revert that fix and record it as not applied. When no command is discoverable, say the fix was applied and not run.

## 7. Commit, push, and hand back

Commit the applied fixes with a message that names the findings they resolve, and push to the pull request's branch. Do not merge, retarget, approve or comment a verdict.

Hand back the commit, the findings applied, the applicable ones that could not be applied and why, and the secret rotations still open. The review that judges this work is Argos's next run.

## When this skill does not apply

**Reviewing the change.** Reading it for findings, assigning severity and writing a verdict are `skills/reviewing-diffs/SKILL.md` and the discipline skills, run by Argos.

**Landing the change.** Merging a clean, approved pull request is `skills/landing-approved-changes/SKILL.md`, under `ADR-013`.

**A finding that needs a decision.** A `question`, an `unchecked`, or any finding whose correction the author or the organisation must choose is handed back, not applied.

**Writing the change in the first place.** This applies corrections to an existing change under review; it does not author a feature.
