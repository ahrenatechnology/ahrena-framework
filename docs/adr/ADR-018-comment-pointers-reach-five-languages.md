# ADR-018: Comment-pointers reaches five languages

- **Status:** accepted
- **Date:** 2026-10-19
- **Issue:** #211

## Context

The comment-pointer condition — a comment a change adds or edits points at an ADR
or an issue, or it goes — arrived in this framework for Python alone (#209, #210).
The scope was deliberate: the standard library ships one comment parser, the
plugin takes no dependency, and a `#` inside a Python string is never a comment
because `tokenize` already knows the difference. Reading a second language meant
writing a lexer, and the first step did not.

But the condition was ported from Barte's `check-comments.py`, and that detector
never read Python alone. It carried four readers — the Python tokenizer, a
TypeScript and JavaScript lexer that tracks strings, template literals and
regular expressions, a shell reader for whole-line comments, and a SQL reader for
whole-line comments — each conservative in the same direction: where it cannot
tell a comment from the data around it, it reports nothing, because the fix
deletes what it reports and a deleted slice of a string is a defect the hook
would have authored.

That leaves the framework and its consumer carrying the same decision twice. The
forge keeps its five-language copy and this framework keeps a Python-only one, so
a fix to the rule has to land in two places and the two can drift. A consumer
cannot retire its copy and consume this one while this one reads a fifth of what
its copy does. The owning principle is that a generic, deterministic check lives
upstream and a consumer consumes it; a Python-only check is not yet generic
enough to be consumed.

One part of the Python detector does not generalise. In Python the condition is
the third of three that read a comment — `clean-code.md` condition 3 owns
commented-out code and `debt-markers.md` condition 1 owns a bare debt marker — so
the Python path delegates those two away. Both of those rules are Python-only,
so in the other four languages there is no condition to delegate to.

## Decision

The comment-pointer condition is generalised to five languages — Python,
TypeScript, JavaScript, shell and SQL — by porting the forge's readers up into
`engineering/fundamentals/hooks/check-comments.py`, which reverses the "Python
only" scope the first step set. The hook dispatches by file suffix to the reader
matched to each syntax.

**The readers are ported; the diff machinery is not.** This hook keeps its own
inline `--changed` diff parser rather than importing one from another hook, the
no-dependency constraint the framework places on its detectors. The forge's copy
imports `check-structure.py` for the shared parser because, as a marketplace
consumer, it has that plugin installed beside it; upstream must not take that
dependency, so only the readers, their per-language exemption sets and their fix
logic cross over.

**The Python path is unchanged in behaviour.** It still tokenises, still
delegates commented-out code to clean-code condition 3 and bare debt markers to
debt-markers condition 1, keeps the same pointer set (`ADR-N`, `#N`), the same
exemptions and the same backtick escape. The generalisation adds languages beside
Python; it does not alter Python.

**Outside Python there is no delegation, and still one condition.** Because
clean-code and debt-markers are Python-only, the other four languages have
nothing to delegate to. Rather than invent per-language copies of those two
rules, the pointer rule subsumes the bare debt marker: a `// TODO` with no issue
carries no durable pointer and is no exemption, so it is this condition's finding
directly, while `// TODO (#12)` carries the issue and passes. The outcome a
reader wants — a bare marker reported, an issue-bearing one allowed — is reached
by the one pointer test rather than by a second condition, so the rule keeps
exactly one condition in every language and nothing is judged twice.

**The non-Python exemptions mirror the forge's.** A per-language tool-directive
set, a license header, a shell shebang, the documentation block directly above a
TypeScript or JavaScript `export`, and a separator with no alphabetic word. The
review route that opens the hook is renamed from `python-comments` to
`comment-pointers` and its path pattern broadened to the five languages' suffixes.

## Consequences

The forge can retire its own five-language `check-comments.py` and consume this
one, which is the result the whole change is for: one decision, enforced in one
place, read by every repository that installs the plugin. A sixth language is a
reader and an exemption set added here, not a second copy added downstream.

The framework now maintains three lexers it did not before. They are the proven
ones from the forge, ported with their conservative failure mode intact, so the
cost is reading-and-keeping rather than designing; and each is covered by a
failing fixture and its carve-out in the hook's test.

The non-Python readers under-report by design. Where a reader cannot tell a
comment from a string, it declines the whole file rather than risk a false
deletion, so a pathological file passes silently. That is the right direction to
err for a rule whose fix removes text, and it matches how the Python path already
treats a file it cannot tokenise.

The hook grew, so it carries more rationale that must stay in docstrings: the
PR-scoped self-check runs this detector over the framework's own hooks, and a
bare prose comment added here would redden its own pull request.

## Alternatives considered

- **Keep the condition Python-only.** Rejected. It leaves the forge carrying a
  five-language copy forever and the one decision living in two places, which is
  the exact duplication consuming an upstream rule is meant to end.
- **Write per-language clean-code and debt-markers rules so the delegation
  generalises too.** Rejected as unjustified scope. Those rules' other conditions
  are Python-specific, and the only behaviour the non-Python path needs from
  debt-markers — a bare marker is reported, an issue-bearing one is not — already
  falls out of the pointer test. Three new rules to reproduce one outcome the
  existing test already gives is abstraction with no second consumer.
- **Import `check-structure.py` for the shared `--changed` parser, as the forge
  does.** Rejected upstream. The no-dependency constraint keeps each detector
  runnable on its own; the duplication of the diff machinery is the trade the
  framework has already accepted for its hooks, and this hook keeps it.
- **Detect comments probabilistically, or with a language model, to cover every
  language at once.** Rejected. The rule is a shape in the source, decided the
  same way locally and in CI with no network and no model; a probabilistic reader
  that sometimes deletes a line of a string is worse than one that reads five
  languages exactly and declines the rest.
