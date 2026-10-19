---
id: review-routes
type: doc
clade: quality
title: How a review selects its skills
summary: Why the skills a review loads are chosen by a route table and a script, what the three drivers of a route read, what a baseline route and an unrouted path mean, and how a route is added.
references:
  - docs/review-findings.md
  - ahrena-engineering-fundamentals:docs/simplicity.md

---

# How a review selects its skills

This is the companion to step 2 of `skills/reviewing-diffs/SKILL.md`. That step runs `hooks/route-review.py`; this says what the script reads, why it is a script, and what its output does and does not claim.

[`docs/review-findings.md`](review-findings.md) argues why a review routes at all: reading every rule against every diff examines nothing closely. The same argument holds one level up. A reviewer with a skill for security and a skill for prompts, loading both on a change to a build script, spends its attention on conditions that cannot fire.

## A route is data

The table is `skills/reviewing-diffs/references/routes.json`. One route is one object.

| Key | What it holds |
|---|---|
| `id` | the route's name, unique in the table, and what a skill's own step 1 looks for |
| `skill` | the skill the route selects, plugin-relative, or `plugin:path` for a skill in another plugin |
| `opens` | the files that skill reads for this route: a rule, a checklist in its `references/`, a detector |
| `why` | one sentence, for the person reading the table |
| `paths`, `lines`, `contains` | the drivers, each a list of regular expressions |
| `baseline` | `true` on a route that reaches every file |

**The table is the only place a pattern lives.** A skill's step 1 lists route identifiers and what each opens. It does not repeat an expression, so there is one place to edit and nothing to drift.

## The three drivers

A route fires on a changed file when every driver it declares matches. Within one driver, any expression in the list is enough.

**`paths` reads the file's path.** This is the cheap driver and most routes need no other. A migration directory, a manifest's filename and an instruction file's name are all decided here.

**`lines` reads the lines the change adds.** A path cannot say that a Python file now calls a model or builds a query from text, and those are the changes the security and prompt skills exist for. The driver reads added lines only: a call that was already in the file is not this change's, and firing on it would send every later edit of that file through a review it does not need. The output names the first line that matched, so the skill starts reading where the route fired.

**`contains` reads the whole file at the head.** It is for a fact about what the file is and not about what changed. The one route that uses it tells an artifact of this framework from any other markdown file under `agents/` by the `clade` field in its frontmatter.

Expressions are Python's `re` syntax and are searched, not anchored. A deleted file has no added lines and no text, so it can fire a route that declares `paths` alone, which is what a removed contract needs.

## Why regular expressions and why a script

The route table this replaces was a column of prose: "any handler, client or job entry point". Two readers classify that differently, and one reader classifies it differently on two days. The reviews then differ before either has read a line.

A regular expression is wrong in a fixed way. A file the pattern misses is missed every time, somebody notices, and the table gets a line. That is the trade [`docs/simplicity.md`](../../fundamentals/docs/simplicity.md) argues for elsewhere: a detector that decides less, and decides it the same way twice.

The script exists so that the table is applied and not paraphrased. It prints which routes fired and on what, which makes the selection something a second reader can check against the diff.

## A driver says where to look

A route firing is not a finding and not a suspicion. The line driver for untrusted input matches every call to `open(`, and nearly all of them are fine. What the route buys is that the checklist for paths is open when the reviewer reads that line, and closed when the change contains no such line.

The cost runs both ways and is accepted in one direction only. A driver that is too wide loads a checklist that finds nothing, which costs attention. A driver that is too narrow skips a checklist that would have found something, which costs a missed finding. The line drivers are written wide for that reason.

## Baseline routes and unrouted paths

A baseline route fires on every file that is not ignored. The secret sweep is the one the table ships: a credential can be pasted into any file type, so no path pattern is right for it.

A baseline does not count as coverage. A path that only a baseline reaches is printed as `unrouted`, and the review says so. A changed `Makefile` was swept for a credential and read against nothing else, and a reader of a clean review should know that.

Paths matched by `ignore` select nothing, the baseline included: lockfiles, vendored and built directories, minified bundles, snapshots. They have no authored lines.

## Adding a route

Add one object to the table, and when it opens a new file, write that file. `hooks/test-route-review.py` fails on a route that names a skill or a file that does not exist, on an expression that does not compile, and on a route with no driver.

A new review skill needs no change to the router and none to the agent's procedure: its routes select it. Its own step 1 lists the route identifiers it answers to.

## A plugin declares its own routes

A core route is for a lens every consumer wants. A consumer, or a plugin installed into one, has lenses of its own: a route for its SQL, its Terraform, its own contract files. Editing the core table to carry them is drift — the consumer's table and the framework's diverge, and the next framework change to the table has to be merged by hand.

So a plugin that adds review lenses ships a **fragment** instead: a file `review-routes.json` at the plugin root, itself a `{routes, ignore?}` object, the same schema as the core table. Its routes' `skill` and `opens` are `plugin:path`-qualified, the cross-plugin reference form the rest of the framework uses, so a lens the fragment selects is loaded exactly like a core one. The merged routes feed the same review-findings set; a consumer's lens is not a second class of route.

**The router merges the installed fragments with the core table at runtime.** Discovery is explicit — the router scans no directory:

| Source | What it names |
|---|---|
| `--plugin-routes <file>` | one fragment; repeat the option for several |
| `ROUTE_REVIEW_FRAGMENTS` | an `os.pathsep`-separated list of fragment files |

The two sources are collected together and de-duplicated by resolved path. The **effective table** is the core table first, then the fragments in a canonical order — sorted by resolved path — so the order they are supplied in cannot change the result. `ignore` is the de-duplicated union of the core's and the fragments'. A route `id` must be unique across the core and every fragment: a collision is an error (exit 2, naming the id), so **no fragment silently overrides a core route**. A fragment that cannot be read or is malformed is the same error as a malformed core table (exit 2, naming the fragment).

With no fragments — no flag, the env var unset or empty — the output is byte-for-byte what it was before fragments existed. `--routes` still replaces the core table; fragments merge on top of whichever base is in effect.

## Where this stops

**The router does not read meaning.** Whether a file is "a handler" is decided by its name and directory. A handler in a file called `process.py` at the root is reached by the source route and not the edges route. The `unrouted` list and the fallback to the language-agnostic rules are what keep that miss visible.

**It does not decide severity, order or verdict.** It selects what is read. Everything after that is the skills'.

**It is not a security scanner.** A line driver that matches `password` is not reporting a password. Treating the router's output as findings would publish dozens of them on an ordinary change, and would teach the author to ignore the review.

**It does not replace reading the description.** A change whose paths and added lines look like a refactor and whose description says it changes who may approve a payment needs the access checklist. The reviewer may open a skill no route selected, and says in the review that it did and why.
