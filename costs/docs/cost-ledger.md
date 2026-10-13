---
id: cost-ledger
type: doc
clade: costs
title: The Cost Ledger
summary: What the cost hook records for a session and for a CI run, how a record is attributed to an issue, how tokens and hours become money, where the ledger and its configuration live, how the pull-request comment is kept, how each of the two installations is wired, and what none of it can tell you.
---

# The Cost Ledger

Almost every change on the platform is built by an agent session, and until this plugin nothing recorded what a change cost. This document is the reference for the three things the plugin does: it **records** a session when it ends, it **reports** per issue, and it **publishes** each pass on the pull request. `skills/reporting-issue-costs` is the procedure for the second; the first and the third run by themselves.

All of the code is in `runtime/`, standard library only. That directory is the plugin's Claude Code runtime hook and what it shares with the report and the CI command. It is not `hooks/`, which in this framework holds the scripts that decide a rule's conditions; this plugin has no rule and so no such script.

## What a record holds

One record per session, one segment per working directory and branch the session spent time in.

| Field | What it is |
|---|---|
| `session_id` | The session, as Claude Code names it |
| `first_event_at`, `last_event_at`, `wall_seconds` | The first and last transcript event, and the time between them |
| `active_seconds`, `idle_threshold_seconds` | Active time, and the threshold it was computed with |
| `turns`, `responses` | Prompts a person sent, and API responses |
| `unfinished_responses` | Responses recorded before they finished, whose output count is a lower bound |
| `subagent_transcripts` | How many sub-agent transcripts were read |
| `segments[].repository`, `.branch` | `owner/name` from the `origin` remote, and the branch |
| `segments[].attribution` | The issue, and how it was found: `branch`, or `unattributed` with a reason |
| `segments[].tokens` | By model, then by kind: `input`, `output`, `cache_write_5m`, `cache_write_1h`, `cache_read` |
| `segments[].active_intervals` | The stretches of active time, so a report can count overlapping sessions once |
| `segments[].key` | A hash of the working directory. The path itself is not stored |

Nothing else is taken from a transcript. No prompt, no response, no tool input or output, no file content, and no path: the working directory is reduced to the repository it belongs to and a hash. `test-record.py` plants text in every one of those places and fails if any of it reaches the ledger; `test-publish.py` does the same for the published comment.

Cache writes are kept as two kinds because they are priced apart: a 1-hour write costs 2x the input price and a 5-minute write 1.25x, and Claude Code uses both. A report shows them as one "cache write" figure and prices them separately.

## How a session is read

The entry format of a transcript is internal to Claude Code and its documentation says it changes between versions. What follows was read from real transcripts written by versions 2.1.281 to 2.1.293, by structure only, and it is what the reader depends on.

**A response is written more than once.** Each content block of an API response is its own record, and all of them carry the same `message.id` and the same `usage`. In a sample of 60 sessions, 9,384 of 19,179 assistant records repeated a response already seen. Summing records would roughly double the count, so usage is folded per message id, keeping the largest value of each counter.

**A sub-agent has its own file.** A session at `S.jsonl` keeps the transcripts of the sub-agents it started at `S/subagents/agent-*.jsonl`, each record marked `isSidechain` and carrying the parent's `sessionId`. The session's own file holds none of their usage. The reader takes every file in that directory, so a session's record covers its sub-agents.

**A sub-agent's output count is a placeholder.** Most records in a sub-agent transcript carry the usage snapshot taken when the response started: `stop_reason` is null and `output_tokens` is a handful. Input and cache counts are right; output is not. The reader cannot recover the true figure from the transcript, so it counts those responses in `unfinished_responses` and every report says the output is a lower bound. This understates cost, and by how much is not knowable from the transcript alone.

**A session moves.** Every record carries `cwd` and `gitBranch`. Half of the sessions sampled touched more than one branch, and one touched 22. Attributing a whole session to the branch it ended on would be wrong half the time, so usage is kept per segment.

**Timestamps are not ordered.** About 4% of records are older than the record before them. Active time is computed over the sorted timeline of the whole session, sub-agents included.

A response is keyed by model id, with a suffix when the price list prices it apart: a prompt over a model's size tier, fast mode, US-only inference. A variant with no entry in the price table is reported as unpriced instead of being priced as the standard one.

## Attribution

In order, and stopping at the first that answers:

1. **The number the branch name carries.** The Forge's convention is `type/issue-slug`, and the expression is the one `contributing/hooks/check-branch-name.py` uses. The two plugins install apart, so it is written twice, and `test-record.py` fails if they drift.
2. **The pull request of the branch, and the issues it closes.** This needs `gh`, so it is done by the report, not by the hook. A pull request that closes several issues is reported under all of them together, as `#12+#15`. Splitting its cost between them would be a guess.
3. **Unattributed**, with the reason: `default-branch`, `no-branch` for a detached checkout, or `no-issue-in-branch-name`. The branch is kept, so a later report can still resolve it.

