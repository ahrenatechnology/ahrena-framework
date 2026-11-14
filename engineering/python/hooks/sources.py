"""The source walk check-python.py and check-test-placement.py share.

Both hooks are scripts run as `python3 <path>`, which puts this directory
first on `sys.path`, so each imports this module by name and needs nothing
installed. Kept to the walk alone: which files a hook reads, and how a path
is shown in a finding.
"""

from __future__ import annotations

from pathlib import Path

SKIP_NAMES = frozenset({"__pycache__", "node_modules", "venv", "build", "dist"})


def display(path: Path, base: Path) -> str:
    """The path relative to the working directory, or as given when outside it."""
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _skipped(relative: Path) -> bool:
    return any(part.startswith(".") or part in SKIP_NAMES for part in relative.parts)


def _walk(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    return [path for path in root.rglob("*.py") if not _skipped(path.relative_to(root))]


def sources(roots: list[Path]) -> list[Path]:
    """Every Python file under the roots, with dot-prefixed and vendored trees left out."""
    found: list[Path] = []
    for root in roots:
        found.extend(_walk(root))
    return sorted(set(found))
