#!/usr/bin/env python3
"""Tests for check-packages.py.

A detector that never accepts is as broken as one that never rejects, so each
condition is pinned by failing fixtures and by the carve-outs it must not flag.
Each case builds a throwaway tree, runs the hook against it as a subprocess,
and asserts on the exit code and the message.

The carve-outs are where the work is. Condition 2 must let an import point
down the layers, let a package outside any layer import anything, leave a
third-party path that happens to contain a layer's name alone, and leave a
test file alone. Condition 3 must report a requirement cycle once, through
every module in it, and must not mistake a chain for a cycle.

#288/AC-3: conditions 2 and 3 of package-boundaries.md, the two this hook
decides, have failing cases below and the carve-outs beside them.

Usage:
    python3 engineering/go/hooks/test-check-packages.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-packages.py"

GO_MOD = "module example.com/m\n\ngo 1.23\n\nrequire github.com/acme/infra/client v1.0.0\n"


def importing(package: str, *paths: str) -> str:
    lines = "\n".join(f'\t"{path}"' for path in paths)
    return f"package {package}\n\nimport (\n{lines}\n)\n"


def tree(files: dict[str, str]) -> dict[str, str]:
    return {"go.mod": GO_MOD, **files}


def go_mod(path: str, *requires: str) -> str:
    lines = "\n".join(f"\t{r} v0.0.0 // indirect" for r in requires)
    return f"module {path}\n\ngo 1.23\n\nrequire (\n{lines}\n)\n"


ARGUMENT = "@argument"


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case(
        "a run over a subdirectory still finds the module above it",
        tree(
            {
                "internal/orders/domain/order.go": importing("domain", "example.com/m/internal/orders/infra"),
                ARGUMENT: "internal/orders",
            }
        ),
        ["[package-boundaries] condition 2"],
    ),
    case(
        "domain importing infra fails",
        tree({"internal/orders/domain/order.go": importing("domain", "example.com/m/internal/orders/infra")}),
        [
            "[package-boundaries] condition 2",
            "a package in the domain layer imports example.com/m/internal/orders/infra, in the infra layer",
            "internal/orders/domain/order.go:1",
        ],
    ),
    case(
        "domain importing application fails",
        tree({"internal/orders/domain/order.go": importing("domain", "example.com/m/internal/orders/application")}),
        ["[package-boundaries] condition 2", "in the application layer"],
    ),
    case(
        "an upward import into another context fails too",
        tree({"internal/orders/application/cancel.go": importing("application", "example.com/m/internal/billing/infra/pg")}),
        ["[package-boundaries] condition 2", "a package in the application layer imports example.com/m/internal/billing/infra/pg"],
    ),
    case(
        "imports pointing down, from outside any layer, to a third party, or from a test pass",
        tree(
            {
                "internal/orders/infra/store.go": importing("infra", "example.com/m/internal/orders/domain"),
                "internal/orders/application/cancel.go": importing("application", "example.com/m/internal/orders/domain"),
                "cmd/app/main.go": importing("main", "example.com/m/internal/orders/infra"),
                "internal/orders/domain/order.go": importing("domain", "github.com/acme/infra/client"),
                "internal/orders/domain/order_test.go": importing("domain", "example.com/m/internal/orders/infra"),
            }
        ),
        ["5 file(s), no failures"],
        ok=True,
    ),
    case(
        "an upward import into another module of the same tree fails",
        {
            "orders/go.mod": go_mod("example.com/orders", "example.com/shared"),
            "orders/domain/order.go": importing("domain", "example.com/shared/infra/log"),
            "shared/go.mod": go_mod("example.com/shared"),
            "shared/infra/log/log.go": "package log\n",
        },
        ["[package-boundaries] condition 2", "imports example.com/shared/infra/log"],
    ),
    case(
        "two modules requiring each other fail once, naming the cycle",
        {
            "a/go.mod": go_mod("example.com/a", "example.com/b"),
            "b/go.mod": go_mod("example.com/b", "example.com/a"),
        },
        ["1 failure(s)", "[package-boundaries] condition 3", "example.com/a -> example.com/b -> example.com/a"],
    ),
    case(
        "a chain of requirements is not a cycle",
        {
            "a/go.mod": go_mod("example.com/a", "example.com/b"),
            "b/go.mod": go_mod("example.com/b", "example.com/c"),
            "c/go.mod": go_mod("example.com/c"),
        },
        ["no failures"],
        ok=True,
    ),
]


def write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def run(files: dict[str, str]) -> tuple[int, str]:
    """Run the hook over the tree, or over the path a case names under ARGUMENT."""
    files = dict(files)
    argument = files.pop(ARGUMENT, ".")
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp), files)
        result = subprocess.run([sys.executable, str(HOOK), argument], cwd=tmp, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    """What went wrong with this case, or nothing."""
    wanted = "pass" if ok else "fail"
    found = [] if ok == (code == 0) else [f"expected the hook to {wanted}, it did the other"]
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def report_failure(name: str, problems: list[str], output: str) -> None:
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")


def summarise(failed: int, total: int) -> int:
    print()
    if failed:
        print(f"{failed} of {total} cases failed.")
        return 1
    print(f"{total} cases passed.")
    return 0


def main() -> int:
    failed = 0
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            report_failure(name, problems, output)
        else:
            print(f"ok    {name}")
    return summarise(failed, len(CASES))


if __name__ == "__main__":
    sys.exit(main())
