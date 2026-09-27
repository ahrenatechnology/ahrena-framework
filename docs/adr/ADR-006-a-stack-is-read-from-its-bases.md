# ADR-006: A stack is read from its bases

- **Status:** accepted
- **Date:** 2026-09-27
- **Issue:** #58

## Context

#58 asked for stacked pull requests and for the reviewer to handle a stack. The
predecessor had six artifacts for it, 1,523 lines, one of them a 321-line guide
to git-spice, which this repository already refuses as maintainer
infrastructure (#16).

The owner settled three things on #58 on 2026-09-26, recorded there as a
comment and promised a record when the rule landed. Stacking is a mode, not a
mandate. The stack is read from base-branch chaining, tool-agnostic. And the
mode is detected, not declared: no flag. The last choice left a question open,
which the owner named in the same comment: how is a stacked pull request told
apart from one opened against the wrong base? Both are a pull request whose
base is not trunk.

#58 also named a collision. #45's planning work and stacking both want a
checklist for when one change becomes several, and the predecessor built it
twice and the two drifted.

A third fact came from the merge method. `ADR-001` lands every pull request as
a squash. When the bottom of a stack lands, trunk gets one new commit and the
next layer still carries the bottom's original commits. Measured on
2026-09-27: the commits on #79's branch are still returned as belonging to #79
by GitHub's commits-to-pulls association after #79 landed as the single squash
`75481ca`. So the stale layer is detectable.

## Decision

A stack is read from the chain of base branches that GitHub records, and from
nothing else. The framework adopts no stacking tool, asks for no flag, and
writes no stack metadata into pull-request bodies.

A pull request whose base is not trunk is a layer when its base is the branch
of an open pull request in the same repository. Its base being the branch of a
merged pull request means it must be retargeted and restacked. Its base being
the branch of a closed, unmerged pull request means it sits on abandoned work.
Its base being the branch of no pull request means it is a wrong base, not a
stack.

A pull request carrying any commit already associated with a different merged
pull request fails, stacked or not. That is the one failure squash and stacking
produce together.

The decomposition checklist belongs to the planning work in #45, which
`ADR-004` gives a sub-issue. Stacking cites it and does not carry one.

## Consequences

`contributing/rules/stacked-pull-requests.md` decides all of this through
`hooks/check-stack.py` in the forge tier of `ADR-002`, and
`skills/stacking-pull-requests` gives the order of operations with `git` and
`gh` alone. `engineering/skills/reviewing-diffs` step 1 reviews a layer against
its parent.

A repository that never stacks pays one API call per commit on every pull
request, for condition 3. That is the cost of catching the stale layer without
a flag, and it is paid whether or not anything is stacked.

The rule arrives before the practice. No pull request in this repository had
ever been stacked when it was written, so its conditions come from GitHub's
mechanics, and the first real stack is its first real test.

Detection leaves one ambiguity a declaration would not. A branch that is the
head of an unrelated open pull request reads as a parent. Every working branch
here carries its own issue number, which makes the accident unlikely, and the
rule says so rather than claiming it cannot happen.

Restacking is manual. After the bottom lands, the next layer has to be rebased
past the landed commits and pushed with `--force-with-lease`. A stacking tool
would do this in one command. The skill does it in three, and the framework
takes that cost over adopting a tool.

## Alternatives considered

- **Adopt a stacking tool, git-spice or Graphite.** Refused twice over. git-spice
  is already refused as maintainer infrastructure, and the owner chose to read
  the chain rather than depend on any tool. A consumer using a tool still
  passes, because every tool produces the chain the rule reads.
- **A flag declaring stack mode.** Refused by the owner on #58. A declaration
  removes the ambiguity with the wrong base. It also adds a setting every
  consumer has to know about before stacking works, for a mode most never use.
- **Stack metadata in each pull-request body.** Some tools write a list of the
  stack's layers into every body. It is a second record of what the bases
  already hold, and it goes stale on every restack.
- **Decomposition owned by stacking.** Rejected. A plan decides how a change
  splits, and a stack is one way of carrying out the split. Owning the
  checklist here would build it a second time beside the plan, which is how the
  predecessor's two copies drifted.
