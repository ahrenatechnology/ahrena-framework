#!/usr/bin/env python3
"""Detector for the Go package-boundaries rule.

Decides two conditions of engineering/go/rules/package-boundaries.md, the two
the compiler does not:

    2. a package in a layer imports no first-party package in a layer above
       it: domain ranks below application, which ranks below infra
    3. the modules of one repository do not require one another in a cycle

The compiler already refuses an import cycle between packages, which is
condition 1 and is not decided here. It does not refuse a package importing
the wrong way across layers, because to the compiler a layer is only a
directory; and the go command does not refuse a requirement cycle between
modules, because minimal version selection was designed to tolerate one.

Both conditions need the whole tree rather than one file, so this hook builds
the first-party module and package maps before it reads an import. It reads Go
through golex.py, beside it, and needs nothing but the Python standard library.

Usage:
    python3 engineering/go/hooks/check-packages.py [path ...]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from golex import Finding, display, imports, load, report, sources, skipped  # noqa: E402

LAYERS = ("domain", "application", "infra")

MODULE_LINE = re.compile(r"^module\s+(\S+)", re.MULTILINE)

REQUIRE_BLOCK = re.compile(r"^require\s*\((.*?)^\)", re.MULTILINE | re.DOTALL)

REQUIRE_LINE = re.compile(r"^require\s+(\S+)\s", re.MULTILINE)


@dataclass(frozen=True)
class Module:
    path: str
    root: Path
    requires: tuple[str, ...]


def read_module(go_mod: Path) -> Module | None:
    text = go_mod.read_text(encoding="utf-8", errors="replace")
    found = MODULE_LINE.search(text)
    if found is None:
        return None
    requires = [line.split()[0] for block in REQUIRE_BLOCK.findall(text) for line in block.splitlines() if line.split()]
    requires += REQUIRE_LINE.findall(text)
    return Module(found.group(1).strip('"'), go_mod.parent, tuple(r for r in requires if not r.startswith("//")))


def modules_in(roots: list[Path]) -> list[Module]:
    found: list[Module] = []
    for root in roots:
        walk = [root] if root.is_file() else root.rglob("go.mod")
        for go_mod in walk:
            if go_mod.name == "go.mod" and not skipped(go_mod.relative_to(root) if root.is_dir() else Path(go_mod.name)):
                module = read_module(go_mod)
                found += [module] if module else []
    return found


def layer_rank(relative: str) -> tuple[int, str] | None:
    """The rank and name of the first layer segment in a package path, if any."""
    for part in relative.split("/"):
        if part in LAYERS:
            return LAYERS.index(part), part
    return None


def first_party(import_path: str, modules: list[Module]) -> str | None:
    """The package's path inside its first-party module, or None for a third-party import."""
    owners = [m for m in modules if import_path == m.path or import_path.startswith(m.path + "/")]
    if not owners:
        return None
    owner = max(owners, key=lambda m: len(m.path))
    return import_path[len(owner.path) + 1 :] if import_path != owner.path else ""


def owning_module(path: Path, modules: list[Module]) -> Module | None:
    owners = [m for m in modules if m.root in path.parents]
    return max(owners, key=lambda m: len(m.root.parts)) if owners else None


def check_layers(path: Path, base: Path, modules: list[Module], findings: list[Finding]) -> None:
    source = load(path, base)
    module = owning_module(path, modules)
    if source is None or module is None or path.name.endswith("_test.go"):
        return
    here = layer_rank(path.parent.relative_to(module.root).as_posix())
    if here is None:
        return
    for import_path in imports(source.tokens):
        relative = first_party(import_path, modules)
        there = layer_rank(relative) if relative is not None else None
        if there is not None and there[0] > here[0]:
            findings.append(
                Finding(
                    f"{source.rel}:1",
                    "package-boundaries",
                    2,
                    f"a package in the {here[1]} layer imports {import_path}, in the {there[1]} layer; "
                    f"the direction is {' < '.join(LAYERS)}, and an import points down it, never up",
                )
            )


def cycle_from(start: str, graph: dict[str, list[str]]) -> list[str] | None:
    """A requirement cycle through `start`, as the module paths in order, or None."""
    stack: list[tuple[str, list[str]]] = [(start, [start])]
    while stack:
        node, trail = stack.pop()
        for nxt in graph.get(node, []):
            if nxt == start:
                return trail + [start]
            if nxt not in trail:
                stack.append((nxt, trail + [nxt]))
    return None


def check_module_cycles(modules: list[Module], base: Path, findings: list[Finding]) -> None:
    paths = {m.path for m in modules}
    graph = {m.path: [r for r in m.requires if r in paths] for m in modules}
    seen: set[frozenset[str]] = set()
    for module in sorted(modules, key=lambda m: m.path):
        cycle = cycle_from(module.path, graph)
        if cycle is None or frozenset(cycle) in seen:
            continue
        seen.add(frozenset(cycle))
        findings.append(
            Finding(
                f"{display(module.root / 'go.mod', base)}:1",
                "package-boundaries",
                3,
                f"the modules require one another in a cycle: {' -> '.join(cycle)}",
            )
        )


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    modules = modules_in(roots)
    findings: list[Finding] = []
    files = sources(roots)
    for path in files:
        check_layers(path, base, modules, findings)
    check_module_cycles(modules, base, findings)
    return report(findings, len(files))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
