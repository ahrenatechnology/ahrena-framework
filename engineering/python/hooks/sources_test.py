"""Tests for sources.py, beside it as rules/test-placement.md asks.

Each test is a plain function, so pytest collects the file as it stands, and
the script runs them itself under `python3`, so it needs nothing installed.

Usage:
    python3 engineering/python/hooks/sources_test.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from sources import display, sources  # noqa: E402


def _tree(root: Path, names: list[str]) -> None:
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")


def test_display_is_relative_inside_the_base() -> None:
    assert display(Path("/repo/pkg/a.py"), Path("/repo")) == "pkg/a.py"


def test_display_keeps_a_path_outside_the_base() -> None:
    assert display(Path("/elsewhere/a.py"), Path("/repo")) == "/elsewhere/a.py"


def test_a_python_file_given_as_a_root_is_read() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _tree(root, ["a.py"])
        assert sources([root / "a.py"]) == [root / "a.py"]


def test_a_file_that_is_not_python_is_not_read() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _tree(root, ["notes.md"])
        assert sources([root / "notes.md"]) == []


def test_dot_prefixed_and_vendored_trees_are_left_out() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _tree(root, ["pkg/a.py", ".venv/b.py", "node_modules/c.py", "build/d.py", "pkg/__pycache__/e.py"])
        assert sources([root]) == [root / "pkg" / "a.py"]


def test_overlapping_roots_report_a_file_once() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _tree(root, ["pkg/a.py"])
        assert sources([root, root / "pkg"]) == [root / "pkg" / "a.py"]


TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]


def main() -> int:
    for test in TESTS:
        test()
        print(f"ok    {test.__name__}")
    print(f"\n{len(TESTS)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
