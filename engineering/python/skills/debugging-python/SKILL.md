---
name: debugging-python
description: Use when Python misbehaves - a failing test whose cause is not obvious, a traceback from production, a result that is wrong with no error at all, a hang or a task that never finishes. Reproduces the defect as a failing test at the narrowest layer that shows it, isolates the cause with Python's own instruments and a list of the defects Python makes easy, fixes the cause rather than the symptom, and searches the tree for the same defect elsewhere.
type: skill
clade: engineering
subclade: python
references:
  - rules/typing.md
  - rules/error-handling.md
  - rules/immutability.md
  - rules/testing.md
  - docs/testing.md
  - docs/architecture.md
  - docs/logging-and-observability.md
  - skills/writing-python/SKILL.md
---

# Debugging Python

A defect is understood when a test fails because of it. Every step here leads to that test, then to the smallest change that makes it pass, then to the question a fix usually skips: where else the same defect lives.

## 1. Collect what the failure left

Read the bug report, the traceback, the log records and the trace for the request. Read a traceback from the bottom: the last frame is where it raised, and the line `The above exception was the direct cause` or `During handling of the above exception` marks a chained cause that is often the real one. With the trace id from a log record, the trace shows which span failed and what the request carried — `docs/logging-and-observability.md` says what each record should hold.

If what was left is not enough to say which input and which entry point produced the failure, ask the reporter for the exact input, the sequence and the environment before writing anything. A guess at the input produces a test that fails for a different reason.

Output: the entry point, the input, the expected result and the observed one.

## 2. Reproduce it as a failing test

Write a test that drives the entry point with that input and asserts the expected result, following `docs/testing.md` for the layer it runs at, and name the bug's issue in it, `#N` or the criterion's `#N/AC-n`, in the test's name or docstring. Run it. It must fail, and fail with the observed behaviour; if it passes, or fails for another reason, the reproduction is wrong — refine the input or the set-up until it does. When the symptom the report describes cannot be produced in a test — a hang, a slowdown — but a narrower one that explains it can, reproduce the narrower one, and say in the hand-back how it accounts for the reported symptom.

Then move the test down, when the defect lives in a layer below the entry point. If it lives in a domain rule, a unit test with no I/O reproduces it in milliseconds and every later step runs faster for it; `docs/architecture.md` says which layer owns which kind of code. Keep the outer test too: it is the one that proves the report is answered.

Output: the failing run — the command and the assertion that failed.

## 3. Isolate the cause

Follow the wrong value backwards from the assertion to the line that produced it: where was it computed, from what, and which condition was not what the code assumed? Python's own instruments do most of this:

- `breakpoint()` at the suspect line, and `pytest --pdb` to stop at the failure with the frame live.
- `python -X dev`, or `-W error`, so a `ResourceWarning`, a `DeprecationWarning` or a never-awaited coroutine becomes an error at the line that caused it.
- `PYTHONASYNCIODEBUG=1` for async code, which reports a callback that blocked the loop and a task destroyed while pending.
- `git bisect run` with the failing test, when the defect is a regression and the tree once passed it.

Then read `references/suspects.md`, the defects Python makes easy, against the code on the path. Several of them are decided by the plugin's hooks; run `check-typing.py` and `check-python.py` on the files on the path, because a finding on that path may be the defect itself.

Output: the cause, in one sentence that names the line and the condition that was false.

A rule's escape — the reason comment `rules/error-handling.md` or `rules/security.md` accepts — is not a fix for the defect being diagnosed. If the hook that found the cause offers one, the fix is still the change to the line.

Stop here and escalate to a person, before any fix, when the cause has corrupted stored data, exposed a secret or personal data, or crosses into another service: each of those needs a decision before a change. Hand back the cause and the failing test.

## 4. Fix the cause

Change the line that produced the wrong value, not the line that noticed it. A `try`/`except` added around the symptom, a default returned where the value was wrong, a retry around a deterministic failure: each makes the test pass and leaves the defect. The fix is written under `skills/writing-python/SKILL.md` step 5, so it does not introduce what the rules forbid while removing what they missed.

Keep it minimal. Reshaping the surrounding code is a separate change, after this one lands.

## 5. Verify

The failing test now passes; the full suite still passes; `mypy --strict`, the plugin's four hooks and the fundamentals structure hook report nothing new on the changed files. Then reread the original report and check the fix answers it — the test proves what the test asserts, and the report may have said more.

Output: the green run, and the hooks' last lines.

## 6. Look for the same defect elsewhere

A defect that was easy to write once was written more than once. Search the tree for its shape: run the hooks over the whole tree when it is one they decide, and search for the pattern when it is not — the same call, the same handler, the same assumption about a value. Fix each occurrence the same way, with a test where one is cheap; where an occurrence belongs to other work, name it in the hand-back for the caller to open an issue, rather than leaving it in a comment.

Then ask what would have caught this one before it shipped: a stricter type, a rule's escape that should not have been used, a test at a layer that had none, a hook condition the defect's shape could become. Name it in the hand-back.

## 7. Hand back

The cause in one sentence, the failing run and the green run, the occurrences found in step 6 and what was done with each, and the guardrail proposed.

## When this skill does not apply

**A behaviour that was never built.** A missing feature reported as a bug is new behaviour, written by `writing-python` against a criterion.

**A failure outside Python.** A database that refuses connections, a network that drops them, an infrastructure limit: the trace will point there, and the fix is not in this code.

**Reviewing a change for defects nobody has hit yet.** That is `reviewing-python`.

**A test that fails only sometimes.** Ordering, shared state and timing between tests are #34 group Q1's isolation subject; this procedure applies once the failure is reproducible, and the first step for a flaky test is to make it so.
