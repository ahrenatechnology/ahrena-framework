#!/usr/bin/env python3
"""Detector for the typing conditions in the Python engineering rule.

Decides four of the five conditions stated in engineering-python/rules/typing.md:

    2. every parameter and every return carries an annotation
    3. an `Any` in an annotation carries a comment saying why
    4. no parameter is defaulted to a mutable literal or to a call that builds one
    5. no `except:` or `except Exception:` handler discards what it caught

Condition 1 — `mypy --strict` reports nothing — is not decided here and could
not be. An AST sees that an annotation is missing; only a type checker sees
that one is wrong, and seeing that means resolving every name across every
file and running a type system over the result. The rule requires the
consuming project to adopt mypy for exactly that reason, and this hook decides
the part of the rule that needs nothing installed.

That split is also what makes conditions 2 to 5 hold on a project that
configures nothing. There is no threshold to tune and no table to fill in: the
hook ships inside the plugin, takes the standard library and nothing else, and
a consumer runs precisely what CI runs.

Usage:
    python3 engineering-python/hooks/check-typing.py [path ...]
"""

from __future__ import annotations

import ast
import io
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Union

RULE = "typing"

# Directories a source walk does not enter. Dot-prefixed names are skipped by
# shape rather than by name, so a cache nobody has heard of yet is skipped
# too; the list holds the vendored and generated trees that carry no dot.
SKIP_NAMES = frozenset({"__pycache__", "node_modules", "venv", "build", "dist"})

# The two node families this hook keeps asking about, once as a union for the
# annotations and once as a tuple for `isinstance`. Neither tuple is annotated,
# so the checker narrows through it: this hook is held to the rule it decides,
# and `mypy --strict` is clean on it.
FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]
CallableNode = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda]

FUNCTION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
CALLABLE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)

# A comment that is an instruction to a tool is not a justification. `# type:
# ignore` beside an `Any` is the second half of the same silence, not a reason
# for it, and pyright's directive is here for the same reason mypy's is.
TOOL_DIRECTIVES = ("type:", "noqa", "pragma", "mypy", "ruff", "pyright", "fmt:", "isort")

# Condition 4. The literals are mutable by construction; the call list is
# Ruff's B006 set, taken unchanged rather than widened, because a closed list
# of builders is what keeps `def f(x=Decimal("0"))` out of the report.
MUTABLE_DISPLAYS: tuple[type, ...] = (ast.List, ast.Dict, ast.Set)
MUTABLE_COMPREHENSIONS: tuple[type, ...] = (ast.ListComp, ast.DictComp, ast.SetComp)
MUTABLE_BUILDERS = frozenset(
    {"list", "dict", "set", "bytearray", "deque", "defaultdict", "OrderedDict", "Counter", "ChainMap"}
)

# Condition 5. These are the two handlers that catch everything; a handler
# naming the failure it absorbs is a decision and is not read here.
BLIND_EXCEPTIONS = frozenset({"Exception", "BaseException"})

# The calls that leave a trace: the standard library's logging vocabulary,
# `warnings.warn`, and the `sys` and `traceback` functions that reach for the
# live exception. The second group is here because a bare `except:` has no
# name to bind, so `sys.exc_info()` is how such a handler takes hold of what
# it caught, and a handler that has hold of it has not discarded it.
TRACE_CALLS = frozenset(
    {
        "debug",
        "info",
        "warning",
        "warn",
        "error",
        "exception",
        "critical",
        "fatal",
        "log",
        "exc_info",
        "format_exc",
        "print_exc",
        "format_exception",
        "print_exception",
    }
)


# --- findings --------------------------------------------------------------


@dataclass
class Finding:
    where: str  # path, with :line
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    rel: str  # for reporting, relative to the working directory
    tree: ast.Module
    comments: dict[int, str]  # line number -> the comment text on that line


# --- reading one file ------------------------------------------------------


