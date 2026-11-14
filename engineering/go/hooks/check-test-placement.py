#!/usr/bin/env python3
"""Detector for the Go test-placement rule.

Decides the condition stated in engineering/go/rules/test-placement.md:

    1. a Go source file that declares a function or a method, other than main
       and init, has a test file named for it in the same directory

The form is the go command's own: a file whose name ends in _test.go is a test
file of the package in its directory, so a reader who opens orders.go finds
orders_test.go beside it. A file whose name carries a build-constraint suffix
(orders_linux.go, orders_linux_amd64.go) is answered by a test file named for
the whole stem or for the stem without that suffix, because the go command
reads the suffix as a constraint, not as part of what the file is about.

It reads Go through golex.py, beside it, and needs nothing but the Python
standard library.

Usage:
    python3 engineering/go/hooks/check-test-placement.py [path ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from golex import Finding, GoFile, brace_depths, run, signatures  # noqa: E402

GOOS = frozenset(
    {
        "aix", "android", "darwin", "dragonfly", "freebsd", "hurd", "illumos", "ios", "js", "linux",
        "nacl", "netbsd", "openbsd", "plan9", "solaris", "wasip1", "windows", "zos",
    }
)

GOARCH = frozenset(
    {
        "386", "amd64", "amd64p32", "arm", "armbe", "arm64", "arm64be", "loong64", "mips", "mipsle",
        "mips64", "mips64le", "mips64p32", "mips64p32le", "ppc", "ppc64", "ppc64le", "riscv", "riscv64",
        "s390", "s390x", "sparc", "sparc64", "wasm",
    }
)

ENTRY_POINTS = frozenset({"main", "init"})


def declared(source: GoFile) -> list[str]:
    """The top-level functions and methods a file declares, entry points left out."""
    depths = brace_depths(source.tokens)
    return [
        signature.name
        for signature in signatures(source.tokens)
        if depths[signature.start] == 0 and signature.name != "func literal" and signature.name not in ENTRY_POINTS
    ]


def candidate_stems(stem: str) -> list[str]:
    """The stems whose test file answers this one: itself, and itself less a GOOS or GOARCH suffix."""
    stems = [stem]
    parts = stem.split("_")
    while len(parts) > 1 and (parts[-1] in GOOS or parts[-1] in GOARCH):
        parts = parts[:-1]
        stems.append("_".join(parts))
    return stems


def check(source: GoFile, findings: list[Finding]) -> None:
    if source.path.name.endswith("_test.go"):
        return
    names = declared(source)
    if not names:
        return
    directory, stem = source.path.parent, source.path.name[: -len(".go")]
    if any((directory / f"{candidate}_test.go").is_file() for candidate in candidate_stems(stem)):
        return
    more = f" and {len(names) - 1} more" if len(names) > 1 else ""
    findings.append(
        Finding(
            f"{source.rel}:1",
            "test-placement",
            1,
            f"{source.path.name} declares {names[0]}{more} and has no {stem}_test.go beside it",
        )
    )


if __name__ == "__main__":
    sys.exit(run(sys.argv, check))
