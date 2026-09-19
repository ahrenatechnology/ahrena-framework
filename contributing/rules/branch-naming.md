---
id: branch-naming
type: rule
clade: contributing
title: The branch name carries its issue
statement: A working branch is named for its conventional type, the number of the issue it answers and a kebab-case slug, joined as type/number-slug.
enforcement: hook
enforced-by: hooks/check-branch-name.py
references:
  - docs/contribution-flow.md
---

# The branch name carries its issue

Two conditions, both decided by `hooks/check-branch-name.py`. Each is a state of a string rather than an opinion about it, which is what lets this rule cost nothing to load and still fire. `docs/contribution-flow.md` gives the provenance of the type set, the five names in this repository that fail, and the flow the branch name is one step of.

## The shape

```
<type>/<issue>-<slug>

feat/38-branch-and-commit-rules
fix/91-null-ledger-total
docs/12-context-budget
```

**The issue number is the part that is new here, and it is the whole point of the rule.** A branch name without it records what kind of change this is and what it is called, and nothing about what it answers. The number is the only field in the name that points outward, and it is what lets a commit, a branch and a pull request be joined to the discussion that produced them without anybody writing the link three times.

It is also the cheapest possible enforcement of issue-first. A branch cannot be named under this rule before the issue exists, because the name needs the number.

## Conditions

Each of these is decided by `hooks/check-branch-name.py`.

1. **The name is a type, a slash, an issue number, a hyphen and a slug.** The issue number is decimal with no leading zero and is not zero, so a number that was padded or invented as a placeholder fails rather than passing as a reference to nothing. The slug matches `[a-z0-9]+(-[a-z0-9]+)*` — the same expression condition 3 of [the foundation's naming rule](../../foundation/rules/naming.md) uses for an artifact name, because a branch name is read in the same places and a second spelling convention is a second thing to get wrong. There is no threshold in this condition: the shape either holds or it does not.

2. **The type is one of eleven:** `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. The set is inherited whole from `@commitlint/config-conventional`'s `type-enum`, which is the list the Conventional Commits specification points at for everything beyond `feat` and `fix`, and it is the same set condition 2 of `commit-format.md` takes so that a branch and the commits on it cannot be typed from two different vocabularies. It was **not** narrowed to the five this repository has actually used — `feat`, `docs`, `ci`, `refactor` and `chore` — because a set closed at five rejects `fix` the first time somebody fixes a bug, and a gate that fails correct work is a gate people switch off.

## Where this stops

**Every branch this repository had before this rule fails condition 1.** All five — `feat/foundation-core`, `feat/cross-plugin-references`, `docs/correctness-and-resource-discipline`, `ci/bump-actions-to-node-24` and the generated `main-3cex9i` — are `type/slug` with no issue number, or worse. The rule changes the practice rather than describing it, and the branches opened for this session's issues, `feat/38-branch-and-commit-rules` among them, are the first names here that pass. The hook's test suite carries the four failing names as cases, so the claim stays true or the tests break.

**One level up the evidence is weaker, and it is stated at its real strength.** Of the seven pull requests opened on this repository, six name an issue somewhere in the body and one — #35, the Node 20 action bump — names only another pull request. So the case that the tie to an issue is routinely lost is not made at the pull-request level. What is missing there is machine-readability rather than the link itself: five of the seven carry no `Closes`, `Fixes` or `Resolves`, so the issue is named in prose and nothing closes automatically. That is a different defect with a different fix, it belongs to a pull-request rule this plugin does not carry, and it is not evidence for this one.

**The number is checked for shape, not for existence.** Whether issue 38 exists, is open, is in this repository or has anything to do with the branch needs the forge's API and a credential. A hook that needs a token is a hook a consumer cannot run offline, and an offline hook is the only kind this framework ships. What is decidable locally is that a number was written down at all, which is the part that actually gets skipped — nobody invents a plausible issue number, they omit it.

**There is no cap on the slug.** The predecessor framework's `lex-git-branches` capped it at 50 characters. Four of the five branch names here carry a slug at all, and those four run from 15 to 35 — `foundation-core` to `correctness-and-resource-discipline` — so no cost has been observed anywhere near 50, and any number between 35 and 50 would be invented, which is the single defect this corpus refuses in a threshold. Git's own limit is real and is a filesystem's, around 255 bytes for a ref path on the common ones, more than six times the longest branch name this repository has had. When a slug ever costs something, the rule grows a cap then, with the case that forced it.

**Trunk, release branches and a detached checkout are outside.** `main`, `master` and anything under `release/` are not working branches, and `HEAD` is what git answers with when no branch is checked out. The hook prints that it has nothing to decide and moves on. Nothing here says whether trunk may be committed to directly; that is a different rule and this plugin does not carry it yet.

**A branch created by machinery this repository does not run would fail.** `dependabot/npm_and_yarn/x`, `renovate/y` and a forge's own `gh-pages` are all real names that condition 1 rejects, and none of them exists here today. They are not pre-exempted, because an exemption list written before the case arrives is a list of guesses; the list grows when the first one appears, with the case that forced it.

**The name is a claim about the work, and the hook cannot check the claim.** A branch called `fix/38-typo` that rewrites a subsystem passes both conditions, and so does `feat/1-x` on a branch that has nothing to do with issue 1. The number ties the branch to an issue; only a reviewer ties it to the right one.
