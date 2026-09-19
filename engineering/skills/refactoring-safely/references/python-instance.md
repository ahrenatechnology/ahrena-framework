# The Python instance

The procedure is language-agnostic; the commands are not. This is what each
step is in Python, and one worked example. Nothing here changes the steps —
where this file and `SKILL.md` appear to disagree, the step is right.

Adjust the commands to what the project actually declares. A project that
runs its suite through `tox`, `nox`, `make test` or a task runner has already
decided; using a different invocation here means the refactor is verified
against a configuration nobody else runs.

## Step 1 — the smell, as a condition

The detector that ships with this plugin decides most of them and prints the
file, the line and the rule, which is the citation step 1 asks for:

```sh
python3 engineering/hooks/check-structure.py path/to/target.py
```

Pass the target, not the tree. A whole-tree run buries the one condition this
refactor is about under every pre-existing finding in the repository, and step
6 then has nothing it can compare against.

Record the output. It is the "before" half of step 6, and re-running the same
command on the same paths is the "after" half.

## Step 2 — the bound, in Python terms

What to walk, in the order that finds the surprises:

- every `import` of the target module, across the repository, and whether the
  name imported is a function, a class or the module
- the module's `__all__` if it declares one, and the names it exports if it
  does not — an absent `__all__` means every public name is the surface
- `**kwargs` and duck-typed parameters, which is where a consumer depends on a
  shape no signature states
- exceptions raised, including the ones raised by a call the target makes and
  never catches, because a caller may be handling them
- what is logged and at what level, what is recorded as a metric, and any
  `__enter__` / `__exit__`, `__del__` or `atexit` side effect
- mutation of arguments in place, which is observable behaviour with no return
  value attached to it

A name with a leading underscore is not automatically out of the bound. If it
is imported somewhere, it is depended on, and the convention did not stop it.

## Step 3 — the baseline and the mutation check

Green before anything moves, and the target's tests located:

```sh
python3 -m pytest -q
python3 -m pytest -q tests/path/to/target_test.py
```

Coverage is how you find the unprotected branches, not how you decide the
refactor is safe:

```sh
python3 -m pytest -q --cov=package.module --cov-report=term-missing
```

Write the characterization tests at the cheapest level that captures the bound:
prefer a call to the public function with recorded inputs and outputs over a
test that reaches into internals, because internals are what step 5 moves. For
awkward outputs — a rendered document, a payload, a long dict — record the
current value once and assert equality against it. `pytest.approx` for floats,
and freeze the clock and any seed rather than asserting a shape.

Then the check the step is built around. Break the target on purpose, run the
tests, and confirm something fails:

```sh
git stash list  # keep the tree clean first
# edit the target: invert a comparison, drop a dict key, return early
python3 -m pytest -q tests/path/to/target_test.py   # must fail
git checkout -- path/to/target.py
```

If the suite is still green, the test is watching something else. This is the
Python-specific trap and it has a name: a test that asserts a mock was called
passes whatever the code around the mock does, so a refactor that moves the
call into a branch that never runs stays green. Assert on the return value and
the recorded side effect, not on the mock.

Commit the tests alone:

```sh
git commit -m "test: characterize target before refactoring"
```

## Steps 4 and 5 — the per-commit gates

After each transformation, in this order, stopping at the first failure:

```sh
ruff format .
ruff check .
mypy .
python3 -m pytest -q
```

`ruff` and `mypy` are in this list for one reason: a rename or a move that
misses a call site is a type error before it is a test failure, and the type
checker finds it in a second. They do not establish that behaviour is
unchanged — only the suite does that, and only because step 3 saw it fail.

A red suite means the last transformation changed behaviour:

```sh
git checkout -- .   # uncommitted
git revert HEAD     # committed
```

Then commit the transformation on its own:

```sh
git commit -m "refactor: extract the authorization policy from the service"
```

Two Python-specific ways a transformation changes behaviour while looking
structural. Moving code between modules changes when import-time side effects
run, and a module that registered something on import stops registering it.
And a default argument, a class attribute or a module-level constant that is
mutable is shared state; moving it into a function or a method gives each call
its own copy, which is usually the fix and is always a behaviour change.

## Step 6 — the after

```sh
python3 engineering/hooks/check-structure.py path/to/target.py path/to/new.py
```

Pass the new files as well as the old one. A count taken only on the original
file is the count that makes relocation look like progress, which is the exact
failure the step exists to catch.

## Worked example

A service class mixing authorization rules, a payment gateway client and retry
handling. It is 14 methods and one of them nests five deep.

**Step 1.** `rules/kiss.md` condition 1, one function at depth 5, and
`rules/clean-code.md` condition 1, the same function at 44 statements. Blocked
change: a second payment provider cannot be added without a sixth branch in
that function.

**Step 2.** Surface: four public methods, three of them called from one
request handler and one from a scheduled job. Failure modes: two exception
types the handler maps to HTTP codes. Side effects: an audit log line per
authorization decision, which a report reads, and a retry counter metric.
Nothing is published outside the repository, so step 2's contract question
ends there. Assumed: the ordering of the audit line relative to the gateway
call, which nothing tests.

**Step 3.** The suite covers the happy path and one failure. Three
characterization tests are added: the audit line and its ordering, the two
exception mappings, and the retry count on a gateway timeout. Each is checked
by breaking the target and watching it fail. One commit.

**Step 4.** Smallest transformation that stops the depth condition firing:
extract the authorization decision into its own function in the same module.
Not a strategy object — condition 1 of `rules/yagni.md` is not satisfied,
because the second provider is a backlog item and there is one consumer.
Reversal criterion: if the extracted function needs the service's state after
all, it goes back inline and the depth is solved by inverting the guards.

**Step 5.** Four commits — extract the decision, invert the guards that
remained, move the retry into the gateway client, delete the branch the second
provider was going to use and never did. Gates green after each.

**Step 6.** Depth is 2, the function is 19 statements, both conditions stop
firing. The three questions: the extracted function is
`is_authorized`, which needs no "and"; a reader chasing an authorization
decision reads one function instead of one branch inside four others, so the
hop count fell; and the name says what it decides rather than where it came
from. Not relocated.

**Step 7.** The ordering of the audit line is no longer assumed — it is one of
the three characterization tests. What stayed assumed: the metric's label set,
which nothing in the suite reaches.
