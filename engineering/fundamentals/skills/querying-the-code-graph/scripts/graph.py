#!/usr/bin/env python3
"""The code graph: generator and query interface, in one standard-library script.

This maintains the two-tier code graph that engineering/fundamentals/docs/
code-graph.md defines, and answers queries over it. It needs neither Graphify
nor tree-sitter to run: the light per-language index is a standard-library scan,
and the macro tier degrades to "unavailable" when Graphify is not on PATH.

Freshness is self-healing rather than gated. The cache lives in a gitignored
`.ahrena/graph/<sha>/`, keyed by the commit it describes, and every query runs a
refresh first: the generator computes the freshness key from HEAD and a marker
of the dirty working tree, and regenerates only when the key it finds does not
match. ADR-016 records why this is a cache and not a committed tree, and why the
freshness check belongs here and not in a CI gate it could never see.

Degradation is deliberate and reported, never silent:

    - Graphify absent    -> the light index still builds and answers; `explain`
                            reports the macro tier unavailable.
    - tree-sitter absent -> the light tier falls back to the `ast` scan. Python
                            is fully indexed; another language is recorded as
                            present but unindexed, which is an extension point.
    - outside a git repo -> the cache is keyed to the working tree rather than a
                            commit, and the queries still work.

Usage:
    python3 scripts/graph.py refresh
    python3 scripts/graph.py --check
    python3 scripts/graph.py doctor [--build] [--install-grammars]
    python3 scripts/graph.py locate <path-or-symbol>
    python3 scripts/graph.py deps <path-or-module>
    python3 scripts/graph.py path <from> <to>
    python3 scripts/graph.py explain <node>

references/commands.md carries the full surface, the output shapes and the exit
codes.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Directories that are never source and only slow the walk down. The same set
# the engineering structure hook skips, so the two agree on what "the tree" is.
SKIP_DIRS = frozenset(
    {
        ".git", ".hg", ".svn", ".tox", ".nox", ".venv", "venv", ".eggs",
        ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__",
        "node_modules", "build", "dist", ".ahrena",
    }
)

# The one root under which the whole graph is cached. Gitignored, so nothing
# here reaches version control and nothing here can drift against the source.
CACHE_ROOT = (".ahrena", "graph")

# Filenames a project might give its component map. Best-effort: when one is
# present the light index resolves a path to its owning component, and when none
# is, `locate` simply omits the component. Reading the map properly is the
# reading-the-component-map skill's job; this is a convenience, not that skill.
MAP_NAMES = ("component-map.yaml", "component-map.yml", "ahrena.yaml", "ahrena.yml")

# The languages the doctor reports tree-sitter grammar availability for, keyed by
# file extension. Python is special: the stdlib `ast` scan covers it with zero
# install, so a grammar is never needed for it. For every other language the
# macro tier and a richer light index want a tree-sitter grammar, whose import
# module is the value here; its pip distribution is the module with underscores
# turned to hyphens (tree_sitter_go -> tree-sitter-go).
LANGUAGE_GRAMMARS = {
    ".py": ("python", "tree_sitter_python"),
    ".js": ("javascript", "tree_sitter_javascript"),
    ".jsx": ("javascript", "tree_sitter_javascript"),
    ".mjs": ("javascript", "tree_sitter_javascript"),
    ".ts": ("typescript", "tree_sitter_typescript"),
    ".tsx": ("typescript", "tree_sitter_typescript"),
    ".go": ("go", "tree_sitter_go"),
    ".rs": ("rust", "tree_sitter_rust"),
    ".rb": ("ruby", "tree_sitter_ruby"),
    ".java": ("java", "tree_sitter_java"),
    ".c": ("c", "tree_sitter_c"),
    ".h": ("c", "tree_sitter_c"),
    ".cc": ("cpp", "tree_sitter_cpp"),
    ".cpp": ("cpp", "tree_sitter_cpp"),
    ".hpp": ("cpp", "tree_sitter_cpp"),
    ".cs": ("c_sharp", "tree_sitter_c_sharp"),
    ".php": ("php", "tree_sitter_php"),
}


# --- the repository the run is keyed to ------------------------------------


def git(root: Path, *args: str) -> str | None:
    """git's standard output, or None when git cannot answer.

    None is a first-class answer here: outside a checkout, or without git on
    PATH, the capability keys the cache to the working tree instead of refusing.
    """
    try:
        done = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True
        )
    except OSError:
        return None
    return done.stdout if done.returncode == 0 else None


def repo_root() -> Path:
    """The repository root, or the current directory outside a checkout."""
    top = git(Path.cwd(), "rev-parse", "--show-toplevel")
    return Path(top.strip()).resolve() if top else Path.cwd().resolve()


def head_sha(root: Path) -> str | None:
    top = git(root, "rev-parse", "HEAD")
    return top.strip() if top else None


def freshness_key(root: Path, sha: str | None) -> str:
    """The sha on a clean tree, the sha plus a dirty-tree digest otherwise.

    A build of a dirty tree is usable; the appended digest is what lets a later
    session tell that build apart from one of the committed tree.
    """
    if sha is None:
        porcelain = git(root, "status", "--porcelain") or ""
        return "working-" + _digest(porcelain)
    porcelain = git(root, "status", "--porcelain")
    if porcelain:
        return f"{sha}+{_digest(porcelain)}"
    return sha


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:12]


def cache_dir(root: Path, sha: str | None) -> Path:
    return root.joinpath(*CACHE_ROOT, sha or "working")


# --- which tiers this machine can build ------------------------------------


@dataclass
class Tiers:
    """What the two tiers can do on this machine, reported by every mode."""

    graphify: bool
    tree_sitter: bool

    @classmethod
    def detect(cls) -> "Tiers":
        return cls(
            graphify=shutil.which("graphify") is not None,
            tree_sitter=importlib.util.find_spec("tree_sitter") is not None,
        )

    def lines(self) -> list[str]:
        indexer = "tree-sitter + stdlib" if self.tree_sitter else "stdlib (ast)"
        macro = "available" if self.graphify else "unavailable (Graphify not on PATH)"
        return [
            f"  light index : available, Python via {indexer}",
            f"  macro tier  : {macro}",
        ]


# --- the light per-language index ------------------------------------------


@dataclass
class FileRecord:
    rel: str
    module: str
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)  # every import, as written
    internal: list[str] = field(default_factory=list)  # rel paths this file imports
    indexed: bool = True  # False for a language no indexer covers


def module_of(rel: str) -> str:
    """The dotted module a source path denotes, package __init__ included."""
    parts = list(Path(rel).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def source_paths(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if SKIP_DIRS.isdisjoint(parts) and path.suffix == ".py":
            found.append(path)
    return found


def scan_python(path: Path, rel: str) -> FileRecord:
    """A file's symbols and imports via the standard-library parser.

    This is the reference indexer. tree-sitter would replace it for other
    languages; for Python the `ast` module is exact and takes no dependency.
    """
    record = FileRecord(rel=rel, module=module_of(rel))
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        record.indexed = False
        return record
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            record.symbols.append(node.name)
    record.imports = sorted(_imports_in(tree, record.module))
    return record


def _imports_in(tree: ast.AST, module: str) -> set[str]:
    """Every imported dotted name, relative imports resolved against `module`."""
    names: set[str] = set()
    package = module.rsplit(".", 1)[0] if "." in module else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(_resolve_from(node, package))
    return {name for name in names if name}


def _resolve_from(node: ast.ImportFrom, package: str) -> str:
    if not node.level:
        return node.module or ""
    base = package.split(".") if package else []
    climbed = base[: len(base) - (node.level - 1)] if node.level > 1 else base
    tail = node.module.split(".") if node.module else []
    return ".".join([*climbed, *tail])


def resolve_internal(records: list[FileRecord]) -> None:
    """Fill each record's `internal`: the repo files it imports.

    An import is internal when a file in the repository declares that module or
    a module it is a package of. Precise enough for a reference impl, and it
    never reaches outside the walked tree.
    """
    by_module: dict[str, str] = {r.module: r.rel for r in records if r.module}
    modules = sorted(by_module)
    for record in records:
        hits: set[str] = set()
        for name in record.imports:
            hits.update(_match_module(name, by_module, modules))
        hits.discard(record.rel)
        record.internal = sorted(hits)


def _match_module(name: str, by_module: dict[str, str], modules: list[str]) -> set[str]:
    if name in by_module:
        return {by_module[name]}
    prefix = name + "."
    return {by_module[m] for m in modules if m.startswith(prefix)}


# --- building and loading the cache ----------------------------------------


def build_index(root: Path, key: str) -> dict:
    records = [scan_python(path, path.relative_to(root).as_posix()) for path in source_paths(root)]
    resolve_internal(records)
    return {
        "key": key,
        "files": {r.rel: _record_json(r) for r in records},
        "modules": {r.module: r.rel for r in records if r.module},
    }


def _record_json(r: FileRecord) -> dict:
    return {
        "module": r.module,
        "symbols": r.symbols,
        "imports": r.imports,
        "internal": r.internal,
        "indexed": r.indexed,
    }


def is_fresh(cache: Path, key: str) -> bool:
    marker = cache / "key"
    return marker.is_file() and marker.read_text(encoding="utf-8").strip() == key and (cache / "index.json").is_file()


def ensure_fresh(root: Path) -> tuple[Path, str, bool]:
    """The cache directory, its key, and whether this call had to rebuild it."""
    sha = head_sha(root)
    key = freshness_key(root, sha)
    cache = cache_dir(root, sha)
    if is_fresh(cache, key):
        return cache, key, False
    cache.mkdir(parents=True, exist_ok=True)
    index = build_index(root, key)
    (cache / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    (cache / "key").write_text(key, encoding="utf-8")
    return cache, key, True


def load_index(cache: Path) -> dict:
    return json.loads((cache / "index.json").read_text(encoding="utf-8"))


# --- the component map, best-effort ----------------------------------------


def owning_component(root: Path, rel: str) -> str | None:
    """The component whose declared paths contain `rel`, if a map is readable.

    A deliberately small reader: it tracks each `name:` and the path tokens that
    follow a `paths:` under it, and returns the longest-prefix match. When no map
    is present, or it cannot be read this simply, it returns None and `locate`
    says the component is unknown rather than guessing.
    """
    text = _map_text(root)
    if text is None:
        return None
    best: tuple[int, str] | None = None
    name = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("- name:") or line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
        elif "paths:" in line and name:
            for token in _path_tokens(line.split("paths:", 1)[1]):
                if rel == token or rel.startswith(token.rstrip("/") + "/"):
                    if best is None or len(token) > best[0]:
                        best = (len(token), name)
    return best[1] if best else None


def _map_text(root: Path) -> str | None:
    for candidate in MAP_NAMES:
        path = root / candidate
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return None
    return None


def _path_tokens(fragment: str) -> list[str]:
    cleaned = fragment.strip().strip("[]")
    return [token.strip().strip("'\"") for token in cleaned.split(",") if token.strip()]


# --- queries ---------------------------------------------------------------


def _file_for(index: dict, target: str) -> str | None:
    """The rel path a target names, whether a path, a module or None."""
    if target in index["files"]:
        return target
    posix = Path(target).as_posix()
    if posix in index["files"]:
        return posix
    return index["modules"].get(target)


def cmd_locate(root: Path, index: dict, target: str) -> int:
    rel = _file_for(index, target)
    if rel is None:
        return _locate_symbol(root, index, target)
    record = index["files"][rel]
    print(f"{rel}")
    print(f"  module    : {record['module'] or '(top level)'}")
    print(f"  symbols   : {', '.join(record['symbols']) or '(none)'}")
    component = owning_component(root, rel)
    print(f"  component : {component or '(no component map, or path not owned)'}")
    if not record["indexed"]:
        print("  note      : present but unindexed; no indexer covers this language")
    return 0


def _locate_symbol(root: Path, index: dict, symbol: str) -> int:
    holders = [rel for rel, rec in index["files"].items() if symbol in rec["symbols"]]
    if not holders:
        print(f"'{symbol}' is not a known file, module or top-level symbol", file=sys.stderr)
        return 1
    print(f"symbol '{symbol}' is declared in:")
    for rel in holders:
        print(f"  {rel}  (component: {owning_component(root, rel) or 'unknown'})")
    return 0


def cmd_deps(index: dict, target: str) -> int:
    rel = _file_for(index, target)
    if rel is None:
        print(f"'{target}' is not a known file or module", file=sys.stderr)
        return 1
    depends_on = index["files"][rel]["internal"]
    dependents = sorted(r for r, rec in index["files"].items() if rel in rec["internal"])
    print(f"{rel}")
    print(f"  depends on   : {', '.join(depends_on) or '(nothing internal)'}")
    print(f"  depended on  : {', '.join(dependents) or '(nothing internal)'}")
    return 0


def cmd_path(index: dict, src: str, dst: str) -> int:
    start, goal = _file_for(index, src), _file_for(index, dst)
    if start is None or goal is None:
        missing = src if start is None else dst
        print(f"'{missing}' is not a known file or module", file=sys.stderr)
        return 1
    chain = _shortest_path(index, start, goal)
    if chain is None:
        print(f"no dependency path from {start} to {goal}; they are decoupled")
        return 0
    print(" -> ".join(chain))
    return 0


def _shortest_path(index: dict, start: str, goal: str) -> list[str] | None:
    queue = [[start]]
    seen = {start}
    while queue:
        trail = queue.pop(0)
        node = trail[-1]
        if node == goal:
            return trail
        for nxt in index["files"].get(node, {}).get("internal", []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append([*trail, nxt])
    return None


def cmd_explain(root: Path, tiers: Tiers, node: str) -> int:
    if not tiers.graphify or macro_build(root) is None:
        why = "Graphify is not on PATH" if not tiers.graphify else "no macro graph is built yet"
        print(f"the macro tier is unavailable ({why}), so '{node}' cannot be explained from the")
        print("overview. Run the doctor to provision it or read exactly what it needs:")
        print("  python3 scripts/graph.py doctor        (report what the macro tier needs)")
        print("  python3 scripts/graph.py doctor --build (build it, when Graphify is present)")
        print("Meanwhile the light floor still answers: query locate/deps/path, or read the")
        print("component map for the declared structure.")
        return 0
    done = subprocess.run(["graphify", "explain", node])
    return done.returncode


# --- the doctor: provisioning the macro tier, ensure-or-report -------------


def macro_build(root: Path) -> Path | None:
    """Where the macro tier's build is, or None when none exists yet.

    Graphify writes under the commit's cache directory, and its personal-skill
    form writes `graphify-out/` at the repository root. Either counts as a build.
    """
    for graph_json in (
        cache_dir(root, head_sha(root)) / "graphify" / "graph.json",
        root / "graphify-out" / "graph.json",
    ):
        if graph_json.is_file():
            return graph_json.parent
    return None


def languages_present(root: Path) -> dict[str, str]:
    """The languages the tree holds, mapped to their tree-sitter grammar module."""
    found: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or not SKIP_DIRS.isdisjoint(path.relative_to(root).parts):
            continue
        entry = LANGUAGE_GRAMMARS.get(path.suffix)
        if entry:
            found[entry[0]] = entry[1]
    return dict(sorted(found.items()))


def grammar_lines(languages: dict[str, str]) -> list[str]:
    """One report line per language found: how its grammar stands."""
    if not languages:
        return ["  languages   : none detected in the tree"]
    lines = []
    for language, module in languages.items():
        if language == "python":
            note = "covered by stdlib ast (no grammar needed)"
        elif importlib.util.find_spec(module) is not None:
            note = f"grammar present ({module})"
        else:
            note = f"grammar absent ({module.replace('_', '-')})"
        lines.append(f"  - {language:<12}: {note}")
    return lines


def missing_grammar_dists(languages: dict[str, str], have_tree_sitter: bool) -> list[str]:
    """The pip distributions `--install-grammars` would install, in order.

    Python is excluded: the stdlib `ast` scan covers it. The tree-sitter runtime
    leads the list only when a grammar actually needs it — on a Python-only tree
    there is nothing to install and the runtime alone would buy nothing.
    """
    grammars = [
        module.replace("_", "-")
        for language, module in languages.items()
        if language != "python" and importlib.util.find_spec(module) is None
    ]
    if grammars and not have_tree_sitter:
        return ["tree-sitter", *grammars]
    return grammars


def provision_grammars(dists: list[str]) -> int:
    """Install the grammar distributions when pip is here; otherwise report how.

    Opt-in and safe: tree-sitter grammars are published pip packages. This never
    touches Graphify, which is a personal skill and never a thing to install.
    """
    print()
    if not dists:
        print("  install-grammars: nothing to install; every detected language is covered")
        return 0
    if importlib.util.find_spec("pip") is None:
        print("  install-grammars: pip is not available here, so this can only report.")
        print(f"  run this where pip is present: python3 -m pip install {' '.join(dists)}")
        return 0
    print(f"  install-grammars: python3 -m pip install {' '.join(dists)}")
    done = subprocess.run([sys.executable, "-m", "pip", "install", *dists])
    print(f"  install-grammars: {'done' if done.returncode == 0 else 'pip exited ' + str(done.returncode)}")
    return 0


def provision_macro(root: Path, tiers: Tiers) -> int:
    """(Re)build the macro graph when Graphify is present; otherwise report how."""
    print()
    if not tiers.graphify:
        print("  build: Graphify is not on PATH, so the macro tier cannot be built here.")
        print("  Graphify is a personal skill, never an installed package. Enable it by")
        print("  installing the skill at ~/.claude/skills/graphify/ and putting `graphify`")
        print("  on PATH; this doctor detects it and never installs it for you.")
        return 0
    print(f"  build: graphify update {root}")
    done = subprocess.run(["graphify", "update", str(root)], cwd=str(root))
    print(f"  build: {'done' if done.returncode == 0 else 'graphify exited ' + str(done.returncode)}")
    return 0


def cmd_doctor(root: Path, tiers: Tiers, build: bool, install_grammars: bool) -> int:
    sha = head_sha(root)
    cache = cache_dir(root, sha)
    state = "fresh" if is_fresh(cache, freshness_key(root, sha)) else "stale"
    languages = languages_present(root)
    build_dir = macro_build(root)

    print("code-graph doctor")
    print(f"  repo  : {root}")
    print(f"  cache : {cache} ({state})")
    print()
    print("light tier (the guaranteed floor, zero install)")
    print("  index       : ready, Python via stdlib ast; locate/deps/path always answer")
    print(f"  tree-sitter : {'present' if tiers.tree_sitter else 'absent (stdlib ast still answers for Python)'}")
    for line in grammar_lines(languages):
        print(line)
    print()
    print("macro tier (optional Graphify enrichment, provisioned here)")
    where = shutil.which("graphify")
    print(f"  graphify    : {'on PATH at ' + where if where else 'not on PATH'}")
    print(f"  build       : {'present at ' + str(build_dir) if build_dir else 'absent'}")
    ready = tiers.graphify and build_dir is not None
    print(f"  status      : {'ready' if ready else 'unavailable'}")
    if not ready:
        print("  to enable   : Graphify is the owner's personal skill, not a package. This")
        print("                doctor never installs it. Put `graphify` on PATH (install the")
        print("                skill at ~/.claude/skills/graphify/), then run `doctor --build`.")

    if build:
        provision_macro(root, tiers)
    if install_grammars:
        provision_grammars(missing_grammar_dists(languages, tiers.tree_sitter))
    return 0


# --- entry point -----------------------------------------------------------


def cmd_check(root: Path, tiers: Tiers) -> int:
    sha = head_sha(root)
    key = freshness_key(root, sha)
    cache = cache_dir(root, sha)
    state = "fresh" if is_fresh(cache, key) else "stale"
    print(f"cache : {cache}")
    print(f"key   : {key}")
    print(f"state : {state}")
    for line in tiers.lines():
        print(line)
    return 0


def cmd_refresh(root: Path, tiers: Tiers) -> int:
    cache, key, rebuilt = ensure_fresh(root)
    print(f"cache : {cache}")
    print(f"key   : {key}")
    print(f"state : {'rebuilt' if rebuilt else 'already fresh'}")
    for line in tiers.lines():
        print(line)
    return 0


def _needs(args: list[str], count: int, usage: str) -> bool:
    if len(args) < count:
        print(f"usage: graph.py {usage}", file=sys.stderr)
        return False
    return True


def main(argv: list[str]) -> int:
    args = argv[1:]
    tiers = Tiers.detect()
    root = repo_root()

    if "--check" in args or (args and args[0] == "check"):
        return cmd_check(root, tiers)
    if not args or args[0] == "refresh":
        return cmd_refresh(root, tiers)

    command, rest = args[0], args[1:]
    if command == "doctor":
        flags = set(rest)
        unknown = flags - {"--build", "--install-grammars"}
        if unknown:
            print(f"usage: graph.py doctor [--build] [--install-grammars]", file=sys.stderr)
            return 2
        return cmd_doctor(root, tiers, "--build" in flags, "--install-grammars" in flags)
    if command == "explain":
        return cmd_explain(root, tiers, rest[0]) if _needs(rest, 1, "explain <node>") else 2

    # Every other query is answered against a current cache.
    _, _, _ = ensure_fresh(root)
    index = load_index(cache_dir(root, head_sha(root)))

    if command == "locate":
        return cmd_locate(root, index, rest[0]) if _needs(rest, 1, "locate <path-or-symbol>") else 2
    if command == "deps":
        return cmd_deps(index, rest[0]) if _needs(rest, 1, "deps <path-or-module>") else 2
    if command == "path":
        return cmd_path(index, rest[0], rest[1]) if _needs(rest, 2, "path <from> <to>") else 2

    print(f"unknown command '{command}'; see references/commands.md", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
