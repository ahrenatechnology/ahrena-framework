#!/usr/bin/env python3
"""Tests for check-context.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing fixture and by the carve-out it must not
flag. Each case builds a throwaway module, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

The carve-outs are where the work is. Condition 1 must not read a field whose
type merely mentions a context (a func type taking one, a map of them) and must
not read an interface. Condition 2 must accept a grouped first parameter, an
unnamed list, and the testing handle that conventionally goes first in a test
helper. Condition 3 must stay quiet on a function with no context in scope, on
the detached task written with `context.WithoutCancel`, and on a module whose
`go` directive predates `WithoutCancel`.

#288/AC-3: every condition the hook decides, context.md 1 to 3, has a
failing case below and the carve-outs beside it.
#288/AC-6: the last check runs the foundation's artifact gate over the
corpus this plugin ships in, when the suite runs inside that checkout.

Usage:
    python3 engineering/go/hooks/test-check-context.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-context.py"

GO_MOD = "module example.com/m\n\ngo 1.23\n"

CLEAN = '''package store

import "context"

type Store struct {
	name string
}

func (s *Store) Get(ctx context.Context, key string) (string, error) {
	return lookup(ctx, key)
}

func lookup(ctx context.Context, key string) (string, error) {
	return key, ctx.Err()
}
'''

NO_CONTEXT_IMPORT = '''package clock

type Context struct{}

type Holder struct {
	ctx Context
}

func use(n int, ctx Context) {}
'''

# --- condition 1: no struct field holds a context.Context -------------------

FIELD = '''package worker

import "context"

type Worker struct {
	id  int
	ctx context.Context
}
'''

EMBEDDED = '''package worker

import "context"

type Request struct {
	context.Context
	Path string
}
'''

GROUPED_FIELD = '''package worker

import "context"

type Pair struct {
	parent, child context.Context
}
'''

ALIASED_IMPORT = '''package worker

import (
	"fmt"
	stdctx "context"
)

type Worker struct {
	ctx stdctx.Context `json:"-"`
}

var _ = fmt.Sprint
'''

NESTED_STRUCT = '''package worker

import "context"

type Outer struct {
	inner struct {
		ctx context.Context
	}
}
'''

FIELDS_THAT_ONLY_MENTION_A_CONTEXT = '''package worker

import "context"

type Hooks struct {
	before func(ctx context.Context) error
	make   func() context.Context
	byKey  map[string]context.Context
}

type Runner interface {
	Run(ctx context.Context) error
}
'''

# --- condition 2: a context.Context is the first parameter ------------------

CONTEXT_SECOND = '''package api

import "context"

func Fetch(id string, ctx context.Context) error {
	return ctx.Err()
}
'''

METHOD_CONTEXT_THIRD = '''package api

import "context"

type Client struct{}

func (c *Client) Send(to string, body []byte, ctx context.Context) error {
	return nil
}
'''

LITERAL_CONTEXT_SECOND = '''package api

import "context"

var handler = func(n int, ctx context.Context) error {
	return nil
}
'''

GROUPED_FIRST = '''package api

import "context"

func Merge(parent, child context.Context, limit int) error {
	return nil
}
'''

UNNAMED_FIRST = '''package api

import "context"

type Op func(context.Context, string) error
'''

TESTING_HANDLE_FIRST = '''package api

import (
	"context"
	"testing"
)

func mustFetch(t *testing.T, ctx context.Context, id string) {
	t.Helper()
}

func benchFetch(tb testing.TB, ctx context.Context) {}
'''

GENERIC_CONTEXT_SECOND = '''package api

import "context"

func Map[T any](items []T, ctx context.Context) []T {
	return items
}
'''

# --- condition 3: a function with a context in scope does not start a fresh one


BACKGROUND_INSIDE = '''package svc

import "context"

func Handle(ctx context.Context, id string) error {
	return save(context.Background(), id)
}

func save(ctx context.Context, id string) error { return nil }
'''

TODO_IN_GOROUTINE = '''package svc

import "context"

func Handle(ctx context.Context) {
	go func() {
		audit(context.TODO())
	}()
}

func audit(ctx context.Context) {}
'''

RESULTS_WITH_BRACES = '''package svc

import "context"

func Index(ctx context.Context) (map[string]struct{}, error) {
	return build(context.Background())
}

func build(ctx context.Context) (map[string]struct{}, error) { return nil, nil }
'''

DETACHED_WITH_WITHOUT_CANCEL = '''package svc

import "context"

func Handle(ctx context.Context) {
	go audit(context.WithoutCancel(ctx))
}

func audit(ctx context.Context) {}
'''

BACKGROUND_WITHOUT_CONTEXT_IN_SCOPE = '''package main

import "context"

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	run(ctx)
}

func run(ctx context.Context) {}
'''

BACKGROUND_IN_A_FUNC_TYPE_ONLY = '''package svc

import "context"

var steps = []func(ctx context.Context) error{
	func(ctx context.Context) error { return nil },
}

var fallback = context.Background()
'''

OLD_MODULE = "module example.com/m\n\ngo 1.20\n"

# --- the walk ------------------------------------------------------------------

GENERATED = '''// Code generated by mockgen. DO NOT EDIT.

package mocks

import "context"

type Fake struct {
	ctx context.Context
}
'''

STRINGS_AND_COMMENTS = '''package doc

import "context"

// type Bad struct { ctx context.Context }
var example = "func f(id string, ctx context.Context) {}"

var raw = `
type Bad struct {
	ctx context.Context
}
`

/* func g(ctx context.Context) { context.Background() } */
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


def module(source: str, path: str = "a.go", go_mod: str = GO_MOD) -> dict[str, str]:
    return {"go.mod": go_mod, path: source}



GENERATOR_WITH_MARKER_IN_A_TEMPLATE = '''package gen

import "context"

const header = `
// Code generated by gen. DO NOT EDIT.
`

type Runner struct {
	ctx context.Context
}
'''

LITERALS_WITH_FUNC_AND_GENERIC_RESULTS = '''package api

import "context"

type Result[T any] struct{ V T }

var f = func(a int, ctx context.Context) func() {
	return nil
}

var g = func(n int, ctx context.Context) Result[int] {
	return Result[int]{}
}
'''



LITERAL_AS_A_WRAPPED_ARGUMENT = '''package api

import "context"

func wrap(f func(int, context.Context) func()) int { return 0 }

var wrapped = wrap(
	func(a int, ctx context.Context) func() { return nil },
)
'''


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case(
        "a literal starting a line inside a call's parentheses is not a declaration",
        module(LITERAL_AS_A_WRAPPED_ARGUMENT),
        ["[context] condition 2", "func literal takes its context.Context as parameter 2", "a.go:8"],
    ),
    case(
        "a generation marker inside a string is not a generated file",
        module(GENERATOR_WITH_MARKER_IN_A_TEMPLATE),
        ["[context] condition 1", "Runner stores a context.Context in field ctx"],
    ),
    case(
        "a literal whose result is a func or a generic type keeps its parameters",
        module(LITERALS_WITH_FUNC_AND_GENERIC_RESULTS),
        ["2 failure(s)", "func literal takes its context.Context as parameter 2", "a.go:7", "a.go:11"],
    ),
    case("a module that threads its context passes", module(CLEAN), ["1 file(s), no failures"], ok=True),
    case(
        "a type named Context in a file that does not import context is not read",
        module(NO_CONTEXT_IMPORT),
        ["no failures"],
        ok=True,
    ),
    case(
        "a struct field holding a context fails",
        module(FIELD),
        ["[context] condition 1", "Worker stores a context.Context in field ctx", "a.go:7"],
    ),
    case(
        "an embedded context makes the struct a Context, and passes",
        module(EMBEDDED),
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "a grouped field declaration fails once per line",
        module(GROUPED_FIELD),
        ["[context] condition 1", "field parent, child"],
    ),
    case(
        "an aliased import is followed and a tag is ignored",
        module(ALIASED_IMPORT),
        ["[context] condition 1", "field ctx", "a.go:9"],
    ),
    case(
        "an anonymous nested struct is read",
        module(NESTED_STRUCT),
        ["[context] condition 1", "a.go:7"],
    ),
    case(
        "a field that only mentions a context, and an interface, are not read",
        module(FIELDS_THAT_ONLY_MENTION_A_CONTEXT),
        ["no failures"],
        ok=True,
    ),
    case(
        "a context as the second parameter fails",
        module(CONTEXT_SECOND),
        ["[context] condition 2", "Fetch takes its context.Context as parameter 2", "a.go:5"],
    ),
    case(
        "a method's receiver is not a parameter",
        module(METHOD_CONTEXT_THIRD),
        ["[context] condition 2", "Send takes its context.Context as parameter 3"],
    ),
    case(
        "a function literal is held too",
        module(LITERAL_CONTEXT_SECOND),
        ["[context] condition 2", "func literal takes its context.Context as parameter 2"],
    ),
    case(
        "type parameters are not parameters",
        module(GENERIC_CONTEXT_SECOND),
        ["[context] condition 2", "Map takes its context.Context as parameter 2"],
    ),
    case(
        "a grouped first parameter, an unnamed list and a testing handle pass",
        {**module(GROUPED_FIRST), "b.go": UNNAMED_FIRST, "c_test.go": TESTING_HANDLE_FIRST},
        ["3 file(s), no failures"],
        ok=True,
    ),
    case(
        "context.Background inside a function holding a context fails",
        module(BACKGROUND_INSIDE),
        ["[context] condition 3", "Handle has a context.Context in scope and calls context.Background", "a.go:6"],
    ),
    case(
        "context.TODO inside a goroutine started by such a function fails",
        module(TODO_IN_GOROUTINE),
        ["[context] condition 3", "calls context.TODO", "a.go:7"],
    ),
    case(
        "braces in the result types do not end the signature early",
        module(RESULTS_WITH_BRACES),
        ["[context] condition 3", "Index has a context.Context in scope", "a.go:6"],
    ),
    case(
        "a detached task written with WithoutCancel passes",
        module(DETACHED_WITH_WITHOUT_CANCEL),
        ["no failures"],
        ok=True,
    ),
    case(
        "context.Background where no context is in scope passes",
        module(BACKGROUND_WITHOUT_CONTEXT_IN_SCOPE),
        ["no failures"],
        ok=True,
    ),
    case(
        "a func type in a composite literal is not a body",
        module(BACKGROUND_IN_A_FUNC_TYPE_ONLY),
        ["no failures"],
        ok=True,
    ),
    case(
        "a module older than go 1.21 is not held to condition 3",
        module(BACKGROUND_INSIDE, go_mod=OLD_MODULE),
        ["no failures"],
        ok=True,
    ),
    case(
        "an old module is still held to conditions 1 and 2",
        module(FIELD, go_mod=OLD_MODULE),
        ["[context] condition 1"],
    ),
    case(
        "a string literal at the start of a line is not an import",
        module(STRING_THAT_LOOKS_LIKE_AN_IMPORT),
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "a generated file is skipped",
        module(GENERATED),
        ["0 file(s), no failures"],
        ok=True,
    ),
    case(
        "vendor and testdata are skipped",
        {"go.mod": GO_MOD, "vendor/x/a.go": FIELD, "testdata/a.go": FIELD},
        ["0 file(s), no failures"],
        ok=True,
    ),
    case(
        "comments, strings and raw strings are not code",
        module(STRINGS_AND_COMMENTS),
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


GATE = Path(__file__).resolve().parents[3] / "foundation" / "hooks" / "validate-artifacts.py"


def corpus_gate() -> int:
    """#288/AC-6: the artifact gate passes with this plugin's rules, docs, skills and agent in it."""
    if not GATE.is_file():
        print("skip  the artifact gate, outside the framework's checkout")
        return 0
    result = subprocess.run([sys.executable, str(GATE), str(GATE.parents[2])], capture_output=True, text=True)
    if result.returncode == 0:
        print("ok    the artifact gate passes over the corpus")
        return 0
    report_failure("the artifact gate passes over the corpus", ["expected exit 0"], result.stdout + result.stderr)
    return 1


def missing_path() -> int:
    """A path that does not exist is an error, not a clean run over nothing."""
    result = subprocess.run([sys.executable, str(HOOK), "no/such/path.go"], capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode == 2 and "does not exist" in output:
        print("ok    a path that does not exist fails instead of passing over zero files")
        return 0
    report_failure("a path that does not exist fails instead of passing over zero files", ["expected exit 2 naming the path"], output)
    return 1


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
    failed += corpus_gate()
    failed += missing_path()
    return summarise(failed, len(CASES) + 2)


if __name__ == "__main__":
    sys.exit(main())
