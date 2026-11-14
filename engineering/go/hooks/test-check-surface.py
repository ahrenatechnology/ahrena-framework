#!/usr/bin/env python3
"""Tests for check-surface.py.

A detector that never accepts is as broken as one that never rejects, so the
condition is pinned by failing fixtures and by the carve-outs it must not flag.
Each case builds a throwaway module, runs the hook against it as a subprocess,
and asserts on the exit code and the message.

The carve-outs are where the work is. The condition must read only what an
importer outside the module can reach: an exported function, a method on an
exported type, an exported field, an exported interface's methods. It must let
through a body that merely uses an internal type, a package that is itself
internal, a `main` package, a test file, and the exported alias the remedy
declares.

#288/AC-3: condition 2 of api-surface.md, the one this hook decides, has a
failing case below and the carve-outs beside it.

Usage:
    python3 engineering/go/hooks/test-check-surface.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-surface.py"

GO_MOD = "module example.com/m\n\ngo 1.23\n"

STORE = '''package store

type Record struct{ ID string }
'''

LEAK_RESULT = '''package api

import "example.com/m/internal/store"

func Load(id string) (store.Record, error) {
	return store.Record{ID: id}, nil
}
'''

LEAK_METHOD_PARAMETER = '''package api

import st "example.com/m/internal/store"

type Client struct{}

func (c *Client) Put(r st.Record) error { return nil }
'''

LEAK_FIELDS = '''package api

import "example.com/m/internal/store"

type Order struct {
	Rec store.Record
	rec store.Record
}

type Wrapped struct {
	store.Record
}
'''

LEAK_INTERFACE = '''package api

import "example.com/m/internal/store"

type Repo interface {
	Get(id string) (store.Record, error)
}
'''

NOT_ON_THE_SURFACE = '''package api

import "example.com/m/internal/store"

type Record = store.Record

type client struct{}

func (c *client) Put(r store.Record) error { return nil }

func load() store.Record { return store.Record{} }

func Load() (Record, error) {
	var r store.Record
	return r, nil
}

type hidden struct {
	Rec store.Record
}
'''

MAIN_PACKAGE = '''package main

import "example.com/m/internal/store"

func Run() store.Record { return store.Record{} }

func main() {}
'''

STRING_THAT_LOOKS_LIKE_AN_IMPORT = '''package api

var names = []string{
	"context",
	"example.com/m/internal/store",
}

type Holder struct {
	ctx context.Context
}

func Load() store.Record { return store.Record{} }
'''


def surface(path: str, source: str) -> dict[str, str]:
    return {"go.mod": GO_MOD, "internal/store/store.go": STORE, path: source}


GENERIC_STRUCT = '''package api

import "example.com/m/internal/store"

type Box[T any] struct {
	Rec store.Record
	V   T
}
'''


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case(
        "an exported generic struct is read",
        surface("api/api.go", GENERIC_STRUCT),
        ["[api-surface] condition 2", "Box exposes store.Record in field Rec"],
    ),
    case(
        "an exported function returning an internal type fails",
        surface("api/api.go", LEAK_RESULT),
        ["[api-surface] condition 2", "Load exposes store.Record", "example.com/m/internal/store", "api/api.go:5"],
    ),
    case(
        "a method on an exported type taking an internal type fails, through an alias",
        surface("api/api.go", LEAK_METHOD_PARAMETER),
        ["[api-surface] condition 2", "Put exposes st.Record", "api/api.go:7"],
    ),
    case(
        "an exported field and an embedded internal type fail; an unexported field does not",
        surface("api/api.go", LEAK_FIELDS),
        ["2 failure(s)", "Order exposes store.Record in field Rec", "api/api.go:6", "Wrapped embeds store.Record", "api/api.go:11"],
    ),
    case(
        "an exported interface's method fails",
        surface("api/api.go", LEAK_INTERFACE),
        ["[api-surface] condition 2", "Repo exposes store.Record in method Get"],
    ),
    case(
        "an alias, an unexported receiver, a body and an unexported type are not the surface",
        surface("api/api.go", NOT_ON_THE_SURFACE),
        ["2 file(s), no failures"],
        ok=True,
    ),
    case(
        "an internal package, a main package and a test file are not held",
        {
            **surface("internal/svc/svc.go", LEAK_RESULT.replace("package api", "package svc")),
            "cmd/run/main.go": MAIN_PACKAGE,
            "api/api_test.go": LEAK_RESULT,
        },
        ["4 file(s), no failures"],
        ok=True,
    ),
    case(
        "a string literal at the start of a line is not an import",
        surface("api/api.go", STRING_THAT_LOOKS_LIKE_AN_IMPORT),
        ["2 file(s), no failures"],
        ok=True,
    ),
]


def write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp), files)
        result = subprocess.run([sys.executable, str(HOOK), "."], cwd=tmp, capture_output=True, text=True)
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
