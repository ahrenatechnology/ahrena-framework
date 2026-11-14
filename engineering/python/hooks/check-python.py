#!/usr/bin/env python3
"""Detector for four of the Python engineering rules.

Decides every condition of these rules, under engineering/python/rules/:

    error-handling.md
        1. a handler that catches BaseException or CancelledError re-raises it
        2. nothing raises `Exception` or `BaseException` itself
        3. no `return`, `break` or `continue` leaves a `finally` block
    immutability.md
        1. a dataclass or attrs class under `domain/` is frozen, or says why not
        2. a function under `domain/` does not mutate a container it was passed
    testing.md
        1. no patch reaches a name under a `domain` or `application` layer
    security.md
        1. `eval` and `exec` run nothing but a literal, or say why
        2. no deserialiser that builds arbitrary objects runs unexplained
        3. no shell runs a command that is not a literal, unexplained
        4. no tar archive is extracted without a filter, unexplained
        5. no call turns TLS verification off, unexplained

The four rules share one hook because they share one walk: a parse of each
file, a table of what its imports bind, and its comments by line. The typing
and boundary conditions keep their own hooks, which were written first and
whose findings this one never repeats.

Like its siblings it takes the standard library and nothing else, so a
consumer runs precisely what CI runs and a project that configured nothing is
still held.

The closed sets below carry the decisions, and each is argued in its rule:

    TOOL_DIRECTIVES     a comment that instructs a tool is not a reason; the
                        same refusal check-typing.py makes for `Any`
    DOMAIN, INTERNAL_LAYERS
                        the layer names rules/module-boundaries.md and the
                        fundamentals domain-model rule already use
    EXITS               ending the process acts on an interrupt rather than
                        swallowing it
    TRACE_CALLS         check-typing.py condition 5's vocabulary; a blind
                        handler with no trace at all is that hook's finding
                        and is not reported a second time here
    MUTATORS            the methods that change a list, dict, set or deque
                        in place
    RECORD_DECORATORS   the decorators that declare a record type, by the
                        dotted name they resolve to; FROZEN_DECORATORS are
                        the attrs pair frozen by construction
    OBJECT_LOADERS, YAML_LOADERS, SAFE_YAML_LOADERS
                        deserialisers that build whatever type the bytes
                        name, and the YAML loaders that do not
    ALWAYS_SHELL, SHELL_ON_REQUEST
                        calls that always run a shell, and the ones that run
                        one when `shell=True` asks
    UNVERIFIED_CONTEXTS the standard library's switch for TLS with no checks
    MOCK_PATCHES        the patch callables, by the dotted name they resolve
                        to, so an HTTP client's `.patch` is not one
    CONTAINER_ANNOTATIONS
                        the annotations that make `+=` and `|=` on a
                        parameter an in-place change

Usage:
    python3 engineering/python/hooks/check-python.py [path ...]
"""

from __future__ import annotations

import ast
import io
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

from sources import MissingPath, display, sources
from typing import Union


FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]
FUNCTION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
LOOP_TYPES = (ast.For, ast.AsyncFor, ast.While)

TOOL_DIRECTIVES = ("type:", "noqa", "pragma", "mypy", "ruff", "pyright", "fmt:", "isort", "nosec")

DOMAIN = "domain"
INTERNAL_LAYERS = frozenset({"domain", "application"})

EXITS = frozenset({"exit", "_exit", "abort"})

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

MUTATORS = frozenset(
    {
        "append",
        "appendleft",
        "extend",
        "extendleft",
        "insert",
        "remove",
        "pop",
        "popleft",
        "popitem",
        "clear",
        "update",
        "setdefault",
        "add",
        "discard",
        "sort",
        "reverse",
        "difference_update",
        "intersection_update",
        "symmetric_difference_update",
    }
)

RECORD_DECORATORS = frozenset(
    {
        "dataclasses.dataclass",
        "attrs.define",
        "attrs.mutable",
        "attr.define",
        "attr.mutable",
        "attr.s",
        "attr.attrs",
        "attrs.frozen",
        "attr.frozen",
    }
)
FROZEN_DECORATORS = frozenset({"attrs.frozen", "attr.frozen"})

