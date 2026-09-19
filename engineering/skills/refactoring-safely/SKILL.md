---
name: refactoring-safely
description: Use when a refactor must change the shape of code and not what a consumer observes: bound the behaviour, get a test that fails when it moves, transform one reversible step at a time.
type: skill
clade: engineering
subclade: quality
references:
  - rules/yagni.md
  - rules/kiss.md
  - rules/clean-code.md
  - rules/duplication.md
  - rules/contract-first.md
  - docs/simplicity.md
  - skills/detecting-contract-breaks/SKILL.md
---

# Refactoring safely

A refactor changes the shape of code and nothing a consumer can observe. Every step here exists to keep that sentence true under pressure, and to reach the question at the end that decides whether the work was worth doing: whether the smell is smaller or merely somewhere else.

[`docs/simplicity.md`](../../docs/simplicity.md) argues the position this procedure carries out — what justifies an abstraction, why the arbitration is asymmetric, and where the thresholds in `rules/kiss.md` came from. It says nothing about how to get code from one shape to the other without spending the behaviour on the way. That is this.

The thresholds themselves are not restated here. `rules/clean-code.md`, `rules/kiss.md` and `rules/duplication.md` declare them, a detector decides most of them, and a procedure that repeated them would be the second place they drift.

Every command in this procedure is language-specific, so the body names none. The Python instance — the baseline, the mutation check, the per-commit gates and a worked example — is in `references/python-instance.md`.

## 1. Name the smell as a condition, and the change it is blocking

Two things written down before a file is opened.

**The smell, as the condition it violates.** A nesting depth over 3, a function body over 30 statements, the third copy of one shape: cited by rule and condition number. Where a detector decides the condition, its output is the citation and the line number is free. "This file is messy" is not a smell, because nothing measures it and step 6 will have nothing to compare against.

**The change the smell is blocking.** A feature that cannot be written cleanly against this shape, a defect that keeps recurring in it, a test that cannot be written because the seam is missing. A refactor with no blocked change is a preference with a commit attached, and the same argument `rules/yagni.md` makes about a speculative abstraction applies to a speculative reshaping of one.

The failure that recurs at this step is naming everything wrong with the file. Take one. Three targets cannot be reverted in one piece and cannot be judged at step 6, which is the same reason the transformations in step 5 are separated.

## 2. Bound the behaviour that must not change

Write down what a consumer can observe today, before anything moves.

The surface each consumer calls, imports or subscribes to. The invariants that hold across it. The failure modes — what is raised, what is returned, what is retried. The ordering and the side effects, which is where this step is usually short by one line: logs something greps, metrics an alert reads, a migration another service queries, a queue another service drains. Performance belongs in the bound when a consumer depends on it and nowhere else; a latency figure nobody has committed to is not observable behaviour, it is a number that moved.

Mark each item **confirmed by a test**, **confirmed by reading**, or **assumed**. The assumed ones are the ones that break, and step 3 is where the important ones stop being assumed.

Then the question that decides whether this procedure applies at all: does the target carry a published surface — a machine-readable contract, an event, an exported symbol set, a shared schema? Reshaping behind one is a refactor. Renaming, removing or narrowing one is not, whatever happens internally, and condition 5 of `rules/contract-first.md` requires it to ship as a version event. Hand that to `skills/detecting-contract-breaks/SKILL.md`, which classifies it against the base version, and either keep the surface fixed and refactor behind it or stop and do the version change as its own change.

## 3. Get a test that fails when the behaviour changes

Run the existing suite first and record that it is green. A suite that was already red cannot tell you what you broke, and finding that out after the first transformation costs the transformation.

Then cover the bound from step 2 at the cheapest level that captures it. These are characterization tests: they record what the code does now, including the parts nobody would design on purpose. A test that asserts the behaviour you wish the code had fails before the refactor starts and is evidence of nothing during it.

**A test that has never failed is not protection.** This is the step that gets skipped, and skipping it is how a refactor proceeds under a suite that watches the wrong thing. Break the target deliberately — invert a comparison, drop a field from a payload, return early — confirm something goes red, and put it back. Do it once per item you marked assumed in step 2 and are now claiming to cover. Coverage is a count of lines executed; it does not claim anything was asserted.

Commit the tests on their own, before the first transformation. They pass against the old code and the new one, which is the whole claim being made, and a reviewer can see they were not written to fit the result.

`references/python-instance.md` gives the commands, the level to write at, and what the mutation check looks like in Python.

## 4. Choose the smallest transformation, and write its reversal criterion

Smallest means the fewest moved lines that stop the condition from step 1 firing. Prefer in this order: rename, then extract, then move, then introduce a type. Each is reversible by the one before it, and each gives step 6 something small enough to judge.

**Do not expand into adjacent cleanup.** The mess next door is somebody's step 1, not yours. Every extra file in the diff is a file whoever reverts this has to reason about, and the reverting happens on the day nobody has time to.

**If the transformation adds an abstraction, it is gated.** An interface, a port, a base class, a registry, a parameter that selects behaviour: condition 1 of `rules/yagni.md` requires a second real consumer, or a test that exists today that requires the seam. Collapsing a third copy satisfies it by construction, and `docs/simplicity.md` lists what people offer instead and why none of it counts — a backlog item, a planned second provider, the observation that the abstraction is cheap.

