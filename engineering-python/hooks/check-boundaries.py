#!/usr/bin/env python3
"""Detector for the module-boundary conditions in the Python engineering rule.

Decides the six conditions stated in engineering-python/rules/module-boundaries.md:

    1. the first-party import graph is acyclic
    2. a layer imports only downward: infra to application to domain
    3. a deferred import is the same edge as a module-level one
    4. a TYPE_CHECKING import is an edge only when a name it binds is loaded
       outside an annotation
    5. the namespace root and each context directory carry no __init__.py
    6. each layer directory carries its own pyproject.toml

Conditions 3 and 4 decide which edges exist rather than raising findings of
their own; their effect surfaces in conditions 1 and 2.

The graph is built with `ast`. A regular expression over source is a detector
that stops matching the first time somebody reformats, and an import graph is
exactly the subject where that matters: the workaround this rule rejects is a
reformatting.

Standard library only. The hook ships inside the plugin, so a consumer runs the
same check CI runs without installing anything.

Usage:
    python3 engineering-python/hooks/check-boundaries.py [import-root ...]

Each argument is a directory that is on sys.path at runtime, because that is
what a dotted import name resolves against. With no argument the hook uses the
working directory.
"""

from __future__ import annotations

import ast
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

RULE = "module-boundaries"

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

FUNC_NODES: tuple[type, ...] = (ast.FunctionDef, ast.AsyncFunctionDef)

# The map this rule ships, rather than one a reviewer supplies per repository.
# Policy ranks below mechanism and an import may only run down the ranks.
LAYERS = {"domain": 0, "application": 1, "infra": 2}
LAYER_ORDER = "infra to application to domain"
NAMESPACE_DIR = "components"
DISTRIBUTION_FILE = "pyproject.toml"


# --- findings --------------------------------------------------------------


@dataclass
class Finding:
    where: str  # path, with :line where a line exists
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


# --- the nodes -------------------------------------------------------------


@dataclass(frozen=True)
class Module:
    """One module file. The node of the graph, and the unit Python executes.

    A package is not a node. Two modules in different packages that import each
    other's neighbours form no runtime cycle, and collapsing them onto their
    packages would report one. An `__init__.py` is a node like any other,
    because Python executes it like any other.
    """

    path: Path
    rel: str  # for reporting, relative to the working directory
    root: Path  # the import root its dotted name resolves against
    parts: tuple[str, ...]  # its own dotted name, as a tuple


def package_of(module: Module) -> tuple[str, ...]:
    """The dotted name of the package a relative import resolves against."""
    if module.path.name == "__init__.py":
        return module.parts
    return module.parts[:-1]