OBJECT_LOADERS = frozenset(
    {
        "pickle.load",
        "pickle.loads",
        "pickle.Unpickler",
        "_pickle.load",
        "_pickle.loads",
        "marshal.load",
        "marshal.loads",
        "shelve.open",
        "dill.load",
        "dill.loads",
        "jsonpickle.decode",
        "yaml.unsafe_load",
        "yaml.unsafe_load_all",
    }
)
YAML_LOADERS = frozenset({"yaml.load", "yaml.load_all"})
SAFE_YAML_LOADERS = frozenset({"SafeLoader", "CSafeLoader", "BaseLoader", "CBaseLoader"})

ALWAYS_SHELL = frozenset(
    {
        "os.system",
        "os.popen",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
        "asyncio.create_subprocess_shell",
    }
)
SHELL_ON_REQUEST = frozenset(
    {"subprocess.run", "subprocess.call", "subprocess.check_call", "subprocess.check_output", "subprocess.Popen"}
)

UNVERIFIED_CONTEXTS = frozenset({"ssl._create_unverified_context"})

MOCK_PATCHES = frozenset({"unittest.mock.patch", "mock.patch", "mocker.patch"})

CONTAINER_ANNOTATIONS = frozenset(
    {
        "list",
        "dict",
        "set",
        "deque",
        "bytearray",
        "defaultdict",
        "OrderedDict",
        "Counter",
        "List",
        "Dict",
        "Set",
        "Deque",
        "DefaultDict",
        "MutableSequence",
        "MutableMapping",
        "MutableSet",
    }
)


@dataclass
class Finding:
    where: str
    rule: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    rel: str
    parts: tuple[str, ...]
    tree: ast.Module
    comments: dict[int, str]
    imports: dict[str, str]


def where(source: Source, node: ast.AST) -> str:
    return f"{source.rel}:{getattr(node, 'lineno', 0)}"


def in_domain(source: Source) -> bool:
    return DOMAIN in source.parts


def comments_in(text: str) -> dict[int, str]:
    """Every comment in the file, by line; tokenised so a `#` in a string is not one."""
    found: dict[int, str] = {}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            found[token.start[0]] = token.string
    return found


def imports_in(tree: ast.Module) -> dict[str, str]:
    """What each imported local name is bound to, as a dotted name.

    A relative import keeps its dots, so `from ..domain import fees` binds
    `fees` to `..domain.fees` and the layer it names is still readable.
    """
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                bound[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom):
            origin = "." * node.level + (node.module or "")
            for alias in node.names:
                joined = f"{origin}.{alias.name}" if origin and not origin.endswith(".") else origin + alias.name
                bound[alias.asname or alias.name] = joined
    return bound


def load(path: Path, rel: str) -> Source | None:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        comments = comments_in(text)
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError, tokenize.TokenError) as exc:
        print(f"{rel}\n    skipped, this interpreter cannot parse it: {exc}", file=sys.stderr)
        return None
    return Source(rel, Path(rel).parts[:-1], tree, comments, imports_in(tree))


def named(node: ast.AST) -> str:
    """The trailing name of a dotted expression, or '' when there is none."""
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else ""


