---
id: comment-ratio
type: rule
clade: engineering
subclade: quality
title: Comments stay a small share of the code
statement: From 20 added code lines, a change's comment lines stay below 10% of its code lines; the code explains itself.
enforcement: judgment
---

# Comments stay a small share of the code

One condition, a ratio over the diff. [`comment-pointers.md`](comment-pointers.md) decides whether each comment is allowed; this rule decides how much of a change is comment. A change can pass the first and fail the second by carrying forty pointer-bearing comments in a hundred lines.

## Conditions

1. **CLN-9. Comment lines divided by code lines, in the lines the diff adds, is below 0.10, from 20 added code lines.** A line holding code and a trailing comment counts once as code and once as comment. A line that is blank, holds only a brace or an import, or holds an exempt comment (shebang, coding declaration, license, directive, separator) is neither. A documentation block above an export counts as comment; a Python docstring is a string and does not, as in `comment-pointers`. Below 20 added code lines the ratio is reported and does not fail. Threshold: 0.10, declared maintainer policy recorded under #34. Detector: a script that counts the two kinds of added line in the diff, over the whole diff and not per file; the TypeScript detector is owned by the clean-code detectors issue #330.

## How this composes with comment-pointers

The two conditions judge different things and never the same line twice. `comment-pointers` condition 1 asks of each added comment: does it point at an ADR or an issue, or is it an exemption? CLN-9 asks of the whole diff: how many comment lines are there? A comment must pass both. A comment that points but pushes the diff past 0.10 is a CLN-9 finding for the diff, and the fix is to delete the comments that restate the code, not to remove their pointers. Exempt comments (shebang, coding declaration, license, directive, separator) are not counted by CLN-9, since they are not prose, so adding a license header never fails the ratio. A change with no code lines added has no ratio and passes.

## Where this stops

**It is a ratio, not a verdict on any comment.** A diff at 0.08 can still hold a comment that lies; staleness is not decided here or in `comment-pointers`.

**A tiny diff gives a noisy ratio.** Three code lines and one comment is 0.33. The condition applies from 20 added code lines; below that, the reviewer reads the comment itself, and the number is reported without failing.

**It does not reach documentation files.** A Markdown file is all prose by nature; only source files in a language the detector reads are counted.

**This rule declares judgment because no detector ships yet.** It moves to `hook` in the change that lands the script.
