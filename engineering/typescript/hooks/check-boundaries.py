#!/usr/bin/env python3
"""Detector for the module-boundary conditions in the TypeScript engineering rule.

Decides every condition stated in engineering/typescript/rules/module-boundaries.md:

    1. the first-party import graph is acyclic; a type-only import is not an
       edge, because the compiler erases it
    2. a dynamic `import()` and a `require()` are edges like any other, and a
       cycle that runs through one is reported with that edge marked deferred
    3. a relative import does not reach into another package's directory
    4. a first-party package imported by name is imported at its root or at a
       subpath its `exports` declares
    5. the workspace's package graph - each package.json's dependency fields
       naming another package in the tree - is acyclic
    6. a first-party package imported by name is declared in the importing
       package's package.json

The graph is built from the source with the lexical scan in tssource.py and
the resolution rules TypeScript applies under `moduleResolution: nodenext`
and `bundler`: a `.js` specifier reaches the `.ts` file beside it, an
extensionless one tries each extension and then the directory's index. A
specifier that resolves to no file in the tree is a third party's and adds no
edge.

`SPECIFIER` finds a string that is a module specifier: after `from`, after a
bare `import`, or as the argument of `import(` or `require(`. It is matched on
the blanked code, where the quotes survive and the text between them does
not, and the specifier is read from the raw text. `SWAPS` is what a
`.js`-family specifier may name on disk, as TypeScript maps it.

Usage:
    python3 engineering/typescript/hooks/check-boundaries.py [path ...]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json  # noqa: E402
import re  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402

from tssource import SCRIPT, Finding, Source, display, load, report, walk  # noqa: E402

RULE = "module-boundaries"

SPECIFIER = re.compile(r"(?:\bfrom\s*|\bimport\s*|\b(import|require)\s*\(\s*)([\"'])")
STATEMENT = re.compile(r"\b(import|export)\b")

SWAPS = {".js": (".ts", ".tsx", ".js", ".jsx"), ".mjs": (".mts", ".mjs"), ".cjs": (".cts", ".cjs"), ".jsx": (".tsx", ".jsx")}


@dataclass(frozen=True)
class Edge:
    target: Path
    line: int
    deferred: bool


@dataclass
class Package:
    """A package.json in the tree: its name, directory, `exports` (None when absent) and declared dependencies."""

    name: str
    root: Path
    exports: object
    depends: frozenset[str]


DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


def declared(data: dict[str, object]) -> frozenset[str]:
    names: set[str] = set()
    for field in DEPENDENCY_FIELDS:
        value = data.get(field)
        if isinstance(value, dict):
            names.update(key for key in value if isinstance(key, str))
    return frozenset(names)


def specifier_at(source: Source, quote: int) -> str:
    end = source.text.find(source.text[quote], quote + 1)
    return source.text[quote + 1 : end] if end != -1 else ""


def type_only(statement: str) -> bool:
    """Whether an import or export clause is erased by the compiler.

    Only the statement-level `type` is erased whole. `import { type A }`
    keeps the import: under verbatimModuleSyntax it is rewritten to
    `import {} from "a"`, which still loads and evaluates the module.
    """
    clause = re.sub(r"^\s*(import|export)\s+", "", statement)
    return clause.startswith("type ") or clause.startswith("type{")


def imports_of(source: Source) -> list[tuple[str, int, bool, bool]]:
    """Each specifier, with its line, whether it is deferred, whether type-only."""
    found = []
    for match in SPECIFIER.finditer(source.code):
        quote = match.start(2)
        specifier = specifier_at(source, quote)
        line = source.line(quote)
        if match.group(1):
            found.append((specifier, line, match.group(1) == "import", False))
            continue
        keywords = list(STATEMENT.finditer(source.code, 0, match.start()))
        if not keywords:
            continue
        statement = source.code[keywords[-1].start() : match.start()]
        found.append((specifier, line, False, type_only(statement)))
    return found


def resolve_relative(importer: Path, specifier: str, known: set[Path]) -> Path | None:
    target = (importer.parent / specifier).resolve()
    candidates: list[Path] = [target]
    for suffix, swaps in SWAPS.items():
        if target.name.endswith(suffix):
            stem = target.with_name(target.name[: -len(suffix)])
            candidates = [stem.with_name(stem.name + swap) for swap in swaps]
    candidates += [target.with_name(target.name + suffix) for suffix in SCRIPT]
    candidates += [target / f"index{suffix}" for suffix in SCRIPT]
    for candidate in candidates:
        if candidate in known:
            return candidate
    return None


def packages_in(roots: list[Path]) -> list[Package]:
    found = []
    for path in walk(roots, ("package.json",)):
        if path.name != "package.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            found.append(Package(data["name"], path.parent.resolve(), data.get("exports"), declared(data)))
    return found


def owner(path: Path, packages: list[Package]) -> Package | None:
    holding = [package for package in packages if package.root in path.parents]
    return max(holding, key=lambda package: len(package.root.parts)) if holding else None


def split_bare(specifier: str) -> tuple[str, str]:
    parts = specifier.split("/")
    count = 2 if specifier.startswith("@") else 1
    return "/".join(parts[:count]), "/".join(parts[count:])


def exported_subpaths(exports: object) -> list[str]:
    if isinstance(exports, dict) and any(isinstance(key, str) and key.startswith(".") for key in exports):
        return [key for key in exports if isinstance(key, str) and key.startswith(".")]
    return ["."] if exports is not None else []


def exports_allow(exports: object, subpath: str) -> bool:
    wanted = f"./{subpath}"
    for key in exported_subpaths(exports):
        if key == wanted:
            return True
        if key.count("*") == 1:
            head, tail = key.split("*")
            if wanted.startswith(head) and wanted.endswith(tail) and len(wanted) >= len(head) + len(tail):
                return True
    return False


def finish_order(graph: dict[Path, list[Edge]]) -> list[Path]:
    """Every node, in the order a depth-first search finishes it."""
    order: list[Path] = []
    seen: set[Path] = set()
    for start in sorted(graph):
        if start in seen:
            continue
        seen.add(start)
        work = [(start, iter(graph[start]))]
        while work:
            node, edges = work[-1]
            target = next((edge.target for edge in edges if edge.target not in seen), None)
            if target is None:
                work.pop()
                order.append(node)
                continue
            seen.add(target)
            work.append((target, iter(graph.get(target, []))))
    return order


def reached(reverse: dict[Path, list[Path]], start: Path, assigned: set[Path]) -> list[Path]:
    """The nodes that reach `start` and belong to no component yet."""
    component = [start]
    assigned.add(start)
    work = [start]
    while work:
        for source in reverse.get(work.pop(), []):
            if source not in assigned:
                assigned.add(source)
                component.append(source)
                work.append(source)
    return component


def strongly_connected(graph: dict[Path, list[Edge]]) -> list[list[Path]]:
    """Kosaraju's two passes, both iterative so a deep tree does not exhaust the stack."""
    reverse: dict[Path, list[Path]] = {}
    for node, edges in graph.items():
        for edge in edges:
            reverse.setdefault(edge.target, []).append(node)
    assigned: set[Path] = set()
    return [reached(reverse, node, assigned) for node in reversed(finish_order(graph)) if node not in assigned]