def written(node: ast.AST) -> str:
    """A dotted expression as written in the source, or '' when it is not one."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = written(node.value)
        return f"{head}.{node.attr}" if head else ""
    return ""


def resolved(source: Source, node: ast.AST) -> str:
    """A dotted expression with its first name replaced by what the import bound."""
    text = written(node)
    if not text:
        return ""
    head, _, rest = text.partition(".")
    origin = source.imports.get(head, head)
    return f"{origin}.{rest}" if rest else origin


def layers_of(dotted: str) -> set[str]:
    return {segment for segment in dotted.split(".") if segment in INTERNAL_LAYERS}


def justified(source: Source, line: int) -> bool:
    """Whether a comment on this line or the one above it says something."""
    return any(_is_prose(source.comments.get(candidate, "")) for candidate in (line, line - 1))


def _is_prose(comment: str) -> bool:
    body = comment.lstrip("#").strip()
    return bool(body) and not body.startswith(TOOL_DIRECTIVES)


def calls(source: Source) -> list[ast.Call]:
    return [node for node in ast.walk(source.tree) if isinstance(node, ast.Call)]


def keyword(call: ast.Call, name: str) -> ast.expr | None:
    for item in call.keywords:
        if item.arg == name:
            return item.value
    return None


def is_constant(node: ast.expr | None, value: object) -> bool:
    return isinstance(node, ast.Constant) and node.value is value


def is_string_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def statements_within(body: list[ast.stmt]) -> list[ast.AST]:
    """Every node in these statements, without entering a nested def or class."""
    found: list[ast.AST] = []
    pending: list[ast.AST] = list(body)
    while pending:
        node = pending.pop()
        found.append(node)
        if isinstance(node, SCOPE_TYPES):
            continue
        pending.extend(ast.iter_child_nodes(node))
    return found


def _caught(handler: ast.ExceptHandler) -> list[ast.expr]:
    if handler.type is None:
        return []
    return list(handler.type.elts) if isinstance(handler.type, ast.Tuple) else [handler.type]


def _catches_base(handler: ast.ExceptHandler) -> bool:
    return handler.type is None or any(named(node) == "BaseException" for node in _caught(handler))


def _catches_cancellation(handler: ast.ExceptHandler) -> bool:
    return any(named(node) == "CancelledError" for node in _caught(handler))


def _leaves_a_trace(handler: ast.ExceptHandler) -> bool:
    """check-typing.py condition 5's question, asked here only to stay out of its way."""
    for node in statements_within(handler.body):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call) and named(node.func) in TRACE_CALLS:
            return True
        if handler.name and isinstance(node, ast.Name) and node.id == handler.name:
            return True
    return False


def _gives_it_back(handler: ast.ExceptHandler) -> bool:
    """Whether the handler re-raises the same object, or ends the process."""
    for node in statements_within(handler.body):
        if isinstance(node, ast.Raise):
            if node.exc is None:
                return True
            if handler.name and isinstance(node.exc, ast.Name) and node.exc.id == handler.name:
                return True
        if isinstance(node, ast.Call) and named(node.func) in EXITS:
            return True
    return False


def check_base_handlers(source: Source, findings: list[Finding]) -> None:
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        base = _catches_base(node)
        cancellation = _catches_cancellation(node)
        if not (base or cancellation) or _gives_it_back(node):
            continue
        if base and not cancellation and not _leaves_a_trace(node):
            continue
        if justified(source, node.lineno):
            continue
        findings.append(_kept(source, node, CANCELLATION_KEPT if cancellation else INTERRUPT_KEPT))


CANCELLATION_KEPT = (
    "catches the task's cancellation and does not re-raise it, so whoever cancelled "
    "the task is told it finished; a TaskGroup, a timeout and a shutdown all wait on "
    "that exception arriving"
)
INTERRUPT_KEPT = (
    "catches BaseException, which is KeyboardInterrupt, SystemExit and a task's "
    "cancellation as well as every error, and does not re-raise it, so the interrupt "
    "a person or a supervisor sent is turned into a line in a log"
)


def _kept(source: Source, handler: ast.ExceptHandler, why: str) -> Finding:
    caught = "except:" if handler.type is None else f"except {ast.unparse(handler.type)}:"
    return Finding(
        where(source, handler),
        "error-handling",
        1,
        f"`{caught}` {why}. End the handler with a bare `raise`, catch `Exception` if an "
        "interrupt was never meant to land here, or say why on this line or the one above",
    )


