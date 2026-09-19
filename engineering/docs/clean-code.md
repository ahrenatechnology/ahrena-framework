---
id: clean-code
type: doc
clade: engineering
subclade: quality
title: The readable surface and what it costs to keep
summary: Where the 30-statement threshold came from, why dead code and commented-out code are one defect with two detectors, why naming is not in the rule, and what a reviewer asks instead.
references:
  - rules/clean-code.md
  - docs/simplicity.md
---

# The readable surface and what it costs to keep

This is the companion to [`rules/clean-code.md`](../rules/clean-code.md). The rule states three conditions and names what decides each one; this explains what they are protecting, where the one number came from, and the two conditions that were considered and are not in the rule.

"Clean code" is usually taught as a list of virtues. A list of virtues is what makes it useless in review: every item is agreeable, none is decidable, and two reviewers reach opposite conclusions about the same function without either being able to say why. What follows is the readable surface reduced to states a script can detect, plus an honest account of the part that cannot be.

## Function size

**What it prevents.** The function nobody can hold in their head, and the change that therefore gets made by pattern-matching rather than by reading. A reader working through a long function is simulating it; past some width of state that simulation stops being reliable, and after that point every edit to the function is a guess that happened to work.

**The detector.** A statement count over the function's own body and the bodies of the control-flow statements inside it, with the docstring excluded and a nested definition counted as one statement rather than descended into. Statements rather than lines, because lines are the formatter's output: a line-based threshold moves when someone changes the column limit or expands a call across four lines, and a statement-based one does not.

**Where the 30 came from.** It was measured, then cross-checked against a source, and it is the top of a gap rather than a round number.

Run over every function in the framework's own Python as it stood when the rule was written — 61 functions across 2,291 lines in the two plugins' hook scripts, their test suites and the two hook templates — the distribution is:

| | Statements |
|---|---|
| median | 8 |
| 75th percentile | 12 |
| 90th percentile | 20 |
| 95th percentile | 26 |
| the seven largest, in order | 17, 20, 23, 25, 26, 26, 26, 41 |

There is nothing between 26 and 41. Everything at 26 and below is a function somebody has been content with, and there are three of them sitting at exactly 26; the single function above the gap is `parse_frontmatter` in the foundation gate, at 41, which is the one function in the corpus a reviewer would already have questioned.

This is the method `rules/progressive-disclosure.md` used to place its 10-line cap on code blocks: put the threshold in the empty span between current practice and the thing you are trying to catch, so it fails nothing that exists and cannot be reached without a genuine change of kind.

**Thirty is the bottom of that span rather than the top, and the choice is the interesting part.** Anything from 27 to 40 fails exactly one function today, so the measurement alone does not pick a number inside the gap. Thirty sits four statements above everything the corpus has been content with — enough headroom that an ordinary function cannot drift into the finding — and ten below the outlier. Taking 40 instead would also fail nothing today, and it would be a threshold calibrated to the defect rather than to the practice: it would license every function in the corpus to grow by half again before anything noticed.

The cross-check is the Linux kernel coding style, which puts a function at "one or two screens of text" on an 80-by-24 terminal, so 24 to 48 lines. Thirty statements sits inside that band. Martin's *Clean Code* argues for far shorter, "hardly ever 20 lines", and the rule deliberately does not take that number: 20 is the corpus's own 90th percentile, so a threshold there would fire on six functions nobody has complained about, and a gate that fires on ordinary code gets switched off. `docs/simplicity.md` records the condition that was deleted for exactly that reason.

**Where it stops paying.** On data. A lookup table written as consecutive assignments, a fixture builder and a generated constant block all accumulate statements without asking the reader to follow anything, because there is no control flow to simulate. Splitting them into three functions makes the table harder to read, not easier. Move them to module level where they read as data, or exclude the file.

It also stops on the arrangement question, which is the more common defect. A 20-statement function interleaving four concerns is worse than a 30-statement function doing one thing in sequence, and no count tells them apart. The threshold catches the functions that are too big to hold; it will never catch the ones that are merely badly arranged, and a reviewer who treats a passing count as an answer has used it wrong.

## Dead code, in the two forms a reader meets

Dead code is one defect and it arrives in two shapes, which is why the rule carries two conditions rather than one.

**Unreachable code** is a statement after an unconditional exit in the same block. It is a definition rather than a threshold: there is nothing to tune and nothing to argue about. It is also nearly always the visible end of a real bug — an early return added during a fix, with the code it displaced left behind — so the finding is usually worth more than the deletion it asks for.

**Commented-out code** is the other shape, and it is the one people defend. The defence is that the code might come back. It might, and version control is where it is: the deleted version is one `git log -S` away and it is guaranteed to be the version that actually ran, while a commented block rots silently against every refactor that goes past it. A reader meeting one has to decide whether it is documentation, a plan, or a mistake, and there is nothing in the file that tells them.

**The detector, and why it is safe.** A comment is commented-out code when its text parses as a Python assignment, augmented assignment, `return`, `raise`, `import`, `del`, `assert`, `global`, `nonlocal`, or a bare call expression. Tool directives are excluded by prefix, because `# type: ignore` parses as an annotation and `# noqa` parses as a name.

The restriction to that statement list is what keeps it quiet. English prose almost never parses as Python: two adjacent nouns are a syntax error, and a single word parses only as a bare name, which is not on the list. Run over 1,700 lines of the framework's own unusually comment-heavy Python it produced zero findings, and against a fixture of six commented-out lines mixed into ten lines of prose about code it found all six and none of the ten.

