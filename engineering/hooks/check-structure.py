#!/usr/bin/env python3
"""Detectors for the structural conditions in the engineering rules.

Decides twenty conditions stated in eight rules:

    engineering/rules/solid.md
      1. a class whose LCOM4 exceeds 1
      2. a concrete member declared and not implemented

    engineering/rules/kiss.md
      1. control flow nested more than 3 deep inside a function body
      2. a function branching on a boolean parameter

    engineering/rules/clean-code.md
      1. a function body holding more than 30 statements
      2. a statement that follows an unconditional exit in the same block
      3. a comment whose text parses as code

    engineering/rules/value-semantics.md
      1. a callable taking more than 4 named parameters
      2. a run of 3 parameter names passed together by 3 callables
      3. a mutable field on a type declared immutable
      4. a write through a frozen type's own guard
      5. a class defining __eq__ with no __hash__ beside it

    engineering/rules/cross-cutting-concerns.md
      1. a retry written inline: a loop that catches and backs off
      2. a function that both commits and rolls back
      3. a function that measures its own duration

    engineering/rules/domain-model.md
      1. a module under domain/ importing a mechanism
      2. a name declared under domain/ carrying a vendor token

    engineering/rules/duplication.md
      1. a third function body carrying a shape two others already carry
      2. a third module-level table carrying contents two others already carry

    engineering/rules/debt-markers.md
      1. a debt marker in a comment that names no issue

The remaining conditions in rules/solid.md, rules/cross-cutting-concerns.md
and rules/domain-model.md need a test run, a count across the tree or a
reviewer, and each says so in its own text. This script decides the ones a
parser can decide and claims nothing about the rest. The conditions in
rules/contract-first.md and rules/pattern-selection.md are decided by jobs the
consuming project runs or by a reviewer reading a catalog, and none of them is
here.

Python only. The standard library ships one parser, this plugin takes no
dependencies, and a regular expression over source stops matching the first
time somebody reformats. Detectors for other languages belong with the plugins
that may take a parser dependency.

Nineteen of the twenty conditions read a file. The twentieth is about a change
rather than a file: condition 1 of rules/debt-markers.md reaches a marker this
change added or modified, and a path does not say which lines those are. So the
change is a second, explicit input. `--changed <spec>` passes the spec to a
pinned `git diff` and the condition is then decided over the lines that diff
adds and no others; with no `--changed`, every line of every file the run was
handed is in scope.

The diff is pinned, not taken as the environment leaves it. Colour, a
replacement diff driver, a textconv filter and a dropped path prefix all come
from ordinary git configurations, and each one empties or mis-points the scope
while the run still exits 0; the pinned options sit after the caller's spec
because git lets the last flag win, and the spec is refused if it is an option
outside `--cached` and `--staged`. The output is decoded leniently, because a
diff carries whatever bytes the changed files carry and a strict decode would
end the run in a traceback CI cannot tell from a finding. The parser reads a
`+++ ` row as a file header only where one can stand, undoes git's quoting of
the path, and consumes each hunk by the counts it declares rather than scanning
for the next header — an added source line whose text begins `++ ` renders as
`+++ ` and is otherwise read as a header pointing at a path out of somebody's
source. None of that is hypothetical: every one of those is a way for this gate
to report a clean tree it never looked at.

Defaulting to every line is deliberate. A gate that defaults to seeing less than
it was handed is a gate that passes by seeing nothing, which is the failure the
workflow's own `fetch-depth: 0` comment already records for a revision range on
a shallow clone. The default over-reports on a repository with a backlog of
markers; `--changed` is how that repository adopts the condition, and it is one
argument in the same command line, so the local run and the CI run are the same
run.

git is consulted only for that scoping and only when it is asked for. The other
nineteen conditions never reach it and decide the same thing outside a
repository as inside one.

Usage:
    python3 engineering/hooks/check-structure.py [path ...]
    python3 engineering/hooks/check-structure.py --changed --cached [path ...]
    python3 engineering/hooks/check-structure.py --changed origin/main...HEAD [path ...]
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

# --- the thresholds, and where they come from ------------------------------

# Linux kernel coding style, chapter 1: "if you need more than 3 levels of
# indentation, you're screwed anyway". Measured over control flow rather than
# raw indentation, so a method's own def does not count against it.
NESTING_MAX = 3

# Inside the empty span in the framework's own Python: over 61 functions the
# distribution reaches 26 statements and then jumps straight to 41. Thirty sits
# near the bottom of that gap, so it fails the one function that was already
# too long and leaves headroom over ordinary code without being calibrated to
# the outlier. docs/clean-code.md carries the distribution.
STATEMENT_MAX = 30

# The measured ceiling of the same corpus: 61 callables, maximum 4, and 4 at
# the 95th percentile. Martin's Clean Code puts the ceiling at three; the cap
# takes the measured number, which is one higher and fails nothing that exists.
PARAMETER_MAX = 4

# The arbitration this plugin uses everywhere a repetition has to become a
# thing: the discriminator chain in rules/solid.md, the data clump below, the
# boundary in rules/cross-cutting-concerns.md and both conditions in
# rules/duplication.md. One mechanism, declared once, not four numbers that
# happen to agree.
RULE_OF_THREE = 3

# Fowler's Data Clumps is about three or more values that travel together.
CLUMP_MIN = 3
CLUMP_OCCURRENCES = RULE_OF_THREE

SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".nox",
        ".venv",
        "venv",
        ".eggs",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
    }
)

DEF_NODES: tuple[type, ...] = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
FUNC_NODES: tuple[type, ...] = (ast.FunctionDef, ast.AsyncFunctionDef)

_CONTROL: list[type] = [ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try]
for _optional in ("Match", "TryStar"):  # 3.10 and 3.11 respectively
    _node = getattr(ast, _optional, None)
    if _node is not None:
        _CONTROL.append(_node)
CONTROL_NODES: tuple[type, ...] = tuple(_CONTROL)

# An interface has no state, so every method is its own LCOM4 component. Enums
# and record types score the same way for the same reason. Measuring them says
# something about the language, not about the design.
INTERFACE_BASES = frozenset(
    {"Protocol", "ABC", "ABCMeta", "Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "TypedDict", "NamedTuple"}
)

RECEIVERS = frozenset({"self", "cls", "mcs", "metacls"})


# --- findings --------------------------------------------------------------


@dataclass
class Finding:
    where: str  # path:line
    rule: str  # the rule id, so the full text is one search away
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    """One parsed file. A parameter object, for the reason its own rule gives.

    Every check needs the tree, the display path and (for the comment scan) the
    text. Passed separately that is a three-name run repeated across every
    check in the file, which is the data clump condition 2 of
    rules/value-semantics.md detects. One object, one parameter.
    """

    rel: str
    text: str
    tree: ast.AST
    # The lines this run is scoped to, or None for every line. Only the debt
    # marker condition reads it, because it is the only condition whose subject
    # is a change rather than a file. The module docstring argues the default.
    scope: frozenset[int] | None = None

    def in_scope(self, line: int) -> bool:
        return self.scope is None or line in self.scope


# --- shared helpers --------------------------------------------------------


def base_name(node: ast.expr) -> str:
    """The trailing identifier of a base-class expression, however it is spelled."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return base_name(node.value)
    return ""