def check_vanilla_raises(source: Source, findings: list[Finding]) -> None:
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(raised, ast.Name) and raised.id in {"Exception", "BaseException"}:
            findings.append(
                Finding(
                    where(source, node),
                    "error-handling",
                    2,
                    f"this raises `{raised.id}` itself, and the only handler that can catch it "
                    f"is `except {raised.id}:`, which catches every other failure with it. "
                    "Raise a class named for this failure, or a built-in that already names it",
                )
            )


def _exits_in(body: list[ast.stmt], in_loop: bool) -> list[ast.stmt]:
    """The returns, and the breaks and continues not owned by a nested loop."""
    found: list[ast.stmt] = []
    for statement in body:
        if isinstance(statement, SCOPE_TYPES):
            continue
        if isinstance(statement, ast.Return):
            found.append(statement)
        elif isinstance(statement, (ast.Break, ast.Continue)) and not in_loop:
            found.append(statement)
        for field, children in ast.iter_fields(statement):
            if not isinstance(children, list):
                continue
            nested = [child for child in children if isinstance(child, ast.stmt)]
            handlers = [child for child in children if isinstance(child, ast.ExceptHandler)]
            owned = in_loop or (isinstance(statement, LOOP_TYPES) and field == "body")
            found.extend(_exits_in(nested, owned))
            for handler in handlers:
                found.extend(_exits_in(handler.body, owned))
    return found


def check_finally_exits(source: Source, findings: list[Finding]) -> None:
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.Try, ast.TryStar)) or not node.finalbody:
            continue
        for exit_node in _exits_in(node.finalbody, in_loop=False):
            keyword_name = type(exit_node).__name__.lower()
            findings.append(
                Finding(
                    where(source, exit_node),
                    "error-handling",
                    3,
                    f"this `{keyword_name}` leaves a `finally` block, and leaving a `finally` "
                    "discards the exception in flight, so a failure in the `try` becomes a "
                    "normal exit with nothing raised. Move it after the `try` statement",
                )
            )


def _record_decorator(source: Source, decorator: ast.expr) -> tuple[str, ast.Call | None]:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    call = decorator if isinstance(decorator, ast.Call) else None
    dotted = resolved(source, target)
    return (dotted if dotted in RECORD_DECORATORS else "", call)


def _frozen(dotted: str, call: ast.Call | None) -> bool:
    if dotted in FROZEN_DECORATORS:
        return True
    return call is not None and is_constant(keyword(call, "frozen"), True)


def check_records(source: Source, findings: list[Finding]) -> None:
    if not in_domain(source):
        return
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for decorator in node.decorator_list:
            dotted, call = _record_decorator(source, decorator)
            if not dotted or _frozen(dotted, call) or justified(source, decorator.lineno):
                continue
            findings.append(
                Finding(
                    where(source, decorator),
                    "immutability",
                    1,
                    f"{node.name} is a record in the domain and is not frozen, so any holder can "
                    "change it under every other holder. Declare it `frozen=True`, or say on the "
                    "decorator's line or the one above why this one has identity and changes",
                )
            )


def _receiver(node: FunctionNode, in_class: bool) -> str:
    positional = [*node.args.posonlyargs, *node.args.args]
    is_static = any(named(item) == "staticmethod" for item in node.decorator_list)
    return positional[0].arg if in_class and positional and not is_static else ""


def _method_ids(tree: ast.Module) -> set[int]:
    marked: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            marked.update(id(child) for child in node.body if isinstance(child, FUNCTION_TYPES))
    return marked


def _containers(arguments: list[ast.arg]) -> set[str]:
    """The parameters annotated as a mutable container, which `+=` and `|=` change in place."""
    found: set[str] = set()
    for arg in arguments:
        outer = arg.annotation.value if isinstance(arg.annotation, ast.Subscript) else arg.annotation
        if outer is not None and named(outer) in CONTAINER_ANNOTATIONS:
            found.add(arg.arg)
    return found


