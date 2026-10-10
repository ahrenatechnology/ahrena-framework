---
name: reviewing-secrets
description: Use on every change under review to sweep the lines it adds for a credential - an API key, a token, a password, a private key, a connection string - written as a literal, travelling into a log or a URL, baked into an artefact, or defaulted so the system starts without it. The baseline security discipline; it runs on every authored file.
type: skill
clade: quality
references:
  - docs/review-findings.md
  - docs/review-routes.md
---

# Reviewing secrets

One question, on every change: does a line it adds put a credential where more people can read it than can read the secret store? The party who gains is whoever can read the repository, its history, a build log or an image layer.

The conditions are in `references/conditions.md`, identified `SEC-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

## 1. Take the route

The `secrets` route is a baseline: it fired on every authored file the change touches. Those are the files this skill sweeps — tests, fixtures, examples, notebooks and documentation included, because a credential is pasted into any of them.

## 2. Read what the repository already decides

A green secret-scanning check (a pre-commit hook, a CI scanner, a provider's push protection) decides what it covers, and a condition it already caught is not reported again. Read how the repository reads its own secrets — the module or the environment variables it uses — so the correction names that path.

## 3. Sweep the added lines

Open `references/conditions.md` and read every added line against SEC-1 to SEC-4. Follow a value that looks like a secret from where it is set to every use, because SEC-2 is decided where it travels, not where it is defined.

Read each condition's `Exempt` line: a published test key, a documented public identifier and a fingerprint logged to tell keys apart are correct.

## 4. Write the findings

Each finding carries the four fields in `docs/review-findings.md`, with the `SEC-n` identifier and a correction that is an instruction. A real credential already committed is also flagged for rotation, because removing the line leaves it in history.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A dependency, an image or a pipeline.** That is `reviewing-supply-chain`, the other half of what this discipline used to cover together.

**A secret inside a prompt or an instruction file.** `reviewing-model-use` reads what reaches a model; this reads the credential as a literal in any file, which includes LLM-3's sweep.

**Who may read a datum while it exists.** Storage, logging and transport of sensitive data that is not itself a credential are `reviewing-access`.
