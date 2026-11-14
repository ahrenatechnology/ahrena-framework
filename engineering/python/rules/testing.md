---
id: testing
type: rule
clade: engineering
subclade: python
title: Tests that run the code they are about
statement: A test patches no name under a domain or application layer; it doubles the port at the adapter and lets the domain and the use cases run.
enforcement: hook
enforced-by: hooks/check-python.py
references:
  - docs/testing.md
---

# Tests that run the code they are about

One condition, decided by `hooks/check-python.py`. Python makes it unusually cheap to replace any name in any module for the length of a test — `mock.patch` takes a dotted string and swaps whatever is there — and the cheapness is the hazard. A test that patches the function it is meant to exercise, or the domain object the use case under test calls, passes against a replacement and says nothing about the code that ships.

The predecessor's testing law had three parts. This rule carries the one that is about Python. The boundary section places the other two.

**Where the line is drawn, and why there.** The predecessor said mocks belong only at system boundaries — HTTP clients, databases, the filesystem, clocks, external services — and that internal collaborators must not be mocked. Deciding which collaborator is internal needs a layer map, and this plugin has one: condition 2 of [`module-boundaries.md`](module-boundaries.md) names `domain`, `application` and `infra`, and the fundamentals domain-model rule locates the domain by the same directory name. `domain` and `application` are the code a test exists to run; `infra` is the mechanism a test is allowed to replace. The backend plugin's test-first skill draws the same line from the other side: use-case tests stand a double in for each port, and the domain is tested with no doubles at all because it imports nothing to double. A double for a port is a class implementing a protocol, written in the test tree; it is not a patch, and nothing here reads it.

## What the specification says

**Nothing in the specification governs test doubles**, so this rule rests on the library's documentation and on practice. The Library Reference for `unittest.mock`, *Where to patch*, explains that `patch` replaces a name in the namespace where it is looked up, for the duration of the patch — which is why a patch can reach any module, including the one under test. The decision about where the line is drawn is argued above from the layer map, on the premise of a test that runs the code it is about.

## Conditions

Decided by `hooks/check-python.py`, in every file it is given.

1. **No patch reaches a name under a `domain` or `application` layer.** The state is a call to `patch`, `mock.patch`, `mocker.patch`, `patch.multiple` or `monkeypatch.setattr` whose dotted target string has a `domain` or `application` segment; or a call to `patch.object`, `mocker.patch.object`, `monkeypatch.setattr` or `monkeypatch.delattr` whose target expression resolves, through the file's imports, to a module path with such a segment. The test that results runs against a replacement of the code it exists to check, and it keeps passing when that code is broken. The fix is to let the domain and the use cases run, and to double what they depend on at the port: a fake repository, a fixed clock, a recording publisher.

    Not measured, and the reason is stated rather than hidden: the condition is decided by a layer convention, and neither corpus this plugin measures against — the CPython standard library and pip — has a `domain` or an `application` directory, so both return zero by construction. The condition has no threshold for a measurement to justify; what it needs is the layer map, which this plugin already declares.

## Where this stops

**"Every behaviour has a test" is not decided here.** The predecessor required a test for every behaviour change. The framework already decides that from the other end: the contributing plugin's traceability rule requires that every acceptance criterion of the issue a pull request closes be named by a test, which is the version of the requirement a script can check. A Python rule saying it again would be a second source of truth.

**"Tests pass before merge" is not decided here.** That is the pipeline's gate, and the contributing plugin's quality-gate skill is the procedure that runs it. A rule cannot make a suite pass; it can only say the suite ran, and the pipeline already says that.

**Coverage is not required, and no percentage appears.** The predecessor recommended 80% and its quality-gate made coverage a hard gate; its test-strategy document called coverage a signal and not a target. #34 recorded that contradiction and that the 80% was never measured, and the fundamentals simplicity document argues against a hard number on the grounds that a detector that is confidently wrong teaches people to switch the gate off. [`docs/testing.md`](../docs/testing.md) says how to read coverage instead.

**Test isolation and the shape of the suite are #34's.** Order dependence, shared state between tests, the share of unit to integration tests: those are language-agnostic, they belong to group Q1 of #34, and this plugin does not pre-empt them.

**The condition does not read a double that is not a patch.** `MagicMock(spec=FeeSchedule)` handed to a use case in place of a domain object is the same defect by another route, and it is not seen, because a mock constructed and passed is indistinguishable to a parser from a fake. A reviewer reads it.

**A project with other layer names gets nothing from the condition.** The map is the three names `module-boundaries.md` declares; making it configurable would turn the rule into a setting, which is the position that rule already takes. A project that patches into `core/` or `services/` is outside this condition and inside a reviewer's.

**Patching into `application` from a test of an inbound adapter is reported.** A route test that replaces the use case to check status codes is a real pattern, and it is still a test that does not run the use case. The rule takes the backend plugin's position — the API layer's acceptance tests run the whole stack against doubled ports — and the cost lands on a project that prefers the other style: it excludes those test files from the hook's paths and writes down why.

**This rule declares a hook, and its one condition has a script.** The statement reaches no request; `docs/testing.md` is what a writer reads before writing a test.
