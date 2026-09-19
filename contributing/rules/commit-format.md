---
id: commit-format
type: rule
clade: contributing
title: What a commit carries
statement: Every commit carries a Conventional Commits subject of at most 72 characters and a signature on the commit object.
enforcement: hook
enforced-by: hooks/check-commit-message.py
references:
  - docs/contribution-flow.md
---

# What a commit carries

Six conditions, all decided by `hooks/check-commit-message.py`. Each is a state of the stored commit object rather than an opinion about it, which is what lets this rule cost nothing to load and still fire. `docs/contribution-flow.md` gives the provenance of the length threshold, the distribution it was placed against, the three different things "signed" can mean and why this rule checks the weakest of them.

The message and the signature are one rule because they are one object. `git cat-file commit` hands back the headers and the message together, so a single read decides all six conditions and there is no second enforcement point that can disagree with the first.

## The shape

```
<type>(<scope>)!: <description>

<body>

<footers>
```

The scope and its parentheses are optional, and stay optional: 13 of this repository's 24 commits carry one, so requiring it would fail practice that is not wrong, and forbidding it would fail more than half the corpus. The `!` marks a breaking change, as does a `BREAKING CHANGE:` footer; both are the specification's and neither has a condition of its own.

## Conditions

Each of these is decided by `hooks/check-commit-message.py`.

1. **The subject parses as Conventional Commits v1.0.0:** a type, an optional parenthesised scope, an optional `!`, a colon, one space, and a description that is not blank. All 24 commits on this repository's trunk already satisfy it, so this condition describes the practice rather than changing it. There is no threshold: the grammar either matches or it does not.