def display(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def discover(roots: list[Path], base: Path) -> dict[Path, Module]:
    modules: dict[Path, Module] = {}
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(root)
            if not SKIP_DIRS.isdisjoint(relative.parts):
                continue
            named = relative.with_suffix("").parts
            parts = named[:-1] if named[-1] == "__init__" else named
            modules[path] = Module(path, display(path, base), root, parts)
    return modules


# --- resolution ------------------------------------------------------------


def resolve(parts: tuple[str, ...], root: Path, modules: dict[Path, Module]) -> Path | None:
    """The module a dotted name names, or None when it is not first-party.

    Membership is tested against the discovered set rather than the filesystem,
    so a vendored or generated tree that the walk skipped is not linked into
    the graph by an import that happens to name it.
    """
    if not parts:
        return None
    base = root.joinpath(*parts)
    module = base.parent / f"{base.name}.py"
    if module in modules:
        return module
    initializer = base / "__init__.py"
    if initializer in modules:
        return initializer
    return None


def ancestor_initializers(
    parts: tuple[str, ...], importer: tuple[str, ...], root: Path, modules: dict[Path, Module]
) -> list[Path]:
    """The package initializers Python runs on the way to `parts`.

    Only the ones the importer does not already live inside. A module's own
    package initializer has finished, or is the thing that triggered the
    module, by the time the module runs; adding that edge would report every
    package whose `__init__.py` re-exports its own submodules.
    """
    found = []
    for depth in range(1, len(parts)):
        prefix = parts[:depth]
        if importer[:depth] == prefix:
            continue
        initializer = root.joinpath(*prefix) / "__init__.py"
        if initializer in modules:
            found.append(initializer)
    return found


# --- reading one module ----------------------------------------------------


@dataclass
class RawImport:
    node: ast.AST
    deferred: bool  # condition 3: the statement sits inside a function body
    guarded: bool  # condition 4: the statement sits under `if TYPE_CHECKING:`


def _is_type_checking(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _statement_blocks(node: ast.AST) -> list[list[ast.stmt]]:
    blocks: list[list[ast.stmt]] = []
    for name in ("body", "orelse", "finalbody"):
        stmts = getattr(node, name, None)
        if isinstance(stmts, list):
            blocks.append(stmts)
    for handler in getattr(node, "handlers", []):
        blocks.append(handler.body)
    for branch in getattr(node, "cases", []):
        blocks.append(branch.body)
    return blocks


def collect_imports(tree: ast.Module) -> list[RawImport]:
    """Every import statement, carrying where it sits."""
    found: list[RawImport] = []
    stack = [(stmt, False, False) for stmt in reversed(tree.body)]
    while stack:
        node, deferred, guarded = stack.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found.append(RawImport(node, deferred, guarded))
            continue
        if isinstance(node, FUNC_NODES):
            stack.extend((child, True, guarded) for child in reversed(node.body))
            continue
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            stack.extend((child, deferred, True) for child in reversed(node.body))
            stack.extend((child, deferred, guarded) for child in reversed(node.orelse))
            continue
        for block in _statement_blocks(node):
            stack.extend((child, deferred, guarded) for child in reversed(block))
    return found


def _annotation_names(tree: ast.Module) -> set[int]:
    """Identities of the Name nodes that sit inside a type annotation."""
    holders: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            holders.append(node.annotation)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            holders.append(node.annotation)
        elif isinstance(node, FUNC_NODES) and node.returns is not None:
            holders.append(node.returns)
    marked = set()
    for holder in holders:
        marked.update(id(sub) for sub in ast.walk(holder) if isinstance(sub, ast.Name))
    return marked


def runtime_names(tree: ast.Module) -> set[str]:
    """Names loaded somewhere other than an annotation.

    Condition 4 turns on this set. A `TYPE_CHECKING` import whose names appear
    only here is not a cycle-breaker, it is a NameError waiting to happen, and
    the coupling it hides is the same coupling a plain import declares.
    """
    marked = _annotation_names(tree)
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and id(node) not in marked
    }


# --- the edges -------------------------------------------------------------


@dataclass(frozen=True)
class Edge:
    source: Path
    target: Path
    line: int
    deferred: bool
    implied: bool  # a package initializer on the path, not a written import


def _plain_candidates(node: ast.Import) -> list[tuple[str, tuple[str, ...], str]]:
    candidates = []
    for alias in node.names:
        parts = tuple(alias.name.split("."))
        candidates.append((alias.asname or parts[0], parts, ""))
    return candidates


def _from_base(node: ast.ImportFrom, module: Module) -> tuple[str, ...] | None:
    """Where a `from ... import ...` starts, relative imports included."""
    tail = tuple(node.module.split(".")) if node.module else ()
    if node.level == 0:
        return tail or None
    package = package_of(module)
    upward = node.level - 1
    if upward > len(package):
        return None
    base = package[: len(package) - upward] + tail
    return base or None


def _from_candidates(node: ast.ImportFrom, module: Module) -> list[tuple[str, tuple[str, ...], str]]:
    base = _from_base(node, module)
    if base is None:
        return []
    return [(alias.asname or alias.name, base, alias.name) for alias in node.names]


def _target_for(
    base: tuple[str, ...], attribute: str, root: Path, modules: dict[Path, Module]
) -> tuple[Path | None, tuple[str, ...]]:
    """`from pkg import name` reaches a submodule when one exists, the package otherwise."""
    if attribute and attribute != "*":
        submodule = resolve(base + (attribute,), root, modules)
        if submodule is not None:
            return submodule, base + (attribute,)
    return resolve(base, root, modules), base


def build_edges(module: Module, tree: ast.Module, modules: dict[Path, Module]) -> list[Edge]:
    runtime = runtime_names(tree)
    edges: list[Edge] = []
    for raw in collect_imports(tree):
        node = raw.node
        candidates = (
            _plain_candidates(node) if isinstance(node, ast.Import) else _from_candidates(node, module)
        )
        for bound, base, attribute in candidates:
            if raw.guarded and bound != "*" and bound not in runtime:
                continue
            target, parts = _target_for(base, attribute, module.root, modules)
            if target is None or target == module.path:
                continue
            edges.append(Edge(module.path, target, node.lineno, raw.deferred, False))
            edges.extend(
                Edge(module.path, initializer, node.lineno, raw.deferred, True)
                for initializer in ancestor_initializers(parts, module.parts, module.root, modules)
            )
    return edges


# --- condition 1: the graph is acyclic -------------------------------------


def components(graph: dict[Path, list[Path]]) -> list[list[Path]]:
    """Tarjan's strongly connected components, iteratively.

    Iteratively because a real repository's import graph is deeper than the
    interpreter's recursion limit, and a gate that crashes on a large tree is
    a gate people turn off.
    """
    index: dict[Path, int] = {}
    low: dict[Path, int] = {}
    stack: list[Path] = []
    on_stack: set[Path] = set()
    found: list[list[Path]] = []
    counter = 0

    def enter(node: Path) -> None:
        nonlocal counter
        index[node] = low[node] = counter
        counter += 1
        stack.append(node)
        on_stack.add(node)

    for start in sorted(graph):
        if start in index:
            continue
        enter(start)
        work = [(start, iter(graph[start]))]
        while work:
            node, pending = work[-1]
            descended = _descend(node, pending, index, low, on_stack, enter, work, graph)
            if descended:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                found.append(_pop_component(node, stack, on_stack))
    return found


def _descend(node, pending, index, low, on_stack, enter, work, graph) -> bool:
    for nxt in pending:
        if nxt not in index:
            enter(nxt)
            work.append((nxt, iter(graph.get(nxt, []))))
            return True
        if nxt in on_stack:
            low[node] = min(low[node], index[nxt])
    return False


def _pop_component(node: Path, stack: list[Path], on_stack: set[Path]) -> list[Path]:
    group = []
    while True:
        member = stack.pop()
        on_stack.discard(member)
        group.append(member)
        if member == node:
            return group


def shortest_cycle(graph: dict[Path, list[Path]], group: set[Path], start: Path) -> list[Path]:
    """A concrete path from `start` back to `start`, so the report is the cycle."""
    queue = deque([[start]])
    seen = {start}
    while queue:
        path = queue.popleft()
        for nxt in sorted(graph.get(path[-1], [])):
            if nxt == start:
                return path + [start]
            if nxt in group and nxt not in seen:
                seen.add(nxt)
                queue.append(path + [nxt])
    return []


def _arrow(cycle: list[Path], modules: dict[Path, Module], edges: dict[tuple[Path, Path], Edge]) -> str:
    pieces = []
    for position, node in enumerate(cycle[:-1]):
        edge = edges[(node, cycle[position + 1])]
        mark = " (deferred)" if edge.deferred else ""
        pieces.append(f"{modules[node].rel}:{edge.line}{mark}")
    pieces.append(modules[cycle[-1]].rel)
    return " -> ".join(pieces)


def check_cycles(
    graph: dict[Path, list[Path]],
    modules: dict[Path, Module],
    edges: dict[tuple[Path, Path], Edge],
    findings: list[Finding],
) -> None:
    for group in components(graph):
        members = set(group)
        start = min(group, key=lambda node: modules[node].rel)
        if len(group) == 1 and start not in graph.get(start, []):
            continue
        cycle = shortest_cycle(graph, members, start)
        if not cycle:
            continue
        deferred = any(edges[(cycle[i], cycle[i + 1])].deferred for i in range(len(cycle) - 1))
        implied = any(edges[(cycle[i], cycle[i + 1])].implied for i in range(len(cycle) - 1))
        message = f"import cycle through {len(cycle) - 1} module(s): {_arrow(cycle, modules, edges)}"
        if deferred:
            message += (
                "; an import moved inside a function is the same edge, so deferring it "
                "does not break this cycle, it only hides it from a naive detector"
            )
        if implied:
            message += (
                "; an arrow into an __init__.py is the package initializer Python runs "
                "before the submodule that was named"
            )
        first = edges[(cycle[0], cycle[1])]
        findings.append(Finding(f"{modules[cycle[0]].rel}:{first.line}", 1, message))


# --- condition 2: a layer imports only downward ----------------------------


def layer_of(module: Module) -> tuple[str, str] | None:
    parts = module.path.relative_to(module.root).parts
    for position, part in enumerate(parts):
        if part != NAMESPACE_DIR or position + 2 >= len(parts):
            continue
        context, layer = parts[position + 1], parts[position + 2]
        if layer in LAYERS:
            return context, layer
    return None


def check_direction(
    edges: dict[tuple[Path, Path], Edge], modules: dict[Path, Module], findings: list[Finding]
) -> None:
    for (source, target), edge in sorted(edges.items()):
        if edge.implied:
            continue  # the written import beside it already carries the finding
        here, there = layer_of(modules[source]), layer_of(modules[target])
        if here is None or there is None or LAYERS[there[1]] <= LAYERS[here[1]]:
            continue
        message = (
            f"{modules[source].rel} is in the {here[1]} layer and imports {modules[target].rel}, "
            f"which is in the {there[1]} layer; the direction is {LAYER_ORDER} and never back"
        )
        if edge.deferred:
            message += ", and a deferred import keeps the coupling, it only moves it"
        findings.append(Finding(f"{modules[source].rel}:{edge.line}", 2, message))


# --- conditions 5 and 6: the packaging the layers ride on ------------------


def namespace_roots(roots: list[Path]) -> list[Path]:
    found = []
    for root in roots:
        for directory in sorted(root.rglob(NAMESPACE_DIR)):
            relative = directory.relative_to(root)
            if directory.is_dir() and SKIP_DIRS.isdisjoint(relative.parts):
                found.append(directory)
    return found


def _subdirectories(directory: Path) -> list[Path]:
    return sorted(child for child in directory.iterdir() if child.is_dir() and child.name not in SKIP_DIRS)


def check_packaging(roots: list[Path], base: Path, findings: list[Finding]) -> None:
    for namespace in namespace_roots(roots):
        _check_namespace(namespace, base, findings)
        for context in _subdirectories(namespace):
            _check_namespace(context, base, findings)
            _check_distributions(context, base, findings)


def _check_namespace(directory: Path, base: Path, findings: list[Finding]) -> None:
    initializer = directory / "__init__.py"
    if not initializer.is_file():
        return
    findings.append(
        Finding(
            display(initializer, base),
            5,
            f"{NAMESPACE_DIR}/ is a PEP 420 namespace root and its contexts are namespace "
            "levels; an __init__.py here makes the namespace a regular package and stops a "
            "second distribution contributing to it",
        )
    )


def _check_distributions(context: Path, base: Path, findings: list[Finding]) -> None:
    for layer in _subdirectories(context):
        if layer.name not in LAYERS or (layer / DISTRIBUTION_FILE).is_file():
            continue
        findings.append(
            Finding(
                display(layer, base),
                6,
                f"the {layer.name} layer has no {DISTRIBUTION_FILE}; a layer ships as its own "
                "distribution so its dependency set stays off the consumers of the layers "
                "below it",
            )
        )


# --- entry point -----------------------------------------------------------


def parse(module: Module) -> ast.Module | None:
    try:
        return ast.parse(module.path.read_text(encoding="utf-8"), filename=str(module.path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        print(f"{module.rel}\n    skipped, this interpreter cannot parse it: {exc}", file=sys.stderr)
        return None


def main(argv: list[str]) -> int:
    roots = [Path(a).resolve() for a in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    modules = discover(roots, base)

    findings: list[Finding] = []
    edges: dict[tuple[Path, Path], Edge] = {}
    graph: dict[Path, list[Path]] = {path: [] for path in modules}
    checked = 0
    unparsed = 0

    for path in sorted(modules):
        tree = parse(modules[path])
        if tree is None:
            unparsed += 1
            continue
        for edge in build_edges(modules[path], tree, modules):
            if (edge.source, edge.target) in edges:
                continue
            edges[(edge.source, edge.target)] = edge
            graph[edge.source].append(edge.target)
        checked += 1

    check_cycles(graph, modules, edges, findings)
    check_direction(edges, modules, findings)
    check_packaging(roots, base, findings)

    suffix = f" ({unparsed} skipped)" if unparsed else ""
    if findings:
        print(f"{len(findings)} failure(s) across {checked} file(s){suffix}:\n")
        for finding in sorted(findings, key=lambda f: (f.where, f.condition)):
            print(finding)
        return 1

    print(f"{checked} file(s), no failures{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
