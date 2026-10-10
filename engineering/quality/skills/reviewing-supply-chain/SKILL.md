---
name: reviewing-supply-chain
description: Use when a change under review touches a dependency manifest, a lockfile, an image definition, a CI pipeline or registry configuration, and the question is what it lets a third party run - an unpinned or unvetted dependency, a script that runs at install, a pipeline that hands a fork its secrets, an image that ships as root, a known-vulnerable version.
type: skill
clade: quality
references:
  - docs/review-findings.md
  - docs/review-routes.md
---

# Reviewing the supply chain

One question: what does this change let someone who publishes a package, an image or an action run on the machines that build or deploy it? The party who gains is whoever controls something this change will download and execute.

The conditions are in `references/conditions.md`, identified `SUP-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

## 1. Take the route

The `supply-chain` route fired because a manifest, a lockfile, an image definition, a workflow or registry configuration changed. Those files are what this skill reads.

## 2. Read what the repository already decides

A green dependency-audit check, a lockfile policy or an image scanner decides what it covers. SUP-6 in particular is `unchecked` rather than guessed when the repository runs no audit — the review does not recall advisories from memory. Read whether the project pins by digest, commits a lockfile, and has a registry of its own.

## 3. Apply the conditions

Open `references/conditions.md` and read the changed manifest, image and pipeline lines against SUP-1 to SUP-6. Check that a lockfile changed with its manifest. Read a new dependency's registry page and repository before trusting its name.

Read each condition's `Exempt` line: a library's own manifest declares ranges on purpose, and a package the organisation publishes is not an unvetted one.

## 4. Write the findings

Each finding carries the four fields in `docs/review-findings.md`, with the `SUP-n` identifier and a correction that is an instruction. A new dependency nobody can vouch for is a `question` naming who must; an advisory the repository cannot check is `unchecked`.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A credential in any of these files.** The secret sweep (`reviewing-secrets`, SEC-1) runs on every file, this one included.

**The cloud resources, IAM and network a pipeline provisions.** Those are an infrastructure discipline, not this skill, which reads what the build pulls in and runs. When the framework ships that discipline it owns them.

**A tool server an agent file adds from an unpinned source.** That is `reviewing-model-use` (LLM-8), because the risk there is what the model may then do.