Nothing is inferred from a prompt, a commit message or a directory name.

## Time

**Wall-clock** is the last event minus the first.

**Active** is the sum of the gaps between consecutive events that are at most the idle threshold. The default threshold is **300 seconds**. A gap longer than that is treated as nobody working: a session left open overnight has a long wall-clock and a short active time.

Active time is the session's, not a person's. One person running four sessions at once produces four hours of active time in one hour of their day. The report takes the union of the active intervals, so within one issue, and in the total, overlapping time is counted once. The rows of two issues that ran at the same time can therefore add up to more than the total.

## Money

**Token cost** is tokens multiplied by the price per million of their model and kind, from `runtime/prices.json`. That file is data: one entry per model with the five prices, the page they were read from and the day they were read. Updating a price is editing that file. A model with no entry is not priced by analogy; its tokens are left out and the report says `no price for model X`.

The table holds Anthropic's first-party API list prices at standard speed and global routing. Token cost is therefore a list-price figure. It is not an invoice, and on a subscription plan it is not what was paid.

**Two rates are configuration, with no default.** The exchange rate to reais, and the hourly rate of a person's time with its currency. A figure that needs one that is missing is reported as `not configured` in text and `null` in JSON, never as zero.

**Development cost** is token cost plus active hours multiplied by the hourly rate. The report shows the three figures apart, in each currency it can.

## Where the ledger lives, and its configuration

The ledger is a directory outside every repository, so it is never committed and is shared by all of them and their worktrees: `$AHRENA_COSTS_HOME`, else `$XDG_STATE_HOME/ahrena-costs`, else `~/.local/state/ahrena-costs`.

```text
sessions/SESSION-ID.json   one record per session, replaced whole on each write
config.json                configuration, optional
errors.log                 what the hook caught instead of failing
locks/                     one lock per session, so two firings run in turn
```

A session's record is one file, written by replacement. Recording the same session again rewrites the same record, so the hook firing many times for one session converges instead of adding up.

| `config.json` key | Environment variable | Default |
|---|---|---|
| `idle_threshold_seconds` | `AHRENA_COSTS_IDLE_SECONDS` | 300 |
| `brl_per_usd` | `AHRENA_COSTS_BRL_PER_USD` | none |
| `hourly_rate` | `AHRENA_COSTS_HOURLY_RATE` | none |
| `hourly_rate_currency`, `USD` or `BRL` | `AHRENA_COSTS_HOURLY_RATE_CURRENCY` | none |
| `publish` | `AHRENA_COSTS_PUBLISH`, `0` to turn it off | on |

A rate that is zero, negative or not a number is treated as not configured.

## The pull-request comment

From the moment a pull request exists for a branch, every pass on it is shown in **one comment**, found by a hidden marker and updated in place. A pass is one run that spent tokens: a development session on somebody's machine, or a run of the pipeline in CI.

Each pass has a stable id: `session:` and the session id for a local session, `ci:` with the run id and the kind for a CI run. Publishing is a merge by that id. The same pass published twice replaces itself and, when nothing changed, writes nothing.

The comment carries its own data. A hidden block holds every pass as JSON, so a publisher with no ledger, which is CI, reads the passes already there, adds its own and rewrites the comment. A missing or malformed block is rebuilt from what the publisher has. The rendered text is recomputed from the passes on every write, with the publisher's price table, so a local pass and a CI pass are priced the same way.

The visible text is Brazilian Portuguese, because that is the language the platform's pull requests are read in. It shows, per pass: when, what kind, who ran it, the models, tokens by kind, active time and token cost; then a total, the cost in reais when an exchange rate is known, the issue the branch is attributed to, every unpriced model, and any pass whose output is a lower bound. It never shows the hourly rate or the cost of a person's time: that is one person's rate, and a pull request is read by everyone with access to the repository.

Where a CI run reports a cost of its own, the cost is still computed from the tokens. The run's figure appears only as a cross-check, when it differs by more than one percent.

## Installing it on a developer's machine

Installing the plugin installs the hook. `.claude-plugin/plugin.json` points Claude Code at `runtime/hooks.json`, which runs `runtime/record.py` on two events:

- **`Stop`**, at the end of each turn, so a pull request opened in the middle of a session gets its comment without waiting for the session to close.
- **`SessionEnd`**, which also catches a turn that was interrupted, where `Stop` does not fire.