def cycle_in(component: list[Path], graph: dict[Path, list[Edge]]) -> list[tuple[Path, Edge]]:
    """One loop through a strongly connected component, from its first member."""
    members = set(component)
    start = min(component)
    path: list[tuple[Path, Edge]] = []
    visited: set[Path] = set()

    def search(node: Path) -> bool:
        visited.add(node)
        for edge in graph.get(node, []):
            if edge.target not in members:
                continue
            path.append((node, edge))
            if edge.target == start:
                return True
            if edge.target not in visited and search(edge.target):
                return True
            path.pop()
        return False

    search(start)
    return path


def check_cycles(graph: dict[Path, list[Edge]], base: Path, findings: list[Finding]) -> None:
    for component in strongly_connected(graph):
        looped = len(component) > 1 or any(edge.target == component[0] for edge in graph.get(component[0], []))
        if not looped:
            continue
        loop = cycle_in(component, graph)
        steps = [
            f"{display(node, base)}:{edge.line} -> {display(edge.target, base)}" + (" (deferred)" if edge.deferred else "")
            for node, edge in loop
        ]
        where = display(loop[0][0], base) if loop else display(min(component), base)
        findings.append(Finding(RULE, where, 1, "import cycle; delete one of these edges:\n      " + "\n      ".join(steps)))


