# ADR-010: A fork syncs its parent through a merge commit

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #115

## Context

The contributing gates assume that a pull request contains only its own commits.
A fork breaks that assumption each time it takes in its parent's trunk.

barte-ai-services/barte-forge is such a fork. It carries this repository plus a
marketplace entry of its own, and it syncs through a plain `upstream` remote.
GitHub does not record it as a fork: `fork` is false and `parent` is null. Its
first sync, barte-ai-services/barte-forge#6, brought in 16 commits and failed
three gates on content that was correct:

- `commit-format` condition 6: four of the parent's commits carry no signature
  (`7350cb1`, `d413c40`, `3a0ef8b`, `9627488`). They are on this repository's
  trunk already, and signing them would mean rewriting it.
- `traceability` condition 3: the parent's tests name `#99/AC-n`. That is this
  repository's #99, but in the fork it resolves to an issue that does not exist.
- `protected-trunk` conditions 1 and 3: both call for squash only.

A squash is the wrong shape for a sync. It copies the parent's changes as a
single new commit and leaves the merge base where it was. The next sync then
merges the same commits again, from the same old base, and every line both sides
touched conflicts a second time. A merge commit moves the merge base forward, so
each conflict is resolved once.

## Decision

A fork syncs its parent's trunk through a pull request that lands as a merge
commit. The gates judge only what the pull request itself brings. Commits the
parent's trunk already reaches passed the parent's gates when they landed there,
and they are left out.

A repository declares itself a fork by setting the Actions variable
`PARENT_REPOSITORY` to `owner/name`. The declaration is explicit because
GitHub's fork flag is absent for exactly the kind of fork that led to this
decision. With the variable set:

- the workflow fetches the parent's default branch into
  `refs/remotes/parent/trunk`;
- `check-commit-message.py` is given `^refs/remotes/parent/trunk`, so it never
  walks the parent's commits;
- `check-traceability.py` reads the changed tests from the pull request's own
  commits, and counts a merge commit only for the files it resolved;
- `check-trunk.py` leaves `allow_merge_commit` undecided, and accepts a trunk
  commit that is the merge commit of a merged pull request.

## Consequences

A fork can take in its parent with every gate green, and the gates still judge
everything the fork writes itself. That includes the conflict resolution inside
the sync's merge commit.

Outside a fork nothing changes. Without the variable nothing is fetched, and all
three checks behave as before. The suites pin that with #115/AC-5.

A fork's trunk is not linear, and it carries the parent's unsigned history. Both
costs sit with the fork. ADR-001 still holds for every pull request that is not
a sync, and the fork's other merge settings keep their conditions.

The exception is wider than a sync. In a fork, any pull request can land as a
merge commit, because the forge cannot tell a sync from any other pull request.
Reviewers choose the method.

A private parent cannot be fetched with the fork's default token. Such a fork
needs a credential for the fetch step, and this record does not provide one.

## Alternatives considered

- Squash the sync. That is refused for the reason given in Context: every later
  sync would resolve the same conflicts again.
- Rebase the fork's own commits onto the parent and force-push trunk. That
  rewrites a protected trunk on every sync, which `protected-trunk` exists to
  prevent.
- Recognise a fork by GitHub's `fork` flag. It is false for a fork that syncs
  through a remote, and barte-forge is one.
- Keep the gates as they are and have an admin bypass each sync. That makes a
  red check routine, and a routinely red check stops being read.
- Change the fork's own copy of the workflow. That diverges from the parent in
  the one file every sync touches, and turns the fix into a conflict.