`SessionEnd` gives a hook 1.5 seconds, and a plugin cannot raise that. So the hook process hands its input to a detached worker and exits at once; the worker does the reading and the publishing. Every error in either process is caught and written to `errors.log`, and the exit code is always 0.

Publishing from the hook is best-effort. It happens only for a branch the session spent tokens on since its last record, or for every branch of the session at `SessionEnd`; only when `gh` is installed; and only when that branch has an open pull request. Offline, or before the pull request exists, the hook only records. The next pass that can publish merges every pass the ledger holds for that branch, so nothing recorded earlier is lost.

To record a transcript after the fact, into a ledger of your choosing and without touching any pull request:

```sh
python3 runtime/record.py --foreground --no-publish --home /tmp/ledger --transcript PATH-TO-SESSION.jsonl
```

## Installing it in CI

The review pipeline runs Claude through `anthropics/claude-code-action`, whose `execution_file` output is the path of a JSON array holding every message of the run. `runtime/publish.py` reads that file instead of a transcript and publishes the run as one pass. It needs `gh` with a token in the environment and nothing else; it reads and writes no ledger.

The job needs `pull-requests: write`, and this repository's `costs/runtime` directory checked out somewhere, called `$FORGE` below. Then one step, after the step that ran Claude, here with the id `claude`:

```yaml
- name: Publish the cost of this pass
  if: always() && steps.claude.outputs.execution_file != ''
  env:
    GH_TOKEN: ${{ github.token }}
    EXECUTION_FILE: ${{ steps.claude.outputs.execution_file }}
    PR_NUMBER: ${{ github.event.pull_request.number }}
    HEAD_REF: ${{ github.head_ref }}
  run: |
    python3 "$FORGE/costs/runtime/publish.py" \
      --execution-file "$EXECUTION_FILE" --repository "$GITHUB_REPOSITORY" \
      --pull-request "$PR_NUMBER" --kind review \
      --run-id "$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" --branch "$HEAD_REF"
```

`--kind` is `review`, `auto-fix` or `release-train`. The run id is what makes the pass idempotent: the same run and attempt published twice changes nothing, and a second attempt is a second pass. A job that runs Claude twice for the same kind gives each its own `--run-id`. Set `AHRENA_COSTS_BRL_PER_USD` to show reais. A failure prints a warning and exits 0, because a cost comment is never a reason to fail a review; `--strict` makes it exit 1, and `--dry-run` prints the pass and calls nothing.

The tokens come from the `modelUsage` of the run's final `result` message. The Agent SDK documents that field as the per-model total of every call in the run, sub-agents included, and documents the `usage` field beside it as the main loop only, so `modelUsage` is the one read. It gives a single cache-write figure; the part the run's own messages show as a 1-hour write is priced as one and the rest as a 5-minute write. When a run has no `modelUsage`, because it crashed before its result, the assistant messages are summed instead and the pass is marked as a lower bound.

## Where this stops

**Sub-agent output is undercounted in local sessions.** The transcript does not hold it, as described above. CI passes do not have this gap, because `modelUsage` is a total.

**A CI pass was never checked against a real execution file.** The adapter is written from the action's source, which writes the SDK's messages to the file unmodified, and from the Agent SDK's type reference. Run `--dry-run` on the first real file before trusting the numbers.

**The repository of a removed worktree is not always known.** It is read from the `origin` remote of the working directory. A directory that is gone resolves only when it was one of Claude Code's own worktrees, under `.claude/worktrees/` of its repository. The hook fires on every turn, so in practice the repository is recorded while the directory still exists and is kept after; recording an old transcript after the fact is where it goes missing, and those segments appear under no repository.

**A session is attributed where it ran, not where its work landed.** A session on branch A that edits files of another clone is recorded under A.

**Active time is not attention.** It is the time during which the transcript kept moving. A person reading a long answer for six minutes is idle by this measure, and an agent working alone for an hour is active.

**Two publishers can race.** Each reads the comment, merges and writes. If two do so at the same moment, one write can drop the other's pass, or each can create a comment. Two comments are merged into the older one on the next publish. A dropped local pass comes back with the next local publish, because the ledger still has it; a dropped CI pass comes back only if that run is published again.

**The comment has a size limit.** The 40 most recent passes get a row each and older ones are folded into one row. The hidden data still holds every pass, and past roughly a hundred and fifty of them GitHub's limit on a comment is reached and publishing is refused and logged.

**What the price table leaves out.** Fast mode and US-only inference have no entries, so a response under either is reported as unpriced. Server-side tool requests such as web search are billed per request, not per token, and are not counted. Bedrock and Vertex have their own price lists, and none is in the table.

**Passes outside Claude Code and the action are not seen.** A model called from a script, or a session on a machine without the plugin, leaves no record.