def _mutated(node: ast.AST, names: set[str], containers: set[str]) -> str:
    """The parameter this node changes in place, or ''."""
    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id in containers:
        return node.target.id
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        owner = node.func.value
        if isinstance(owner, ast.Name) and owner.id in names and node.func.attr in MUTATORS:
            return owner.id
    targets: list[ast.expr] = []
    if isinstance(node, (ast.Assign, ast.Delete)):
        targets = list(node.targets)
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        targets = [node.target]
    for target in targets:
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id in names:
            return target.value.id
    return ""


def check_argument_mutation(source: Source, findings: list[Finding]) -> None:
    if not in_domain(source):
        return
    methods = _method_ids(source.tree)
    for node in ast.walk(source.tree):
        if not isinstance(node, FUNCTION_TYPES):
            continue
        spec = node.args
        arguments = [*spec.posonlyargs, *spec.args, *spec.kwonlyargs]
        names = {arg.arg for arg in arguments}
        names.discard(_receiver(node, id(node) in methods))
        containers = _containers(arguments) & names
        reported: set[str] = set()
        for child in statements_within(node.body):
            name = _mutated(child, names, containers)
            if name and name not in reported:
                reported.add(name)
                findings.append(_mutates_argument(source, child, node.name, name))


def _mutates_argument(source: Source, at: ast.AST, function: str, name: str) -> Finding:
    return Finding(
        where(source, at),
        "immutability",
        2,
        f"{function} changes `{name}` in place, and `{name}` is the caller's object, so the "
        "caller's value changes under it without the signature saying so. Build a new value "
        "and return it",
    )


def _patch_kind(source: Source, call: ast.Call) -> str:
    """'path' when the first argument is a dotted path, 'object' when it is a target, or ''."""
    text = written(call.func)
    if not text:
        return ""
    last = text.split(".")[-1]
    if text.startswith("monkeypatch.") and last in {"setattr", "delattr"}:
        first = call.args[0] if call.args else None
        return "path" if first is not None and is_string_literal(first) else "object"
    dotted = resolved(source, call.func)
    if dotted in MOCK_PATCHES:
        return "path"
    if last in {"object", "multiple"} and dotted.rsplit(".", 1)[0] in MOCK_PATCHES:
        return "object" if last == "object" else "path"
    return ""


def check_patches(source: Source, findings: list[Finding]) -> None:
    for call in calls(source):
        kind = _patch_kind(source, call)
        if not kind or not call.args:
            continue
        first = call.args[0]
        if kind == "path" and isinstance(first, ast.Constant) and isinstance(first.value, str):
            target = first.value
        elif kind == "object":
            target = resolved(source, first)
        else:
            continue
        if layers_of(target):
            findings.append(_patches_inside(source, call, first, target))


def _patches_inside(source: Source, call: ast.Call, first: ast.expr, target: str) -> Finding:
    shown = written(first) or target
    layer = sorted(layers_of(target))[0]
    return Finding(
        where(source, call),
        "testing",
        1,
        f"this patches `{shown}`, which resolves to `{target}` in the {layer} layer, so the "
        "test runs against a replacement of the code it exists to check. Double the port the "
        "code depends on instead, at the adapter, and let the domain and the use cases run",
    )


def _security(source: Source, call: ast.Call, condition: int, message: str) -> Finding:
    return Finding(
        where(source, call),
        "security",
        condition,
        f"{message}. Where the input is trusted, say why in a comment on this line or the one above",
    )


def check_evaluators(source: Source, findings: list[Finding]) -> None:
    for call in calls(source):
        if not (isinstance(call.func, ast.Name) and call.func.id in {"eval", "exec"}):
            continue
        if call.args and is_string_literal(call.args[0]):
            continue
        if not justified(source, call.lineno):
            findings.append(
                _security(
                    source,
                    call,
                    1,
                    f"`{call.func.id}` runs a value as Python, with the program's whole authority, "
                    "and whoever controls the value writes the program",
                )
            )


def _yaml_is_safe(call: ast.Call) -> bool:
    loader = keyword(call, "Loader")
    if loader is None and len(call.args) > 1:
        loader = call.args[1]
    return loader is not None and named(loader) in SAFE_YAML_LOADERS


