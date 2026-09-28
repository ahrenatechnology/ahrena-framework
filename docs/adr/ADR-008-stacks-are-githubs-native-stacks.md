# ADR-008: Stacks are GitHub's native stacks

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #104
- **Supersedes:** ADR-006

## Context

`ADR-006` read a stack from the chain of base branches and adopted no tool.
That decision rested on a claim made to the owner on 2026-09-26: that GitHub
had no native stacked pull requests, only the base-branch primitive that
third-party tools build on. The claim was out of date. GitHub shipped stacked
pull requests in public preview on 2026-07-30, with the `gh-stack` CLI
extension and an agent skill.

The owner's ask on #58 had been exactly that module: when stacking on GitHub,
activate GitHub's own stacked pull request module. Base-branch chaining was
chosen only because the module was said not to exist. So `ADR-006` recorded a
decision taken on a false premise, and the owner's own intent was never
carried out.

What the module does was measured on stack #103, the first in this
repository (#97, #101, #102), on 2026-09-28:

- A stack is a GitHub object. A pull request carries a `stack` field of type
  `PullRequestStack`, with a number, a base and ordered entries.
- When #97 merged, GitHub retargeted #101 to `main` and rebased it itself. The
  timeline shows `automatic_base_change_succeeded`, then
  `head_ref_force_pushed`, and #101 was left with its own single commit. The
  manual `git rebase --onto` that `skills/stacking-pull-requests` prescribed
  was never run.
- While stacked, #101 and #102 showed an empty `closingIssuesReferences`,
  even after #101's base became `main`. Each still closed its issue when it
  merged: #98 was closed by #101 and #99 by #102.

## Decision

A stack is GitHub's native stack, and it is made and operated with
`gh stack` or on github.com. The framework adopts GitHub's `gh-stack`
extension and agent skill for the mechanics, and adds only its own
conventions on top.

A pull request whose base is not trunk belongs to a GitHub stack. Belonging to
a stack is the declaration: it is the module the owner activates, and there is
no second flag. A pull request off trunk and in no stack has a wrong base, or
is a hand-made chain that should be put in a stack with `gh stack link`.

A stack lands on trunk. Its layers merge through the stack, from github.com or
with `gh stack merge`, never with `gh pr merge` on a single layer.

## Consequences

`hooks/check-stack.py` reads the `stack` field instead of inferring a stack
from bases. The inference `ADR-006` needed, telling a layer from a wrong base
by whether its base branch had an open pull request, is gone. So is its
ambiguity: an unrelated pull request's branch no longer reads as a parent.
The cycle condition goes too, because GitHub's stack is an ordered list and
cannot close into a ring.

The check that a pull request carries no commit that already landed stays.
GitHub rebases a stack's layers when one below them merges, so inside a stack
this condition should never fire. It still catches a branch rebased by hand,
and a pull request built on top of work that landed without being stacked.

`skills/stacking-pull-requests` stops teaching the restack. It keeps what
GitHub's skill does not know about this framework: every layer has its own
issue, its branch is named `type/N-slug` explicitly because `gh stack add -m`
with no name generates a date-and-slug name that fails `branch-naming.md`, its
body closes its own issue, and the stack is merged as a stack.

The framework now depends on a feature in public preview. Its commands, its
API field and its behaviour can change without notice, and the detector reads
a field GitHub has not called stable. When the field changes, condition 1
reports unchecked rather than failing, because a GraphQL error is the forge
not answering. That keeps the gate honest, and it also means a breaking
change would go unseen until someone reads the output.

`ADR-006` stays in the log, superseded, as the record of a decision that was
made on a false premise and corrected.

## Alternatives considered

- **Keep base-branch chaining, as `ADR-006` decided.** Rejected on its
  premise. The module exists, the owner asked for it from the start, and it
  does what the skill made people do by hand: it retargets and rebases layers
  itself.
- **Support both: native stacks and hand-made chains.** Rejected. A chain
  outside a stack gets none of GitHub's retargeting and none of its stack
  merge, which are the reasons to stack at all. Allowing it would keep the
  inference and the ambiguity `ADR-006` needed, for a way of working the
  framework no longer recommends. `gh stack link` turns such a chain into a
  stack in one command.
- **A third-party stacking tool.** Rejected, as before: git-spice is refused
  as maintainer infrastructure (#16). The native module is GitHub's own and
  needs nothing the forge does not already provide.
