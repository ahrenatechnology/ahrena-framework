---
id: script-injection
type: rule
clade: engineering
subclade: devops
title: No contributor-controlled text is expanded into a script
statement: No ${{ }} expression that expands contributor-controlled text (a title, a body, a branch name, a commit message) appears in a run step or a github-script.
enforcement: judgment
references:
  - docs/github-actions.md
---

# No contributor-controlled text is expanded into a script

An expression in a `run:` block is substituted into the script before the shell sees it. When the value is text an outside contributor wrote, the contributor writes part of the script. GitHub's [Script injections](https://docs.github.com/en/actions/concepts/security/script-injections) page lists the contexts to treat as untrusted, those that "typically end with `body`, `default_branch`, `email`, `head_ref`, `label`, `message`, `name`, `page_name`, `ref`, and `title`", and the [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) gives the correction: set the value "to an intermediate environment variable", which the shell then reads as data.

## Conditions

1. **No `${{ }}` expression in a `run:` step, or in the `script` input of `actions/github-script`, reads an untrusted context.** The contexts are the issue, pull request and discussion `title` and `body`; a comment's, review's or review comment's `body`; a commit's `message` and author or committer `name` and `email`; the pull request head's `ref`, `label` and `repo.default_branch`; `github.head_ref`; a page's `page_name`; the `workflow_run` head branch, display title and head commit; and `toJSON(github.event)`. Decided by `hooks/check-workflows.py`, in workflows and composite actions. Also reported by actionlint ("Script injection by potentially untrusted inputs"), zizmor `template-injection` and Scorecard `Dangerous-Workflow`.
2. **A value a contributor controls that reaches a script by any other path is passed through `env:` and quoted.** A step output computed from a title, a `workflow_dispatch` input from a public form, an artifact's content. Decided by review.

## Where this stops

**The list is GitHub's, and it is closed for the hook.** `github.event.repository.name` and `github.event.pull_request.head.sha` are not attacker text and pass. A context outside the list that a contributor can still shape is condition 2.

**An environment variable moves the problem out of the script, not out of the program.** `"$TITLE"` passed to `eval`, or unquoted to a command that interprets it, is injectable again; that is `reviewing-untrusted-input`.

**`with:` inputs to other actions are not read.** An action that builds a shell line from its input is the action's defect; zizmor reads some of them.

**This rule declares judgment because condition 2 needs a reader.** `hooks/check-workflows.py` decides condition 1 exactly, and its tests pin each; the statement reaches the agent's instruction file so the rest is read.