def check_loaders(source: Source, findings: list[Finding]) -> None:
    for call in calls(source):
        dotted = resolved(source, call.func)
        unsafe = dotted in OBJECT_LOADERS or (dotted in YAML_LOADERS and not _yaml_is_safe(call))
        if unsafe and not justified(source, call.lineno):
            findings.append(
                _security(
                    source,
                    call,
                    2,
                    f"`{dotted}` builds whatever objects the bytes name and runs their code while "
                    "it does, so loading bytes someone else wrote runs code someone else wrote. "
                    "Load a data-only format, or a YAML safe loader",
                )
            )


def check_shells(source: Source, findings: list[Finding]) -> None:
    for call in calls(source):
        dotted = resolved(source, call.func)
        shell = dotted in ALWAYS_SHELL or (dotted in SHELL_ON_REQUEST and is_constant(keyword(call, "shell"), True))
        if not shell or (call.args and is_string_literal(call.args[0])):
            continue
        if not justified(source, call.lineno):
            findings.append(
                _security(
                    source,
                    call,
                    3,
                    f"`{dotted}` hands a built string to a shell, which reads `;`, `|`, `$()` and "
                    "spaces in whatever was spliced into it. Pass an argument list with `shell` off",
                )
            )


def _zip_archives(source: Source) -> set[str]:
    """The names this file binds to a `zipfile.ZipFile`, which sanitises member names itself."""
    bound: set[str] = set()
    for node in ast.walk(source.tree):
        pairs: list[tuple[ast.expr | None, ast.expr]] = []
        if isinstance(node, (ast.With, ast.AsyncWith)):
            pairs = [(item.optional_vars, item.context_expr) for item in node.items]
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            pairs = [(node.targets[0], node.value)]
        for target, value in pairs:
            opened = isinstance(value, ast.Call) and resolved(source, value.func) == "zipfile.ZipFile"
            if opened and isinstance(target, ast.Name):
                bound.add(target.id)
    return bound


def check_archives(source: Source, findings: list[Finding]) -> None:
    if not any(origin.split(".")[0] == "tarfile" for origin in source.imports.values()):
        return
    zips = _zip_archives(source)
    for call in calls(source):
        if named(call.func) not in {"extractall", "extract"} or not isinstance(call.func, ast.Attribute):
            continue
        if isinstance(call.func.value, ast.Name) and call.func.value.id in zips:
            continue
        if keyword(call, "filter") is not None or justified(source, call.lineno):
            continue
        findings.append(
            _security(
                source,
                call,
                4,
                f"`{named(call.func)}` writes each member where its stored name says, and a tar "
                "member may be named `../../etc/cron.d/x` or be a link out of the target. Pass "
                '`filter="data"`, which every interpreter from 3.12 accepts',
            )
        )


def check_tls(source: Source, findings: list[Finding]) -> None:
    for call in calls(source):
        dotted = resolved(source, call.func)
        off = is_constant(keyword(call, "verify"), False)
        if not (off or dotted in UNVERIFIED_CONTEXTS) or justified(source, call.lineno):
            continue
        what = "`verify=False`" if off else f"`{dotted}`"
        findings.append(
            _security(
                source,
                call,
                5,
                f"{what} turns certificate verification off, so anyone on the path can answer in "
                "the server's name and read what is sent. Point the client at the right CA bundle",
            )
        )


CHECKS = (
    check_base_handlers,
    check_vanilla_raises,
    check_finally_exits,
    check_records,
    check_argument_mutation,
    check_patches,
    check_evaluators,
    check_loaders,
    check_shells,
    check_archives,
    check_tls,
)


def report(findings: list[Finding], checked: int, unparsed: int) -> int:
    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if not findings:
        print(f"{checked} file(s), no failures{suffix}.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
    for finding in sorted(findings, key=lambda item: (item.where, item.rule, item.condition)):
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = 0
    unparsed = 0

    try:
        paths = sources(roots)
    except MissingPath as missing:
        print(missing, file=sys.stderr)
        return 2
    for path in paths:
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
