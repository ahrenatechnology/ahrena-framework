#!/usr/bin/env python3
"""Detectors for the structural conditions in the engineering rules.

Decides four conditions stated in two rules:

    engineering/rules/solid.md
      1. a class whose LCOM4 exceeds 1
      2. a concrete member declared and not implemented

    engineering/rules/kiss.md
      1. control flow nested more than 3 deep inside a function body
      2. a function branching on a boolean parameter

The remaining conditions in rules/solid.md need a test run, a count across the
tree or a layer map, and each says so in its own text. This script decides the
ones a parser can decide and claims nothing about the rest.

Python only. The standard library ships one parser, this plugin takes no
dependencies, and a regular expression over source stops matching the first
time somebody reformats. Detectors for other languages belong with the plugins
that may take a parser dependency.

Usage:
    python3 engineering/hooks/check-structure.py [path ...]
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

# --- the thresholds, and where they come from ------------------------------

# Linux kernel coding style, chapter 1: "if you need more than 3 levels of
# indentation, you're screwed anyway". Measured over control flow rather than
# raw indentation, so a method's own def does not count against it.
NESTING_MAX = 3

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


def check_cohesion(tree: ast.AST, rel: str, findings: list[Finding]) -> None:
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
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
                    f"{rel}:{cls.lineno}",
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


def check_unimplemented(tree: ast.AST, rel: str, findings: list[Finding]) -> None:
    for fn in (n for n in ast.walk(tree) if isinstance(n, FUNC_NODES)):
        body = without_docstring(fn.body)
        if len(body) != 1 or not _raises_not_implemented(body[0]):
            continue
        if is_abstract(fn):
            continue
        findings.append(
            Finding(
                f"{rel}:{fn.lineno}",
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


def check_nesting(tree: ast.AST, rel: str, findings: list[Finding]) -> None:
    for fn in (n for n in ast.walk(tree) if isinstance(n, FUNC_NODES)):
        best, where = 0, fn.lineno
        for stmt in fn.body:
            deep, line = _depth(stmt, 1)
            if deep > best:
                best, where = deep, line
        if best > NESTING_MAX:
            findings.append(
                Finding(
                    f"{rel}:{where}",
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


def check_flag_argument(tree: ast.AST, rel: str, findings: list[Finding]) -> None:
    for fn in (n for n in ast.walk(tree) if isinstance(n, FUNC_NODES)):
        flags = _boolean_parameters(fn)
        if not flags:
            continue
        for flag, line in _first_branch_per_flag(fn, flags).items():
            findings.append(
                Finding(
                    f"{rel}:{line}",
                    "kiss",
                    2,
                    f"{fn.name} branches on the boolean parameter '{flag}'; that is two "
                    f"functions, and the call site reads {fn.name}(..., True)",
                )
            )


CHECKS = (check_cohesion, check_unimplemented, check_nesting, check_flag_argument)


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


def main(argv: list[str]) -> int:
    roots = [Path(a).resolve() for a in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    unparsed = 0

    for path in sources(roots):
        try:
            rel = path.relative_to(base).as_posix()
        except ValueError:
            rel = path.as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            unparsed += 1
            print(f"{rel}\n    skipped, this interpreter cannot parse it: {exc}", file=sys.stderr)
            continue
        for check in CHECKS:
            check(tree, rel, findings)
        checked += 1

    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if findings:
        print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
        for finding in sorted(findings, key=lambda f: (f.where, f.rule, f.condition)):
            print(finding)
        return 1

    print(f"{checked} file(s), no failures{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