def decorator_names(node: ast.AST) -> set[str]:
    names = set()
    for dec in getattr(node, "decorator_list", []):
        target = dec.func if isinstance(dec, ast.Call) else dec
        name = base_name(target)
        if name:
            names.add(name)
    return names


def without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            return body[1:]
    return body


def own_nodes(fn: ast.AST):
    """Every node belonging to this function, not descending into nested defs."""
    stack = [child for child in getattr(fn, "body", []) if not isinstance(child, DEF_NODES)]
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, DEF_NODES):
                stack.append(child)


def functions(tree: ast.AST):
    """Every function and method in the tree, at any depth."""
    return (node for node in ast.walk(tree) if isinstance(node, FUNC_NODES))


def classes(tree: ast.AST):
    return (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef))


def within(node: ast.AST):
    """`node` and everything under it, not descending into nested defs."""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        for child in ast.iter_child_nodes(current):
            if not isinstance(child, DEF_NODES):
                stack.append(child)


def called_names(nodes) -> set[str]:
    """The trailing identifier of every call among these nodes."""
    return {base_name(node.func) for node in nodes if isinstance(node, ast.Call)}


def is_abstract(fn: ast.AST) -> bool:
    return bool(decorator_names(fn) & {"abstractmethod", "abstractproperty", "overload"})