@dataclass
class Tree:
    """What every file is checked against: the files that exist, the packages that hold them, and the graph being built."""

    known: set[Path]
    packages: list[Package]
    graph: dict[Path, list[Edge]]


def check_file(source: Source, tree: Tree, findings: list[Finding]) -> None:
    path, packages = source.path, tree.packages
    by_name = {package.name: package for package in packages}
    mine = owner(path, packages)
    for specifier, line, deferred, erased in imports_of(source):
        where = f"{source.rel}:{line}"
        if specifier.startswith("."):
            target = resolve_relative(path, specifier, tree.known)
            if target is None:
                continue
            theirs = owner(target, packages)
            if theirs is not None and theirs is not mine:
                findings.append(
                    Finding(RULE, where, 3, f"reaches into {theirs.name} by path ({specifier}); import it by its name and exported entry")
                )
            if not erased:
                tree.graph.setdefault(path, []).append(Edge(target, line, deferred))
            continue
        name, subpath = split_bare(specifier)
        package = by_name.get(name)
        if package is None or package is mine:
            continue
        if mine is not None and name not in mine.depends:
            manifest = display(mine.root / "package.json", Path.cwd())
            findings.append(Finding(RULE, where, 6, f"imports {name}, which {manifest} does not declare; add it with the workspace protocol"))
        if not subpath or exports_allow(package.exports, subpath):
            continue
        if package.exports is None:
            reason = f"{name} declares no exports, so {specifier} is a file, not an entry; add it to exports or import the root"
        else:
            reason = f"{specifier} is not in {name}'s exports; import an exported entry, or export this one on purpose"
        findings.append(Finding(RULE, where, 4, reason))


def check_package_graph(packages: list[Package], base: Path, findings: list[Finding]) -> None:
    """Condition 5: the first-party package graph, read from the manifests, has no cycle."""
    names = {package.name: package for package in packages}
    graph = {
        package.root / "package.json": [Edge(names[name].root / "package.json", 0, False) for name in sorted(package.depends) if name in names]
        for package in packages
    }
    by_manifest = {package.root / "package.json": package.name for package in packages}
    for component in strongly_connected(graph):
        if len(component) < 2 and not any(edge.target == component[0] for edge in graph.get(component[0], [])):
            continue
        loop = cycle_in(component, graph)
        chain = " -> ".join([by_manifest[node] for node, _ in loop] + [by_manifest[loop[0][0]]])
        where = display(loop[0][0], base)
        findings.append(Finding(RULE, where, 5, f"package cycle {chain}; one of these dependencies has to go, or the shared part becomes its own package"))


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    files = [path.resolve() for path in walk(roots, SCRIPT)]
    known = set(files)
    packages = packages_in(roots)
    tree = Tree(known, packages, {path: [] for path in files})
    findings: list[Finding] = []
    for path in files:
        check_file(load(path, display(path, base)), tree, findings)
    check_cycles(tree.graph, base, findings)
    check_package_graph(packages, base, findings)
    return report(findings, len(files))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