2. **The type is one of eleven:** `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. Inherited whole from `@commitlint/config-conventional`'s `type-enum`, the same set and the same inheritance as condition 2 of `branch-naming.md`, so a branch and the commits on it are typed from one vocabulary. The script carries the list once per hook and the two hooks read from the same source, which is `@commitlint/config-conventional` rather than each other.

3. **The subject is at most 72 characters.** `git log` indents every line of a message by four spaces, so 72 is the longest subject that still fits a default 80-column terminal without wrapping. That arithmetic is the threshold's whole provenance; it arrives here by way of the predecessor framework's `codex-commit-standards`, which stated 72 without deriving it. It was **not** adjusted to fit this repository: 4 of the 24 subjects on trunk are over it, the longest reaching 76. Raising it to 77 would calibrate the threshold to the corpus's own outlier and break the arithmetic that produced it, which is the move [the engineering plugin's clean-code doc](../../engineering/docs/clean-code.md) refuses when it places a threshold at the bottom of a gap rather than at the top of the data. There is no gap here — the 24 subjects run from 21 to 76 with no empty span — so a measured threshold was not available and an inherited one is stated as inherited.

4. **The subject does not end in a period.** A subject is a title, and a title that ends in a full stop spends a character of a budget condition 3 already found tight. Measured rather than inherited: 0 of 24 subjects on trunk end in one, so this condition describes the practice exactly and costs nothing to keep.

5. **A body is separated from the subject by one blank line.** The state is a second line that is not empty when a third line exists. Every tool that splits a message into subject and body splits on that blank line, so a message without it has one field where it should have two. Measured: 23 of the 24 commits carry a body and all 23 comply.

6. **The commit object carries a signature header.** The state is a header whose name begins `gpgsig` in the stored object. The payload may be OpenPGP, SSH or X.509 and this condition does not read it. This is the weakest of the three things "signed" can mean, it is chosen deliberately, and the next section says what it costs.

## Presence, not verification

Three different properties can be called "signed", and they are not equally available.

| Property | What it needs | Available here |
|---|---|---|
| A signature is on the object | the object | yes, always |
| The signature verifies | `gpg.ssh.allowedSignersFile`, or a keyring, holding every contributor's public key | no |
| The forge marks it Verified | the key registered on an account, plus an API call and a credential | no |

Condition 6 takes the first. The second and third both require key distribution that this framework cannot ship: a gate that fires on everybody who has not yet configured a signer list is a gate that gets switched off, which is the failure mode [`docs/simplicity.md` in the engineering plugin](../../engineering/docs/simplicity.md) argues against, and a hook that needs a token stops being something a consumer can run offline.

**The detector is the header, not `git verify-commit` and not `%G?`.** That is a measurement rather than a preference, and both alternatives were run against a commit known to carry an SSH `gpgsig` header.

`git verify-commit` does not return a verdict at all. On git 2.43.0 with `gpg.ssh.allowedSignersFile` unset it exits 1 having printed `gpg.ssh.allowedSignersFile needs to be configured and exist for ssh signature verification`, which is the tool declining to decide rather than deciding against. A gate cannot read a refusal as a failure without failing every contributor who has not distributed keys.

`%G?` is worse, because it does answer and the answer is wrong. It reports `N` for an unsigned commit and also `N` for that SSH-signed commit — the same letter for "there is no signature" and "there is a signature I was not given the keys to check". A detector built on it cannot tell the two apart, and it would report every signed commit on this repository's feature branches as unsigned.

**What condition 6 does not buy is trust.** A signature by a key nobody has vouched for passes it, and so does a signature over a payload that no longer matches. The condition proves that signing was configured and used, which is the state that is actually missing, and it proves nothing about who signed.

## Where this stops

**20 of the 24 commits on trunk fail condition 6, and the reason is worth knowing.** Every commit written in this project's agent container carries an SSH `gpgsig` header, and those commits still exist with their signatures on the feature branches. The versions that landed on `main` are a rebase's re-authored copies, and a rebase does not re-sign. So the rule cannot be enforced against trunk's history without failing on work nobody can now fix, and it is enforced against a pull request's own commits instead. Stated here rather than discovered: this is a real loss, the fix is a merge strategy this rule does not own, and the condition is worth keeping anyway because it catches the commit that was never signed at all.

**The rule cannot run in a `commit-msg` git hook, which is why its enforcement point is CI.** At `commit-msg` time there is a message file and no commit object, so condition 6 has nothing to read. Splitting the rule so that five conditions fire early and one fires late would create two enforcement points that can disagree, and the one that matters most would be the one that fires last.

**"Atomic" is refused, not deferred.** The predecessor stated it as law — one logical change per commit — and named human review as the tool. It is the most valuable thing anybody could say about a commit and no script decides it, because deciding it means deciding that two edits belong to one intention. The version that is runnable is a threshold on diff size, which fails a large rename and passes a small commit that mixes a fix into a refactor. `docs/contribution-flow.md` carries the question a reviewer asks instead.

**Language and mood are refused for the same reason.** The predecessor required an English subject in the imperative present, and named "commitlint with a custom rule for subject language" as the detector; no such rule existed. Deciding that a subject is English needs a dictionary or a model, deciding that it is imperative needs a parser for English, and either would be wrong about `docs: i18n groundwork`. Both stay in the doc as review questions.

**Breaking changes get no condition.** The specification's two forms both parse under condition 1, and whether a change is breaking is a property of the diff rather than of the message. No commit object anywhere in this repository declares one — not a `!` in a subject, not a `BREAKING CHANGE:` footer, on trunk or on any branch — so there is nothing to measure and nothing to place a threshold against.

**Merge commits are skipped rather than judged.** The state is a commit object with more than one `parent` header; its message was written by whatever performed the merge and it carries no change of its own to describe. This repository contains no merge commits at all today, so the exemption is not a carve-out for something measured — it is a guard against a shape the forge produces, and it is named here so it is not mistaken for one.

**Nothing here reads the description.** A subject of exactly 72 characters saying `feat: stuff` passes all six conditions, and so does one that describes a different change from the one in the diff. Condition 1 checks that the message has fields; only a reviewer checks that they were filled in with the truth.

**The hook reads git and nothing else.** It shells out to `git rev-list` and `git cat-file`, which is not a dependency in the sense the other plugins mean it: the conditions are about commit objects, and a commit object does not exist without git. A repository under any other version control system has no state for this rule to decide.