def display(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def comments_in(text: str) -> dict[int, str]:
    """Every comment in the file, by the line it sits on.

    Tokenised rather than scanned for `#`, because a hash inside a string
    literal is not a comment and a detector that thinks it is will accept a
    justification nobody wrote.
    """
    found: dict[int, str] = {}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            found[token.start[0]] = token.string
    return found


def load(path: Path, rel: str) -> Source | None:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
        print(f"{rel}\n    skipped, this interpreter cannot parse it: {exc}", file=sys.stderr)
        return None
    return Source(rel, tree, comments_in(text))


# --- the callables in a file -----------------------------------------------


def _method_ids(tree: ast.Module) -> set[int]:
    """Identities of the defs that sit directly in a class body."""
    marked: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            marked.update(id(child) for child in node.body if isinstance(child, FUNCTION_TYPES))
    return marked


def functions(tree: ast.Module) -> list[tuple[FunctionNode, bool]]:
    """Every `def` in the file, paired with whether it is a method."""
    methods = _method_ids(tree)
    return [(node, id(node) in methods) for node in ast.walk(tree) if isinstance(node, FUNCTION_TYPES)]


def callables(tree: ast.Module) -> list[CallableNode]:
    """Every `def` and every `lambda`: the nodes that carry a parameter list."""
    return [node for node in ast.walk(tree) if isinstance(node, CALLABLE_TYPES)]


def decorators(node: FunctionNode) -> set[str]:
    """The decorator names on a def, with any call wrapper unwrapped."""
    names = set()
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        names.add(named(target))
    return names


def named(node: ast.AST) -> str:
    """The trailing name of a dotted expression, or '' when there is none."""
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else ""


def parameters(node: CallableNode) -> list[ast.arg]:
    spec = node.args
    named_args = [*spec.posonlyargs, *spec.args, *spec.kwonlyargs]
    variadic = [arg for arg in (spec.vararg, spec.kwarg) if arg is not None]
    return named_args + variadic


def receiver(node: FunctionNode, is_method: bool) -> ast.arg | None:
    """The `self` or `cls` a method does not annotate, or None.

    Taken positionally rather than by name, because the receiver is whatever
    sits first and a method that calls it something else still has one. A
    `staticmethod` has none, which is the whole difference between the two.
    """
    positional = [*node.args.posonlyargs, *node.args.args]
    if not is_method or not positional or "staticmethod" in decorators(node):
        return None
    return positional[0]


# --- condition 2: every parameter and every return is annotated ------------


def _needs_return(node: FunctionNode, annotated: int) -> bool:
    """Whether the def owes a return annotation.

    An `__init__` with at least one annotated parameter does not, which is
    mypy's own exemption rather than a softening invented here. The rule
    requires mypy in condition 1, and a hook that disagreed with it would be
    reporting a state the checker calls correct.
    """
    return node.name != "__init__" or annotated == 0


def check_annotations(source: Source, findings: list[Finding]) -> None:
    for node, is_method in functions(source.tree):
        skipped = receiver(node, is_method)
        params = [arg for arg in parameters(node) if arg is not skipped]
        missing = [arg.arg for arg in params if arg.annotation is None]
        if missing:
            findings.append(_missing_parameters(source, node, missing))
        if node.returns is None and _needs_return(node, len(params) - len(missing)):
            findings.append(_missing_return(source, node))


def _missing_parameters(source: Source, node: FunctionNode, missing: list[str]) -> Finding:
    listed = ", ".join(missing)
    return Finding(
        f"{source.rel}:{node.lineno}",
        2,
        f"{node.name} does not annotate {listed}; an unannotated parameter is a contract "
        "the reader has to infer and the checker has nothing to hold, so every later change "
        "to it is unverifiable",
    )


def _missing_return(source: Source, node: FunctionNode) -> Finding:
    return Finding(
        f"{source.rel}:{node.lineno}",
        2,
        f"{node.name} declares no return type; write the type it returns, or `-> None` when "
        "it returns nothing, which is the annotation that says so on purpose",
    )


# --- condition 3: an `Any` carries its reason ------------------------------


def annotation_expressions(tree: ast.Module) -> list[ast.expr]:
    """Every expression the syntax marks as a type annotation."""
    holders: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            holders.append(node.annotation)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            holders.append(node.annotation)
        elif isinstance(node, FUNCTION_TYPES) and node.returns is not None:
            holders.append(node.returns)
    return holders


def any_names(holder: ast.expr) -> list[ast.expr]:
    """Every `Any` inside one annotation, bare or dotted."""
    return [
        node
        for node in ast.walk(holder)
        if isinstance(node, (ast.Name, ast.Attribute)) and named(node) == "Any"
    ]


def justified(comments: dict[int, str], line: int) -> bool:
    """Whether a comment on this line or the one above it says something."""
    return any(_is_prose(comments.get(candidate, "")) for candidate in (line, line - 1))


def _is_prose(comment: str) -> bool:
    body = comment.lstrip("#").strip()
    return bool(body) and not body.startswith(TOOL_DIRECTIVES)


def check_any(source: Source, findings: list[Finding]) -> None:
    for holder in annotation_expressions(source.tree):
        for node in any_names(holder):
            if justified(source.comments, node.lineno):
                continue
            findings.append(_unjustified_any(source, node))


def _unjustified_any(source: Source, node: ast.expr) -> Finding:
    return Finding(
        f"{source.rel}:{node.lineno}",
        3,
        "this annotation is `Any` and no comment says why; `Any` switches the checker off "
        "for everything downstream of it, so the reason belongs beside it — on this line or "
        "the one above — and a tool directive is not a reason",
    )


# --- condition 4: no default is mutable ------------------------------------


def defaults_of(node: CallableNode) -> list[ast.expr]:
    spec = node.args
    return [default for default in [*spec.defaults, *spec.kw_defaults] if default is not None]


def mutable_kind(node: ast.expr) -> str:
    """What makes this default mutable, or '' when nothing does."""
    if isinstance(node, MUTABLE_DISPLAYS):
        return "a mutable literal"
    if isinstance(node, MUTABLE_COMPREHENSIONS):
        return "a comprehension"
    if isinstance(node, ast.Call) and named(node.func) in MUTABLE_BUILDERS:
        return f"a call to {named(node.func)}()"
    return ""


def check_defaults(source: Source, findings: list[Finding]) -> None:
    for node in callables(source.tree):
        for default in defaults_of(node):
            kind = mutable_kind(default)
            if kind:
                findings.append(_mutable_default(source, default, kind))


def _mutable_default(source: Source, default: ast.expr, kind: str) -> Finding:
    return Finding(
        f"{source.rel}:{default.lineno}",
        4,
        f"this default is {kind}, and a default is evaluated once when the `def` runs, not "
        "once per call; every caller that takes it shares one object and each one's changes "
        "are waiting for the next. Default to None and build the value in the body",
    )


# --- condition 5: no handler discards what it caught -----------------------


def catches_everything(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(named(node) in BLIND_EXCEPTIONS for node in caught)


def _handler_nodes(handler: ast.ExceptHandler) -> list[ast.AST]:
    found: list[ast.AST] = []
    for statement in handler.body:
        found.extend(ast.walk(statement))
    return found


def _keeps(node: ast.AST, bound: str | None) -> bool:
    """Whether this node is one of the three things a real handler does."""
    if isinstance(node, ast.Raise):
        return True
    if isinstance(node, ast.Call):
        return named(node.func) in TRACE_CALLS
    return bool(bound) and isinstance(node, ast.Name) and node.id == bound


def handled(handler: ast.ExceptHandler) -> bool:
    return any(_keeps(node, handler.name) for node in _handler_nodes(handler))


def check_handlers(source: Source, findings: list[Finding]) -> None:
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.ExceptHandler) or not catches_everything(node):
            continue
        if not handled(node):
            findings.append(_discarded(source, node))


def _discarded(source: Source, handler: ast.ExceptHandler) -> Finding:
    caught = "except:" if handler.type is None else f"except {ast.unparse(handler.type)}:"
    return Finding(
        f"{source.rel}:{handler.lineno}",
        5,
        f"`{caught}` catches everything and the body neither re-raises, nor logs, nor names "
        "the exception it bound, so the failure leaves no trace anywhere. Re-raise it, "
        "translate it with `raise ... from`, log it, or catch the type you meant to absorb",
    )


# --- entry point -----------------------------------------------------------


CHECKS = (check_annotations, check_any, check_defaults, check_handlers)


def _skipped(relative: Path) -> bool:
    return any(part.startswith(".") or part in SKIP_NAMES for part in relative.parts)


def _walk(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    return [path for path in root.rglob("*.py") if not _skipped(path.relative_to(root))]


def sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        found.extend(_walk(root))
    return sorted(set(found))


def report(findings: list[Finding], checked: int, unparsed: int) -> int:
    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if not findings:
        print(f"{checked} file(s), no failures{suffix}.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
    for finding in sorted(findings, key=lambda item: (item.where, item.condition)):
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    unparsed = 0

    for path in sources(roots):
        source = load(path, display(path, base))
        if source is None:
            unparsed += 1
            continue
        for check in CHECKS:
            check(source, findings)
        checked += 1

    return report(findings, checked, unparsed)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