**The form that is not in the rule.** The third shape of dead code is a symbol defined and never used — an unreferenced function, class, constant or import. It is a real defect and it is out of reach here, because deciding it needs every module that could import the symbol, and this detector reads one file at a time. A single-file version would flag every public function in a library. Whole-program linters do this well and a project should run one; what the rule will not do is ship a version that is wrong about the most common case.

## Comment hygiene, beyond the one mechanical case

The rule catches one comment defect. The expensive ones are all judgment, and naming them is more useful than pretending otherwise.

**The stale comment** describes behaviour the code no longer has. It is worse than no comment, because a reader who trusts it stops reading the code. Nothing mechanical detects it: the comment and the code are both well-formed and only a human knows they disagree. The mitigation is structural rather than detective — a comment that explains *why* survives a refactor, and a comment that restates *what* is invalidated by every one of them.

**The restating comment** repeats the line below it in English. It costs a line and buys nothing, and it is the one people write when they have been told to comment their code. The test is whether deleting it loses information; usually a better name for the thing below would have carried everything the comment did.

**The comment that should have been a name** is the interesting case, because it is a real finding with a real fix. A comment introducing a block inside a function is marking a section, and a section of a function is a function. Extracting it replaces the comment with a name that the compiler checks and the call site reads.

## Why naming is not in the rule

The rule owns names in its title and refuses them in its conditions, and that gap is deliberate rather than an omission to fill later.

Every naming defect worth catching needs something a parser does not have. A name that lies needs to know what the code does. A name abbreviated past recognition needs a dictionary and the domain's vocabulary. A name whose length does not match its scope needs a judgment about how far the reader has to carry it — and the underlying convention, that scope and name length rise together, is a guideline with no threshold in it.

What is left for a script is the class of shape rules that look mechanical and are not: banning `data`, `info`, `temp`, `manager`, `helper` and `util` by list. A list like that is wrong in both directions at once. `data` is the correct name for the payload of a parser, and a `TemplateManager` that manages templates is named accurately. Meanwhile the worst names in any codebase — the ones that are plausible, specific and false — are not on any list and never will be.

`rules/naming.md` in the foundation plugin takes the same position about skill names and says so plainly: its gerund check is a suffix test that catches the mistake that actually happens, and closing the remaining gap would need a dictionary the hook will not take a dependency on. The same reasoning applies here with more force, because code has a vastly larger vocabulary than a corpus of artifact names.

**What a reviewer asks instead.** Three questions, in order, and each of them has an answer the author can act on:

1. Read the name and say what you expect the thing to do. Then read the body. Where the two disagree, one of them is wrong, and it is usually the name.
2. Take every abbreviation and ask who else in the codebase uses it. An abbreviation that appears once is a private shorthand; one that appears throughout the domain is vocabulary and should stay.
3. For a name that is generic, ask what would have to be added to make it specific. If the answer is nothing, because the thing genuinely is a bag of unrelated data or a collection of unrelated operations, the name is honest and the *type* is the defect — which is condition 1 of `rules/solid.md`, not this rule.

## What the detectors cost, measured

The claim that these three conditions are low-noise is checkable, so it was checked. Run over the 2,291 lines of framework Python described above:

| Condition | Findings |
|---|---|
| a function body over 30 statements | 1 |
| a statement after an unconditional exit | 0 |
| a comment that parses as code | 0 |

The one size finding is `parse_frontmatter` at 41 statements, and it is a true positive: it opens a frontmatter block, scans for the close, then runs a nine-branch state machine over the lines between, and the state machine is the function hiding inside it. It sits in the foundation plugin, so this slice records it rather than fixing it.

The third condition produced nothing across a corpus whose comments are unusually dense and unusually prose-like, which is exactly the case that breaks a naive detector. Against a fixture of sixteen comments — six commented-out lines and ten lines of prose *about* code, including `# Usage:`, `# type: ignore`, and a sentence naming a function and its arguments — it found the six and none of the ten. That fixture is `SIXTEEN_COMMENTS` in `hooks/test-check-structure.py`, so the claim is a test rather than a recollection.

One true positive and zero false positives across 2,291 lines is the profile `docs/simplicity.md` records for the KISS and SOLID detectors, and it is the standard a condition has to clear before its rule is worth a gate.

## Where this stops

**This document does not teach clean code from scratch.** It assumes the reader knows roughly what the practice claims and needs to know what this framework will hold them to. Martin's *Clean Code* and Kernighan and Pike's *The Practice of Programming* are the sources behind the material here and neither is reproduced.

**It does not cover duplication.** Duplication is the other half of what "clean code" usually means and it is a different question, decided by a different predicate: the rule of three, not a size threshold. `rules/duplication.md` states it and `docs/duplication.md` explains it, including the threshold measurement, which follows the method in this document and had to borrow a control corpus because the framework's own Python contains no duplicated bodies to place a floor against.

**It carries no worked examples outside Python.** The three conditions are stated in language-neutral terms and the one shipped detector parses Python, because the Python standard library contains a Python parser and nothing else. Detectors for other languages belong with the plugins that may take a parser dependency.

**It says nothing about formatting.** Indentation, line length, import order and quote style are decided by a formatter that runs without argument, and a framework that has opinions about them is competing with a tool that already won. Every condition here is deliberately invariant under reformatting, which is why they count statements and parse comments rather than measuring lines.