class Union:
    """Disjoint sets, for counting the connected components LCOM4 is defined as."""

    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def join(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[a] = b

    def groups(self) -> list[list[str]]:
        buckets: dict[str, list[str]] = {}
        for item in self.parent:
            buckets.setdefault(self.find(item), []).append(item)
        return [sorted(names) for names in sorted(buckets.values(), key=lambda g: sorted(g)[0])]


# --- rules/solid.md condition 1: LCOM4 -------------------------------------


def _is_interface_or_record(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        if base_name(base) in INTERFACE_BASES:
            return True
    for keyword in cls.keywords:
        if keyword.arg == "metaclass" and base_name(keyword.value) in INTERFACE_BASES:
            return True
    return False


def _features(method: ast.AST) -> set[str]:
    """Every `self.X` this method touches, whether attribute or sibling call."""
    args = method.args.posonlyargs + method.args.args
    if not args or args[0].arg not in RECEIVERS:
        return set()
    receiver = args[0].arg
    touched = set()
    for node in ast.walk(method):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == receiver:
                touched.add(node.attr)
    return touched


def _graph_members(cls: ast.ClassDef) -> list[ast.AST]:
    """The methods LCOM4 is computed over.

    Dunder methods are out because __init__ touches every attribute and would
    connect every component. Static methods are out because they touch none
    and would each form a component of their own.
    """
    return [
        node
        for node in cls.body
        if isinstance(node, FUNC_NODES)
        and not (node.name.startswith("__") and node.name.endswith("__"))
        and "staticmethod" not in decorator_names(node)
    ]


def _partition(members: list[ast.AST]) -> list[list[str]]:
    """LCOM4's connected components: methods joined by shared state or a call."""
    names = [m.name for m in members]
    features = {m.name: _features(m) for m in members}
    union = Union(names)
    for left, right in combinations(names, 2):
        joined = features[left] & features[right] or right in features[left] or left in features[right]
        if joined:
            union.join(left, right)
    return union.groups()


def check_cohesion(src: Source, findings: list[Finding]) -> None:
    for cls in classes(src.tree):
        if _is_interface_or_record(cls):
            continue
        members = _graph_members(cls)
        if len(members) < 2 or all(is_abstract(m) for m in members):
            continue
        groups = _partition(members)
        if len(groups) > 1:
            partition = " | ".join("{" + ", ".join(g) + "}" for g in groups)
            findings.append(
                Finding(
                    f"{src.rel}:{cls.lineno}",
                    "solid",
                    1,
                    f"class {cls.name} has LCOM4 = {len(groups)}; its methods partition into "
                    f"groups that share no instance state and never call one another: {partition}",
                )
            )


# --- rules/solid.md condition 2: a member declared and not implemented -----


def _raises_not_implemented(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Raise) or stmt.exc is None:
        return False
    raised = stmt.exc.func if isinstance(stmt.exc, ast.Call) else stmt.exc
    return base_name(raised) == "NotImplementedError"


def check_unimplemented(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        body = without_docstring(fn.body)
        if len(body) != 1 or not _raises_not_implemented(body[0]):
            continue
        if is_abstract(fn):
            continue
        findings.append(
            Finding(
                f"{src.rel}:{fn.lineno}",
                "solid",
                2,
                f"{fn.name} is declared and not implemented; implement it, mark it "
                "@abstractmethod, or take it out of the interface that forced it",
            )
        )


# --- rules/kiss.md condition 1: nesting depth ------------------------------


def _blocks(node: ast.AST) -> list[tuple[str, list[ast.stmt]]]:
    blocks: list[tuple[str, list[ast.stmt]]] = [("body", list(getattr(node, "body", [])))]
    for handler in getattr(node, "handlers", []):
        blocks.append(("handler", list(handler.body)))
    for case in getattr(node, "cases", []):
        blocks.append(("case", list(case.body)))
    for name in ("orelse", "finalbody"):
        stmts = getattr(node, name, None)
        if stmts:
            blocks.append((name, list(stmts)))
    return blocks


def _depth(node: ast.stmt, level: int) -> tuple[int, int]:
    """Deepest control-flow nesting at or below `node`, which itself sits at `level`."""
    if isinstance(node, DEF_NODES) or not isinstance(node, CONTROL_NODES):
        return 0, 0
    best, where = level, node.lineno
    for label, stmts in _blocks(node):
        # `elif` is an If inside the parent's orelse. It continues the chain
        # rather than nesting inside it, so it stays at the same level.
        elif_chain = label == "orelse" and isinstance(node, ast.If) and len(stmts) == 1 and isinstance(stmts[0], ast.If)
        child_level = level if elif_chain else level + 1
        for child in stmts:
            deep, line = _depth(child, child_level)
            if deep > best:
                best, where = deep, line
    return best, where


def check_nesting(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        best, where = 0, fn.lineno
        for stmt in fn.body:
            deep, line = _depth(stmt, 1)
            if deep > best:
                best, where = deep, line
        if best > NESTING_MAX:
            findings.append(
                Finding(
                    f"{src.rel}:{where}",
                    "kiss",
                    1,
                    f"{fn.name} nests control flow {best} deep; the limit is {NESTING_MAX}",
                )
            )


# --- rules/kiss.md condition 2: a flag argument ----------------------------


def _boolean_parameters(fn: ast.AST) -> list[str]:
    slots = fn.args.posonlyargs + fn.args.args
    defaults: dict[str, ast.expr] = {}
    for arg, default in zip(slots[len(slots) - len(fn.args.defaults) :], fn.args.defaults):
        defaults[arg.arg] = default
    for arg, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults):
        if default is not None:
            defaults[arg.arg] = default

    flags = []
    for arg in slots + fn.args.kwonlyargs:
        if arg.arg in RECEIVERS:
            continue
        annotated = arg.annotation is not None and base_name(arg.annotation) == "bool"
        default = defaults.get(arg.arg)
        defaulted = isinstance(default, ast.Constant) and isinstance(default.value, bool)
        if annotated or defaulted:
            flags.append(arg.arg)
    return flags


def _tests_bare(test: ast.expr, name: str) -> bool:
    if isinstance(test, ast.Name):
        return test.id == name
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return isinstance(test.operand, ast.Name) and test.operand.id == name
    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == name:
        comparators = test.comparators
        return len(comparators) == 1 and isinstance(comparators[0], ast.Constant) and isinstance(comparators[0].value, bool)
    return False


def _first_branch_per_flag(fn: ast.AST, flags: list[str]) -> dict[str, int]:
    """The line of the first `if` testing each flag, so one flag reports once."""
    seen: dict[str, int] = {}
    branches = [n for n in own_nodes(fn) if isinstance(n, ast.If)]
    for node in sorted(branches, key=lambda n: n.lineno):
        hit = next((flag for flag in flags if _tests_bare(node.test, flag)), None)
        if hit is not None and hit not in seen:
            seen[hit] = node.lineno
    return seen


def check_flag_argument(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        flags = _boolean_parameters(fn)
        if not flags:
            continue
        for flag, line in _first_branch_per_flag(fn, flags).items():
            findings.append(
                Finding(
                    f"{src.rel}:{line}",
                    "kiss",
                    2,
                    f"{fn.name} branches on the boolean parameter '{flag}'; that is two "
                    f"functions, and the call site reads {fn.name}(..., True)",
                )
            )


# --- rules/clean-code.md condition 1: function size ------------------------


def body_statements(body: list[ast.stmt]) -> int:
    """Statements in this body, not descending into nested defs.

    A nested function or class counts as one statement and is measured on its
    own, exactly as condition 1 of rules/kiss.md treats nesting depth.
    """
    count = 0
    stack = [list(body)]
    while stack:
        for node in stack.pop():
            count += 1
            if isinstance(node, DEF_NODES):
                continue
            stack.extend(stmts for _, stmts in _blocks(node) if stmts)
    return count


def check_length(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        count = body_statements(without_docstring(fn.body))
        if count > STATEMENT_MAX:
            findings.append(
                Finding(
                    f"{src.rel}:{fn.lineno}",
                    "clean-code",
                    1,
                    f"{fn.name} holds {count} statements; the limit is {STATEMENT_MAX}, and a "
                    "function this long is simulated rather than read",
                )
            )


# --- rules/clean-code.md condition 2: unreachable code ---------------------

EXIT_NODES: tuple[type, ...] = (ast.Return, ast.Raise, ast.Continue, ast.Break)


def _statement_lists(fn: ast.AST):
    """Every statement list inside this function, not descending into nested defs."""
    stack = [list(fn.body)]
    while stack:
        stmts = stack.pop()
        yield stmts
        for node in stmts:
            if isinstance(node, DEF_NODES):
                continue
            stack.extend(nested for _, nested in _blocks(node) if nested)


def _first_dead(stmts: list[ast.stmt]) -> ast.stmt | None:
    for index, node in enumerate(stmts[:-1]):
        if isinstance(node, EXIT_NODES):
            return stmts[index + 1]
    return None


def check_unreachable(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        for stmts in _statement_lists(fn):
            dead = _first_dead(stmts)
            if dead is not None:
                findings.append(
                    Finding(
                        f"{src.rel}:{dead.lineno}",
                        "clean-code",
                        2,
                        f"this statement follows an unconditional exit in {fn.name} and cannot "
                        "run; delete it, or move the exit that shadows it",
                    )
                )


# --- rules/clean-code.md condition 3: commented-out code -------------------

# English prose almost never parses as Python, but a single word parses as a
# bare name and `type: ignore` parses as an annotation. Restricting the match
# to statements that carry an effect, and excluding the tool directives by
# prefix, is what keeps the detector silent on ordinary comments.
COMMENT_STATEMENTS: tuple[type, ...] = (
    ast.Assign,
    ast.AugAssign,
    ast.Return,
    ast.Raise,
    ast.Import,
    ast.ImportFrom,
    ast.Delete,
    ast.Assert,
    ast.Global,
    ast.Nonlocal,
)

TOOL_DIRECTIVES = ("type:", "noqa", "pragma", "pylint", "mypy", "ruff", "fmt:", "isort", "!")


def _is_code(comment: str) -> bool:
    body = comment.lstrip("#").strip()
    if not body or body.startswith(TOOL_DIRECTIVES):
        return False
    try:
        parsed = ast.parse(body)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    if not parsed.body:
        return False
    head = parsed.body[0]
    if isinstance(head, COMMENT_STATEMENTS):
        return True
    return isinstance(head, ast.Expr) and isinstance(head.value, ast.Call)


def _comments(text: str) -> list[tokenize.TokenInfo]:
    try:
        stream = tokenize.generate_tokens(io.StringIO(text).readline)
        return [token for token in stream if token.type == tokenize.COMMENT]
    except (tokenize.TokenError, SyntaxError, IndentationError, ValueError):
        return []


def check_commented_code(src: Source, findings: list[Finding]) -> None:
    for token in _comments(src.text):
        if not _is_code(token.string):
            continue
        findings.append(
            Finding(
                f"{src.rel}:{token.start[0]}",
                "clean-code",
                3,
                f"this comment is code, not prose: {token.string.strip()!r}; delete it, "
                "because version control already keeps the version that ran",
            )
        )


# --- rules/value-semantics.md condition 1: parameter count -----------------


def named_parameters(fn: ast.AST) -> list[str]:
    """Parameter names, without the receiver and without *args and **kwargs.

    The variadics are excluded because they are not a clump: the caller sees
    one name, not five, and there is nothing to gather into an object.
    """
    slots = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
    return [arg.arg for arg in slots if arg.arg not in RECEIVERS]


def check_parameter_count(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        names = named_parameters(fn)
        if len(names) <= PARAMETER_MAX:
            continue
        findings.append(
            Finding(
                f"{src.rel}:{fn.lineno}",
                "value-semantics",
                1,
                f"{fn.name} takes {len(names)} parameters; the limit is {PARAMETER_MAX}. Gather "
                "the ones that belong together into a value, or split the function; a parameter "
                "object with a single call site is gated by the abstraction trigger in "
                "rules/yagni.md, and with one call site the split is the smaller fix",
            )
        )


# --- rules/value-semantics.md condition 2: a data clump --------------------


def _runs(names: list[str]) -> set[tuple[str, ...]]:
    """Every contiguous run of CLUMP_MIN or more parameter names."""
    found = set()
    for start in range(len(names)):
        for end in range(start + CLUMP_MIN, len(names) + 1):
            found.add(tuple(names[start:end]))
    return found


def _sharers(tree: ast.AST) -> dict[tuple[str, ...], list[ast.AST]]:
    shared: dict[tuple[str, ...], list[ast.AST]] = {}
    for fn in functions(tree):
        for run in _runs(named_parameters(fn)):
            shared.setdefault(run, []).append(fn)
    return {run: fns for run, fns in shared.items() if len(fns) >= CLUMP_OCCURRENCES}


def _contains(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    span = len(shorter)
    return any(longer[i : i + span] == shorter for i in range(len(longer) - span + 1))


def _maximal(shared: dict[tuple[str, ...], list[ast.AST]]) -> list[tuple[str, ...]]:
    """Drop a run that is a sub-run of a longer one shared by the same callables."""
    kept = []
    for run, fns in shared.items():
        lines = {fn.lineno for fn in fns}
        covered = any(
            len(other) > len(run) and _contains(other, run) and {f.lineno for f in others} == lines
            for other, others in shared.items()
        )
        if not covered:
            kept.append(run)
    return sorted(kept)


def check_data_clump(src: Source, findings: list[Finding]) -> None:
    shared = _sharers(src.tree)
    for run in _maximal(shared):
        fns = sorted(shared[run], key=lambda fn: fn.lineno)
        names = ", ".join(fn.name for fn in fns)
        findings.append(
            Finding(
                f"{src.rel}:{fns[-1].lineno}",
                "value-semantics",
                2,
                f"({', '.join(run)}) is passed together by {len(fns)} callables in this module "
                f"({names}); the third occurrence is the parameter object, and being the third "
                "it already satisfies the abstraction trigger in rules/yagni.md",
            )
        )


# --- rules/value-semantics.md conditions 3 and 4: immutability -------------

MUTABLE_TYPES = frozenset(
    {
        "list",
        "set",
        "dict",
        "bytearray",
        "deque",
        "defaultdict",
        "Counter",
        "OrderedDict",
        "List",
        "Set",
        "Dict",
        "DefaultDict",
        "MutableSequence",
        "MutableMapping",
        "MutableSet",
    }
)

FROZEN_DECORATORS = frozenset({"frozen"})
FROZEN_BASES = frozenset({"NamedTuple"})


def _declares_frozen(cls: ast.ClassDef) -> bool:
    if any(base_name(base) in FROZEN_BASES for base in cls.bases):
        return True
    if decorator_names(cls) & FROZEN_DECORATORS:
        return True
    for dec in cls.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        for keyword in dec.keywords:
            frozen = keyword.arg == "frozen" and isinstance(keyword.value, ast.Constant)
            if frozen and keyword.value.value is True:
                return True
    return False


def _mutable_factory(node: ast.AnnAssign) -> bool:
    if not isinstance(node.value, ast.Call):
        return False
    return any(
        keyword.arg == "default_factory" and base_name(keyword.value) in MUTABLE_TYPES
        for keyword in node.value.keywords
    )


def _mutable_fields(cls: ast.ClassDef) -> list[tuple[str, int]]:
    found = []
    for node in cls.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if base_name(node.annotation) in MUTABLE_TYPES or _mutable_factory(node):
            found.append((node.target.id, node.lineno))
    return found


def _setattr_escapes(cls: ast.ClassDef) -> list[tuple[str, int]]:
    found = []
    for method in (n for n in cls.body if isinstance(n, FUNC_NODES)):
        if method.name == "__post_init__":
            continue
        for node in own_nodes(method):
            call = isinstance(node, ast.Call) and base_name(node.func) == "__setattr__"
            if call and not isinstance(node.func, ast.Name):
                found.append((method.name, node.lineno))
                break
    return found


def check_immutability(src: Source, findings: list[Finding]) -> None:
    for cls in classes(src.tree):
        if not _declares_frozen(cls):
            continue
        for name, line in _mutable_fields(cls):
            findings.append(
                Finding(
                    f"{src.rel}:{line}",
                    "value-semantics",
                    3,
                    f"{cls.name}.{name} is a mutable container on a type declared immutable; "
                    "the binding is frozen and the contents are not, so two values that compare "
                    "equal today need not tomorrow. Use the immutable counterpart",
                )
            )
        for name, line in _setattr_escapes(cls):
            findings.append(
                Finding(
                    f"{src.rel}:{line}",
                    "value-semantics",
                    4,
                    f"{cls.name}.{name} writes through the frozen type's own guard; return a "
                    "replaced copy instead, or the type is not immutable and should not say it is",
                )
            )


# --- rules/value-semantics.md condition 5: equality without hashing --------


def _defines(cls: ast.ClassDef, name: str) -> bool:
    for node in cls.body:
        if isinstance(node, FUNC_NODES) and node.name == name:
            return True
        if isinstance(node, ast.Assign) and any(base_name(t) == name for t in node.targets):
            return True
        if isinstance(node, ast.AnnAssign) and base_name(node.target) == name:
            return True
    return False


def check_hashability(src: Source, findings: list[Finding]) -> None:
    for cls in classes(src.tree):
        generated = bool(decorator_names(cls) & {"dataclass", "attrs", "define", "frozen"})
        if generated or not _defines(cls, "__eq__") or _defines(cls, "__hash__"):
            continue
        findings.append(
            Finding(
                f"{src.rel}:{cls.lineno}",
                "value-semantics",
                5,
                f"{cls.name} defines __eq__ and no __hash__, so Python makes it unhashable and "
                "it cannot be a dict key or a set member; define __hash__ over the same fields, "
                "or write '__hash__ = None' to say the type has identity rather than value",
            )
        )


# --- rules/cross-cutting-concerns.md conditions 1 to 3 ---------------------

LOOP_NODES: tuple[type, ...] = (ast.For, ast.AsyncFor, ast.While)

SLEEP_NAMES = frozenset({"sleep"})

TRANSACTION_NAMES = frozenset({"commit", "rollback"})

# A duration is two reads of a clock with a subtraction between them. Reading a
# clock once is a timestamp, which is data rather than a measurement.
CLOCK_NAMES = frozenset(
    {"time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "now", "utcnow"}
)


def check_inline_retry(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        for loop in (n for n in own_nodes(fn) if isinstance(n, LOOP_NODES)):
            nodes = list(within(loop))
            catches = any(isinstance(n, ast.Try) and n.handlers for n in nodes)
            if not (catches and called_names(nodes) & SLEEP_NAMES):
                continue
            findings.append(
                Finding(
                    f"{src.rel}:{loop.lineno}",
                    "cross-cutting-concerns",
                    1,
                    f"{fn.name} loops, catches and backs off, which is a retry written inline; "
                    "apply it at the boundary so the policy is declared once and testable apart "
                    "from the call it wraps",
                )
            )
            break


def check_inline_transaction(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        if not TRANSACTION_NAMES <= called_names(own_nodes(fn)):
            continue
        findings.append(
            Finding(
                f"{src.rel}:{fn.lineno}",
                "cross-cutting-concerns",
                2,
                f"{fn.name} both commits and rolls back, so it owns the transaction boundary as "
                "well as the work inside it; move the boundary out and let the body raise",
            )
        )


def check_inline_timer(src: Source, findings: list[Finding]) -> None:
    for fn in functions(src.tree):
        nodes = list(own_nodes(fn))
        reads = [n for n in nodes if isinstance(n, ast.Call) and base_name(n.func) in CLOCK_NAMES]
        duration = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub) for n in nodes)
        if len(reads) < 2 or not duration:
            continue
        findings.append(
            Finding(
                f"{src.rel}:{reads[0].lineno}",
                "cross-cutting-concerns",
                3,
                f"{fn.name} measures its own duration; a timer written inside the work it times "
                "is applied once per author instead of once per boundary",
            )
        )


# --- rules/domain-model.md conditions 1 and 2 ------------------------------

DOMAIN_DIR = "domain"

# The layer names the rule declares, so the map that condition 6 of
# rules/solid.md needs is carried by the layout instead of by a reviewer.
MECHANISM_DIRS = frozenset({"adapters", "adapter", "infrastructure", "infra", "persistence"})

# Packages that are a mechanism whatever they are imported for. Stdlib modules
# a domain legitimately uses — datetime, decimal, uuid, enum, json — are not
# here; the list holds transports, drivers, frameworks and numeric runtimes.
MECHANISM_PACKAGES = frozenset(
    {
        "sqlite3",
        "socket",
        "urllib",
        "http",
        "requests",
        "httpx",
        "aiohttp",
        "boto3",
        "botocore",
        "redis",
        "pymongo",
        "psycopg",
        "psycopg2",
        "sqlalchemy",
        "kafka",
        "confluent_kafka",
        "pika",
        "django",
        "flask",
        "fastapi",
        "starlette",
        "celery",
        "pandas",
        "numpy",
        "torch",
        "tensorflow",
        "sklearn",
        "openai",
        "anthropic",
    }
)

# Tokens that name something outside every domain: a product, a protocol, a
# serialisation format or a layering technique. Unlike a list of generic nouns,
# which docs/clean-code.md refuses, each of these denotes a thing the domain
# does not contain, so a match is a domain name pointing outward.
VENDOR_TOKENS = frozenset(
    {
        "sql", "sqlite", "postgres", "postgresql", "mysql", "mongo", "mongodb", "redis",
        "kafka", "rabbitmq", "sqs", "sns", "s3", "dynamodb", "elasticsearch",
        "http", "https", "rest", "grpc", "graphql", "soap", "websocket",
        "json", "xml", "yaml", "csv", "protobuf", "avro",
        "orm", "dao", "dto", "jdbc", "odbc", "impl",
        "jwt", "oauth", "smtp", "ldap",
        "boto", "aws", "azure", "gcp",
        "django", "flask", "fastapi", "celery",
        "pandas", "numpy", "torch", "tensorflow", "sklearn", "openai", "anthropic",
    }
)

TOKEN = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")


def name_tokens(name: str) -> list[str]:
    """A declared name split on snake_case and camelCase boundaries, lowercased."""
    return [part.lower() for part in TOKEN.findall(name)]


def in_domain(rel: str) -> bool:
    return DOMAIN_DIR in Path(rel).parts


def _imported(node: ast.stmt) -> list[str]:
    """The dotted module path of each import in this statement."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module or ""]
    return []


def _mechanism_in(module: str) -> str:
    parts = [part for part in module.split(".") if part]
    if parts and parts[0] in MECHANISM_PACKAGES:
        return parts[0]
    hits = [part for part in parts if part in MECHANISM_DIRS]
    return hits[0] if hits else ""


def check_domain_imports(src: Source, findings: list[Finding]) -> None:
    if not in_domain(src.rel):
        return
    for node in ast.walk(src.tree):
        for module in _imported(node):
            mechanism = _mechanism_in(module)
            if not mechanism:
                continue
            findings.append(
                Finding(
                    f"{src.rel}:{node.lineno}",
                    "domain-model",
                    1,
                    f"a domain module imports '{module}', which is mechanism ('{mechanism}'); "
                    "the domain declares what it needs and the adapter implements it",
                )
            )


def _declared_names(tree: ast.AST) -> list[tuple[str, int]]:
    """Every name this module declares: types, callables and annotated fields."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, DEF_NODES):
            found.append((node.name, node.lineno))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.append((node.target.id, node.lineno))
    return found


def check_domain_names(src: Source, findings: list[Finding]) -> None:
    if not in_domain(src.rel):
        return
    stem = Path(src.rel).stem
    for name, line in [(stem, 1), *_declared_names(src.tree)]:
        hit = next((token for token in name_tokens(name) if token in VENDOR_TOKENS), None)
        if hit is None:
            continue
        shown = f"{stem}.py" if line == 1 and name == stem else name
        findings.append(
            Finding(
                f"{src.rel}:{line}",
                "domain-model",
                2,
                f"the domain name {shown} carries '{hit}', which names a technology rather than "
                "anything in the domain; the model should read the way the business speaks",
            )
        )


# --- rules/duplication.md conditions 1 and 2 -------------------------------

# The smallest body the clone condition reports. Measured over 288,485 lines
# of the CPython standard library: at four statements the detector first
# groups three unrelated constructors (argparse, difflib, doctest) that each
# assign four parameters to four fields, and at five and above every group in
# that corpus is a genuine repetition. docs/duplication.md carries the counts.
CLONE_MIN_STATEMENTS = 5

# Fowler's three-or-more again, this time over a table's entries. Below it the
# detector reports [], {}, () and ['Popen'] — five of the seven groups it
# finds in the same corpus, and none of the two worth having.
TABLE_MIN_ENTRIES = 3

COLLECTION_NODES: tuple[type, ...] = (ast.List, ast.Set, ast.Tuple, ast.Dict)

# A bounded context is a directory, as rules/domain-model.md declares, and
# these are the layer names that mark one. The directory above the first of
# them is the context a file belongs to.
CONTEXT_LAYERS = MECHANISM_DIRS | {DOMAIN_DIR, "application"}

# The fields that carry a declared identifier rather than structure. Renaming
# these consistently is what makes two bodies one shape when one is the other
# with different names.
IDENTIFIER_FIELDS: dict[type, tuple[str, ...]] = {
    ast.Name: ("id",),
    ast.Attribute: ("attr",),
    ast.arg: ("arg",),
    ast.keyword: ("arg",),
    ast.alias: ("name", "asname"),
    ast.ExceptHandler: ("name",),
    ast.Global: ("names",),
    ast.Nonlocal: ("names",),
    ast.FunctionDef: ("name",),
    ast.AsyncFunctionDef: ("name",),
    ast.ClassDef: ("name",),
}


@dataclass
class Copy:
    path: str
    line: int
    what: str  # the function, or the names the table is bound to
    size: int  # statements for a body, entries for a table

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


class Shape:
    """A body's structure, with its identifiers and its literals renamed.

    Two bodies have one shape when either can be obtained from the other by
    renaming. The renaming is consistent rather than blanket: the first
    distinct name becomes n0 and the second n1, so `a + b` and `a + a` stay
    different shapes and only a real copy collides.
    """

    def __init__(self) -> None:
        self.names: dict[str, str] = {}
        self.literals: dict[str, str] = {}
        self.parts: list[str] = []

    def emit(self, node: ast.AST) -> None:
        if isinstance(node, ast.Constant):
            kind = type(node.value).__name__
            key = f"{kind}:{node.value!r}"
            self.parts.append(self.literals.setdefault(key, f"{kind}{len(self.literals)}"))
            return
        self.parts.append(type(node).__name__ + "(")
        identifiers = IDENTIFIER_FIELDS.get(type(node), ())
        for field, value in ast.iter_fields(node):
            self.emit_value(value, identifiers, field)
            self.parts.append(",")
        self.parts.append(")")

    def emit_value(self, value: object, identifiers: tuple[str, ...], field: str) -> None:
        if field in identifiers and isinstance(value, str):
            self.parts.append(self.names.setdefault(value, f"n{len(self.names)}"))
        elif isinstance(value, ast.AST):
            self.emit(value)
        elif isinstance(value, list):
            for item in value:
                self.emit_value(item, identifiers, field)
        else:
            self.parts.append(repr(value))


def shape_of(body: list[ast.stmt]) -> str:
    shape = Shape()
    for stmt in body:
        shape.emit(stmt)
    return "".join(shape.parts)


def context_of(rel: str) -> str:
    """The bounded context a file sits in: the directory above its layer.

    A tree with none of the layer directories is one context, which is the
    right answer for a codebase that has not drawn any: everything in it is
    one model, so every copy in it counts against every other.
    """
    parts = Path(rel).parts
    for index, part in enumerate(parts):
        if part in CONTEXT_LAYERS:
            return "/".join(parts[:index])
    return ""


def _bodies(sources: list[Source]) -> dict[tuple[str, str], list[Copy]]:
    """Function bodies at or over the floor, grouped by context and shape."""
    found: dict[tuple[str, str], list[Copy]] = {}
    for src in sources:
        context = context_of(src.rel)
        for fn in functions(src.tree):
            body = without_docstring(fn.body)
            size = body_statements(body)
            if size < CLONE_MIN_STATEMENTS:
                continue
            found.setdefault((context, shape_of(body)), []).append(
                Copy(src.rel, fn.lineno, fn.name, size)
            )
    return found


def _entries(node: ast.expr) -> list:
    return node.keys if isinstance(node, ast.Dict) else node.elts


def _table(node: ast.stmt) -> ast.expr | None:
    """The literal collection this module-level assignment binds, if any.

    A single-argument call around one counts, because `frozenset({...})` and
    `tuple([...])` are the same table wearing the constructor that makes it
    immutable, which is what condition 3 of rules/value-semantics.md asks for.
    """
    value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
    if isinstance(value, ast.Call) and len(value.args) == 1 and not value.keywords:
        value = value.args[0]
    if not isinstance(value, COLLECTION_NODES):
        return None
    return value if len(_entries(value)) >= TABLE_MIN_ENTRIES else None


def _bound_to(node: ast.stmt) -> str:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return ", ".join(base_name(target) for target in targets) or "a table"


def _tables(sources: list[Source]) -> dict[tuple[str, str], list[Copy]]:
    """Module-level literal tables, grouped by context and by contents."""
    found: dict[tuple[str, str], list[Copy]] = {}
    for src in sources:
        context = context_of(src.rel)
        for node in getattr(src.tree, "body", []):
            table = _table(node)
            if table is None:
                continue
            found.setdefault((context, ast.dump(table)), []).append(
                Copy(src.rel, node.lineno, _bound_to(node), len(_entries(table)))
            )
    return found


def _duplicates(groups: dict[tuple[str, str], list[Copy]]) -> list[tuple[str, list[Copy]]]:
    """The groups that reached the rule of three, each ordered and with its context."""
    reached = []
    for (context, _), copies in sorted(groups.items()):
        if len(copies) >= RULE_OF_THREE:
            reached.append((context, sorted(copies, key=lambda copy: (copy.path, copy.line))))
    return reached


def _inside(context: str) -> str:
    return f" inside the context '{context}'" if context else ""


def _listed(copies: list[Copy]) -> str:
    return "; ".join(f"{copy.what} at {copy.where}" for copy in copies)


def sweep_duplicate_bodies(sources: list[Source], findings: list[Finding]) -> None:
    for context, copies in _duplicates(_bodies(sources)):
        last = copies[-1]
        findings.append(
            Finding(
                last.where,
                "duplication",
                1,
                f"{last.what} repeats a {last.size}-statement body that "
                f"{len(copies) - 1} other functions already carry{_inside(context)} "
                f"({_listed(copies[:-1])}); three copies is one decision written three "
                "times. Collapse them and parameterise what differs; being the third "
                "occurrence this already satisfies the abstraction trigger in "
                "rules/yagni.md, and a base class raised to hold the common part is "
                "more structure than the duplication it removes",
            )
        )


def sweep_duplicate_tables(sources: list[Source], findings: list[Finding]) -> None:
    for context, copies in _duplicates(_tables(sources)):
        last = copies[-1]
        findings.append(
            Finding(
                last.where,
                "duplication",
                2,
                f"{last.what} holds the same {last.size} entries as "
                f"{len(copies) - 1} other module-level tables{_inside(context)} "
                f"({_listed(copies[:-1])}); the names differ and the contents are the "
                "duplicate. Declare it once and import it. A name is not an "
                "abstraction, so the trigger in rules/yagni.md does not gate this fix",
            )
        )


# --- rules/debt-markers.md condition 1: a marker that names no issue -------

# The closed set, uppercase. These are the four tokens
# foundation/rules/completeness.md already bans in an artifact's own prose, and
# they are taken from there unchanged so that the two rules governing these
# tokens at least agree on which tokens they are. The predecessor framework's
# list added three lowercase phrases; those are ordinary English, and a detector
# for them rejects prose, which is the argument completeness.md already made
# about a lowercase spelling of the first one. The set is asserted rather than
# measured, by the predecessor and here, and the rule says so.
MARKERS = ("TODO", "TBD", "FIXME", "XXX")

# The marker, then the reference that redeems it. The boundaries are spelled out
# rather than taken from \b so that a longer run of the same letters is one word
# and not a marker. The reference is a parenthesised issue number immediately
# after the token and nowhere else: a number further along the line is a
# cross-reference, and the rule wants the owner of the debt, not a pointer.
DEBT_MARKER = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(MARKERS) + r")(?![A-Za-z0-9_])(\(#[1-9][0-9]*\))?"
)

# Prose about markers, quoted the way completeness.md lets an artifact quote
# one. Without this a detector for the condition cannot describe itself, and
# neither can the rule's own hook. The fence is a run of backticks matched
# against its own length, because a single-backtick fence reads ``TODO`` as two
# empty spans around a bare marker and flags the very escape it offers.
QUOTED = re.compile(r"(`+)(?:(?!\1)[\s\S])*?\1")


def check_debt_markers(src: Source, findings: list[Finding]) -> None:
    for token in _comments(src.text):
        line = token.start[0]
        if not src.in_scope(line):
            continue
        for match in DEBT_MARKER.finditer(QUOTED.sub("", token.string)):
            if match.group(2):
                continue
            findings.append(
                Finding(
                    f"{src.rel}:{line}",
                    "debt-markers",
                    1,
                    f"this comment leaves {match.group(1)} with no issue behind it: "
                    f"{token.string.strip()!r}. Open the issue and write "
                    f"{match.group(1)}(#N) with nothing between the marker and the "
                    "bracket — a space or a colon in there does not redeem it — or do "
                    "the work now, or delete the marker; debt nobody agreed to is debt "
                    "nobody is accountable for",
                )
            )


CHECKS = (
    check_cohesion,
    check_unimplemented,
    check_nesting,
    check_flag_argument,
    check_length,
    check_unreachable,
    check_commented_code,
    check_parameter_count,
    check_data_clump,
    check_immutability,
    check_hashability,
    check_inline_retry,
    check_inline_transaction,
    check_inline_timer,
    check_domain_imports,
    check_domain_names,
    check_debt_markers,
)

# A check reads one file. A sweep reads every file the run was given at once,
# because a copy that stays in one module is the rarer and the cheaper half of
# duplication: the expensive one is the body pasted into the next package.
SWEEPS = (
    sweep_duplicate_bodies,
    sweep_duplicate_tables,
)


# --- entry point -----------------------------------------------------------


def sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_DIRS.isdisjoint(path.relative_to(root).parts):
                found.append(path)
    return found


def display_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def load(path: Path, rel: str, scope: frozenset[int] | None) -> Source | None:
    """The parsed file, or None once the reason it could not be read is reported."""
    try:
        text = path.read_text(encoding="utf-8")
        return Source(rel, text, ast.parse(text, filename=str(path)), scope)
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        print(f"{rel}\n    skipped, this interpreter cannot parse it: {exc}", file=sys.stderr)
        return None


# --- the change, when the run is scoped to one -----------------------------

CHANGED_FLAG = "--changed"

# The two spellings of a spec that may begin with a dash. Every other option git
# diff accepts is refused here, because the spec lands on the same command line
# as the options below and git lets the last flag win: `--name-only`, `--quiet`
# and `--output=` each leave the scope empty while the run still exits 0, and
# `-U5` widens it past the lines the change wrote. That is the silent pass
# rules/debt-markers.md names as the one failure mode worse than a noisy one.
SPEC_OPTIONS = ("--cached", "--staged")

# The prefix the `+++` side of a file header carries. Pinned rather than assumed:
# diff.noprefix drops it and diff.mnemonicPrefix rewrites it, and a hook that
# chopped two characters off unconditionally would read `abc.py` as `c.py` —
# blaming a file nobody touched and missing the marker in the real one.
DST_PREFIX = "b/"

# The diff is pinned rather than taken as the environment leaves it. Colour
# escapes (color.diff), a replacement driver (diff.external, GIT_EXTERNAL_DIFF)
# and a content filter (diff.*.textconv) are ordinary configurations, and each
# one empties or garbles the scope while the run still exits 0. The pinned
# options follow the caller's spec so that a spec which smuggled one of them in
# cannot override them.
PINNED = (
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--src-prefix=a/",
    f"--dst-prefix={DST_PREFIX}",
    "--unified=0",
)

# A unified-diff hunk header. With --unified=0 there is no context, so the range
# on the `+` side is exactly the lines the change adds or rewrites, and the two
# counts together are exactly how many body rows follow the header — which is
# what lets the parser consume a hunk rather than scan forward for the next one.
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# git renders a merge's unresolved paths as a combined diff, whose `@@@` header
# and two-column body this parser does not read, or as a bare `* Unmerged path`
# line with no diff at all. Either way the file has no two-sided change to scope,
# and that is reported rather than passed over in silence.
UNMERGED = ("diff --cc ", "diff --combined ", "* Unmerged path ")

# git C-quotes a path in a diff header when it holds a double quote, a backslash,
# a control character or — unless core.quotePath is off — a byte above ASCII. The
# first two are quoted whatever that setting says, so a hook that did not undo
# the quoting would be permanently blind to those names and a marker could hide
# behind a filename.
ESCAPES = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
OCTAL = "01234567"


class Unavailable(Exception):
    """git could not answer, and the run must say so rather than see nothing."""


def git(args: list[str], cwd: Path) -> str:
    """git's standard output, decoded leniently.

    A diff carries whatever bytes the changed files carry. Decoding it with the
    locale codec and errors='strict' — which is what text=True asks for — raises
    inside subprocess, past the OSError below, past this hook's own unavailable
    path, and out as a traceback with an exit code CI cannot tell apart from a
    real finding. Every field this parser reads is ASCII, so a byte replaced in a
    content row costs nothing and the run completes.
    """
    try:
        done = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True)
    except OSError as exc:
        raise Unavailable(f"git could not be run: {exc}") from exc
    if done.returncode != 0:
        raise Unavailable(_decode(done.stderr).strip() or f"git exited {done.returncode}")
    return _decode(done.stdout)


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def unquote(field: str) -> str:
    """The path a diff header names, with git's C-style quoting undone."""
    if len(field) < 2 or not (field.startswith('"') and field.endswith('"')):
        return field
    body, out, at = field[1:-1], bytearray(), 0
    try:
        while at < len(body):
            if body[at] != "\\":
                out.extend(body[at].encode("utf-8"))
                at += 1
            elif body[at + 1] in OCTAL:
                out.append(int(body[at + 1 : at + 4], 8))
                at += 4
            else:
                out.extend(ESCAPES.get(body[at + 1], body[at + 1]).encode("utf-8"))
                at += 2
    except (IndexError, ValueError) as exc:
        raise Unavailable(f"git named a path this hook cannot read: {field} ({exc})") from exc
    return out.decode("utf-8", errors="replace")


def added_lines(diff: str, top: Path) -> dict[Path, set[int]]:
    """The lines each file gains, keyed by the path the walk will hand back.

    A `+++ ` row is a file header only where one can stand: straight after the
    matching `--- ` row, and never inside a hunk, whose body is consumed by the
    counts the header declares. Both locks guard one input. Under --unified=0 an
    added source line renders with a single `+`, so a line whose own text begins
    `++ ` reaches this parser as `+++ `; read as a header it re-points the scope
    at a path taken from somebody's source, which hides every later marker in the
    file that really changed and blames one the change never opened. Any file
    carrying diff fixtures holds such a line, this hook's own tests included.
    """
    added: dict[Path, set[int]] = {}
    lines: set[int] | None = None
    source_header = False
    body = 0
    for row in diff.split("\n"):
        if body:
            body -= 0 if row.startswith("\\") else 1
            continue
        if row.startswith(UNMERGED):
            raise Unavailable(
                f"git gave no two-sided diff for an unresolved merge ({row.strip()!r}), and a "
                "file with no diff has no lines in scope. Finish the merge, or pass a revision"
            )
        if row.startswith("diff --git "):
            lines, source_header = None, False
            continue
        if row.startswith("+++ ") and source_header:
            target = unquote(row[4:])
            lines = None if target == "/dev/null" else added.setdefault(_target(top, target), set())
            source_header = False
            continue
        source_header = row.startswith("--- ")
        hunk = HUNK.match(row)
        if hunk is None:
            continue
        start, count = int(hunk.group(2)), int(hunk.group(3) or 1)
        body = int(hunk.group(1) or 1) + count
        if lines is not None:
            lines.update(range(start, start + count))
    return added


def _target(top: Path, target: str) -> Path:
    """The `+++ b/<path>` side of a file header, as an absolute path."""
    if not target.startswith(DST_PREFIX):
        raise Unavailable(
            f"git named the changed file {target!r}, which does not carry the "
            f"{DST_PREFIX!r} prefix this run pins, so the scope cannot be trusted"
        )
    return (top / target[len(DST_PREFIX) :]).resolve()


def scoped(spec: str, paths: list[Path]) -> dict[Path, frozenset[int]]:
    """The lines the change adds, for each walked path the diff reaches."""
    top = Path(git(["rev-parse", "--show-toplevel"], Path.cwd()).strip()).resolve()
    outside = [path for path in paths if not path.is_relative_to(top)]
    if outside:
        raise Unavailable(
            f"{outside[0]} lies outside the repository at {top}, so no diff can say "
            f"which of its lines this change wrote ({len(outside)} path(s) in all)"
        )
    # No pathspec. The walk has already chosen the files, so one argument per
    # walked file is redundant, and past a few thousand of them it is an argument
    # list the kernel refuses — which kills all twenty conditions on a repository
    # whose only fault is being large. Intersecting the whole diff with the walk
    # is a dict lookup per file and has no limit.
    diff = git(["-c", "color.ui=false", "diff", spec, *PINNED], top)
    return {path: frozenset(lines) for path, lines in added_lines(diff, top).items()}


def split_argv(argv: list[str]) -> tuple[list[str], str | None]:
    """The paths, and the change the run is scoped to when one was named."""
    if CHANGED_FLAG not in argv:
        return argv, None
    at = argv.index(CHANGED_FLAG)
    if at + 1 == len(argv):
        raise Unavailable(f"{CHANGED_FLAG} needs a revision or range to pass to the diff")
    spec = argv[at + 1]
    if spec.startswith("-") and spec not in SPEC_OPTIONS:
        raise Unavailable(
            f"{spec!r} is not a revision or range, and the only options {CHANGED_FLAG} "
            f"takes are {' and '.join(SPEC_OPTIONS)}. An option that suppresses the "
            "patch would scope the condition to nothing and still exit 0"
        )
    return argv[:at] + argv[at + 2 :], spec


def report(findings: list[Finding], checked: int, unparsed: int) -> int:
    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if findings:
        print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
        for finding in sorted(findings, key=lambda f: (f.where, f.rule, f.condition)):
            print(finding)
        return 1

    print(f"{checked} file(s), no failures{suffix}.")
    return 0


def main(argv: list[str]) -> int:
    base = Path.cwd()
    try:
        rest, spec = split_argv(argv[1:])
        paths = sources([Path(a).resolve() for a in rest] or [base])
        scope = scoped(spec, paths) if spec is not None else {}
    except Unavailable as exc:
        print(f"{CHANGED_FLAG}: {exc}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    parsed: list[Source] = []
    unparsed = 0

    for path in paths:
        lines = None if spec is None else scope.get(path, frozenset())
        source = load(path, display_path(path, base), lines)
        if source is None:
            unparsed += 1
            continue
        for check in CHECKS:
            check(source, findings)
        parsed.append(source)

    for sweep in SWEEPS:
        sweep(parsed, findings)

    return report(findings, len(parsed), unparsed)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