Then write the reversal criterion beside the choice: what would have to turn out to be true for this to be the wrong transformation, and what reverting it costs once it is merged. A transformation nobody can state a reversal for is not being tried, it is being adopted, and the difference shows up at step 6 when reverting is the answer.

## 5. Run the transformations one at a time, each reversible on its own

One transformation per commit, and the baseline from step 3 green after each.

A red suite after a single transformation means that transformation changed behaviour. **Revert it rather than fixing forward.** A fix stacked on an unverified step buries which of the two was wrong, and the sequence stops being a sequence of known-good states, which is the only property that made it safe.

**Never a structural change and a behavioural change in the same commit.** The value of the sequence is that reverting one commit has a blast radius somebody can state. A commit that moves code and changes what it does has none, and neither half can be kept without the other.

A step too large to verify is two steps. The signal is reaching for a verification that is not the suite: reading the diff and reasoning that it must be fine. That reasoning is what the tests were written to replace.

## 6. Check the smell is smaller rather than relocated

Re-run whatever decided the condition in step 1 and record the before and after. Then ask the thing the count cannot: where did it go?

A smell is relocated when the numbers improve and the reader's work does not. The shapes that do it are specific and they all pass a detector:

- a 60-statement function that becomes six functions only comprehensible read in order, in the order they appear
- a discriminator chain that becomes a registry keyed by the same discriminator, with the branches now in six files and the reader unable to find the third one
- a conditional lifted into a boolean parameter, so the branch happens at the call site with no name on it
- two copies collapsed into one helper with a flag that selects which of the copies you wanted, which is the duplication plus an indirection

In each of them the condition stops firing and nothing is simpler. `docs/simplicity.md` states the cost being paid: every future reader opens two files to learn what one function did, and every future change decides which side of the seam it belongs on.

Three questions, answered out loud rather than assumed:

1. **Can the extracted part be named without "and", "helper", "manager" or "handler"?** A name that needs one is holding two things that were separated by cut rather than by joint.
2. **Does a reader who did not write this reach the answer in fewer hops than before?** Count the hops for the question that brought them here. More hops for the same answer is the relocation, whatever the counts say.
3. **Does the name say what the part does, or where it came from?** `validate_then_persist`, `part_two`, and anything named after the function it was cut out of, are all the seam confessing that it is arbitrary.

If the answer is that the smell moved, revert — step 5 made that cheap and this is what it was made cheap for — and choose a different transformation at step 4. Keeping a result because the count improved is how a corpus fills with structure nobody asked for and nobody can undo. This step has no detector behind it, deliberately, and the final section says why.

## 7. Hand back what changed, what shrank, and what was not checked

Report four things, in this order:

- **The condition from step 1**, with its state before and after, cited the same way both times.
- **The transformations**, in the order they were committed, each with its commit, so the sequence can be walked backwards without reading the diff.
- **The reversal criterion** from step 4, which is now the thing a future reader needs and the only place it is written down.
- **What stayed assumed.** Every item in step 2's bound that no test reached. Name each one rather than omitting it: an unnamed gap reads as coverage, and the next person refactors through it believing the suite has them.

Do not also review the result. A review of this change reads it against the rules from the outside and is `skills/reviewing-diffs/SKILL.md`'s procedure; an author reviewing their own refactor confirms the decision they have already made and publishes it as a second opinion.

## When this skill does not apply

**A change to behaviour.** A bug fix, a new feature, a deliberate change to what is returned or when. Doing it under the word "refactor" destroys step 3: the characterization tests have to be edited to accept the new behaviour, and an edited characterization test is evidence of nothing. Land the behaviour change with its own tests, or refactor first and change second — never the two in one commit.

**A change to a published surface.** Renaming an exported symbol, removing a field, narrowing a type on a contract other people are coded against. Internally behaviour-preserving is not consumer-preserving. `skills/detecting-contract-breaks/SKILL.md` classifies it and condition 5 of `rules/contract-first.md` says what it has to ship as.

**A rewrite.** Replacing a component rather than reshaping it. There is no sequence of small reversible steps between the two implementations, and the existing behaviour is not the specification — it is the thing being questioned. That needs a parallel run, a comparison of the two outputs on live traffic and a cutover, and none of that is here.

**An opportunistic tidy with nothing blocked and the suite already green.** A one-line rename, a dead comment deleted, an import ordered. Step 1 has no answer and the procedure costs more than the change. Make it. If it turns out to need a characterization test, it was never a tidy and step 1 has an answer after all.

**Reviewing a refactor somebody else wrote.** This produces one. Reading one against the rules is `skills/reviewing-diffs/SKILL.md`, and its boundary step — checking each candidate finding against the rule's own `Where this stops` — is the reviewer's equivalent of step 6 and is not this.

**Deciding step 6 mechanically.** This is the one part of the procedure with no detector behind it, and that is a refusal rather than a gap to be closed. `engineering/hooks/check-structure.py` can report that the nesting is now 2 and the third copy is gone. It cannot report that the complexity is now spread across four files that have to be read together, because every mechanical proxy for that — the counts falling, the diff going net-negative, the coverage holding — is satisfied exactly by the transformations the question exists to catch. Encoding it would ship a detector that is wrong about the common case, which is how a gate gets switched off and takes the conditions that were right with it; `rules/kiss.md` records having already paid that once, for the indirection condition it dropped. So it is asked of a reader, and a reader who answers it honestly is the only thing standing between a refactor and a rename.
