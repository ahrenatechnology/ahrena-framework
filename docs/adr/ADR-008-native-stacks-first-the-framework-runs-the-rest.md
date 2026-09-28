# ADR-008: Native stacks first, and the framework runs the rest

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #104
- **Supersedes:** ADR-006

## Context

`ADR-006` read a stack from the chain of base branches and adopted no tool.
That decision rested on a claim made to the owner on 2026-09-26: that GitHub
had no native stacked pull requests. The claim was out of date. GitHub
shipped them in public preview on 2026-07-30, with the `gh-stack` CLI
extension and an agent skill. The owner's ask on #58 had been exactly that
module: when stacking on GitHub, activate GitHub's own stacked pull request
module. Base-branch chaining was chosen only because the module was said not
to exist.

What the module does was measured on stack #103, the first in this
repository (#97, #101, #102), on 2026-09-28:

- A stack is a forge object. A pull request carries a `stack` field of type
  `PullRequestStack`, with a number, a base and ordered entries.
- When #97 merged, GitHub retargeted #101 to `main` and rebased it itself. The
  timeline shows `automatic_base_change_succeeded`, then
  `head_ref_force_pushed`. #102 was rebased the same way. The manual
  `git rebase --onto` that `skills/stacking-pull-requests` prescribed was
  never run.
- While stacked, #101 and #102 showed an empty `closingIssuesReferences`.
  Each still closed its issue when it merged: #98 was closed by #101 and #99
  by #102.

Native stacks are GitHub's, though, and in preview. The owner's next
direction settled the general case: Ahrena must not depend on the forge
providing them. Where the version-control and work-management tool does not
deliver stacks, the framework delivers them itself, with an agent following
the skill.

## Decision

A stack is the forge's native stack wherever the forge has one. Where it has
none, the framework runs the stack itself.

On a forge with native stacks, a pull request whose base is not trunk belongs
to one. Belonging to a stack is the declaration, and there is no second flag.
The stack is made and merged with the forge's own tools: on GitHub, `gh stack`
and github.com. A pull request off trunk and in no stack, on such a forge, has
a wrong base or is a hand-made chain that belongs in a stack.

On a forge without them, the stack is the chain of base branches, as
`ADR-006` read it. Each layer's base is the branch of an open pull request,
and the chain reaches trunk. The agent does what the forge would have done:
it rebases the next layer past a landed one, and retargets it to trunk.

Which kind a forge has is read from the forge, not configured. A stack of
either kind lands on trunk, each layer through its own merge.

## Consequences

`hooks/check-stack.py` asks the forge's schema whether `PullRequestStack`
exists. If it does, conditions 1 and 2 read the pull request's `stack` field.
If it does not, they check the chain of bases, which is `ADR-006`'s logic
kept as the fallback. A GitHub Enterprise host without the feature, or GitHub
before it, lands in the fallback without anything to set.

The check that a pull request carries no commit that already landed stays on
both paths. In a native stack it should never fire, because the forge
rebases. In a framework-run stack it is the signal that the restack is due.

`skills/stacking-pull-requests` has two paths. The native path defers the
mechanics to GitHub's `gh-stack` and adds only this framework's conventions.
Every layer has its own issue. Its branch is named `type/N-slug` explicitly,
because `gh stack add -m` with no name generates a date-and-slug name that
fails `branch-naming.md`. Its body closes its own issue, and the stack is
merged as a stack. The framework-run path is the procedure the skill had
before this record: chain the bases, land the bottom, restack and retarget
the next.

The native path depends on a feature in preview, and on a field GitHub has
not called stable. When the field changes, conditions 1 and 2 report
unchecked, because a GraphQL error is the forge not answering. The fallback
path does not depend on it at all.

The detector reads GitHub's API on both paths, so on a forge that does not
speak it, all three conditions are unchecked. The skill is still the part
that runs anywhere. On another forge the agent runs the framework path with
that forge's CLI.

`ADR-006` stays in the log, superseded. Its reading of stacks survives as the
fallback, and what is superseded is its claim that there is nothing else.

## Alternatives considered

- **Native only.** Rejected by the owner. It would make stacking unavailable
  wherever the forge does not provide it, and make the framework depend on a
  preview feature of one vendor.
- **Framework-run only, as `ADR-006` decided.** Rejected. Where the forge has
  native stacks, they retarget and rebase layers themselves and merge a stack
  in one operation. Refusing them makes an agent redo by hand what the forge
  already does.
- **A setting that picks the path.** Rejected. The forge's schema already
  answers the question, so a setting would be a second answer that can
  disagree with it.
- **A third-party stacking tool.** Rejected, as before. git-spice is refused
  as maintainer infrastructure (#16).
