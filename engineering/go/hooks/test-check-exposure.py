#!/usr/bin/env python3
"""Tests for check-exposure.py.

A detector that never accepts is as broken as one that never rejects, so each
condition is pinned by failing fixtures and by the carve-outs it must not flag.
Each case builds a throwaway module, runs the hook against it as a subprocess,
and asserts on the exit code and the message.

The first failing case of condition 2 is the incident that opened #294, with
invented identifiers: a handler that stores a secret, catches the cloud
provider's access-denied error, and writes it to the client as it came.

The carve-outs are where the work is. Condition 1 must not read a verb inside
a comment or a test file. Condition 2 must let a generic message and a
correlation id through. Condition 3 must accept the redacting methods in
another file of the same package, and must leave a field that only names a
secret's location alone when it does not carry the secret.

#288/AC-3: conditions 1 to 3 of exposure.md, the ones this hook decides,
have failing cases below and the carve-outs beside them.

Usage:
    python3 engineering/go/hooks/test-check-exposure.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-exposure.py"

GO_MOD = "module example.com/m\n\ngo 1.23\n"

INCIDENT = '''package api

import (
	"net/http"

	"example.com/m/internal/vault"
)

type Handler struct{ store *vault.Store }

func (h *Handler) PutSecret(w http.ResponseWriter, r *http.Request) {
	if err := h.store.Put(r.Context(), r.PathValue("name"), r.Body); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
'''

WRAPPED_INTO_RESPONSE = '''package api

import (
	"fmt"
	nethttp "net/http"
)

func fail(w nethttp.ResponseWriter, err error) {
	nethttp.Error(w, fmt.Sprintf("store failed: %v", err), 500)
}
'''

GRPC_STATUS = '''package rpc

import (
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func translate(err error) error {
	return status.Errorf(codes.Internal, "put failed: %v", err)
}
'''

GENERIC_RESPONSE = '''package api

import (
	"log/slog"
	"net/http"
)

func fail(w http.ResponseWriter, r *http.Request, err error, id string) {
	slog.ErrorContext(r.Context(), "put secret", "request_id", id, "error", err)
	http.Error(w, "internal error, reference "+id, http.StatusInternalServerError)
}
'''

WHOLE_STRUCT_VERBS = '''package config

import (
	"fmt"
	"log"
)

type Config struct{ Region, RoleARN string }

func Dump(c Config) string {
	log.Printf("loaded %+v", c)
	return fmt.Sprintf("%#v", c)
}
'''

VERBS_IN_COMMENTS_AND_TESTS = '''package config

import "fmt"

// Dump used to print %+v, which leaked every field.
func Dump(name string) string { return fmt.Sprintf("%q", name) }
'''

VERB_IN_TEST = '''package config

import "testing"

func TestDump(t *testing.T) { t.Logf("%+v", struct{ A int }{1}) }
'''

CREDENTIALS = '''package vault

type Credentials struct {
	User     string
	Password string
}

type Client struct {
	Endpoint     string
	ClientSecret string
}
'''

CREDENTIALS_REDACTED = '''package vault

import "log/slog"

type Credentials struct {
	User     string
	Password string
}

func (c Credentials) String() string { return c.User + ":REDACTED" }

func (c Credentials) LogValue() slog.Value { return slog.StringValue(c.String()) }
'''

ONLY_STRING = '''package vault

type Key struct {
	ID         string
	PrivateKey []byte
}

func (k Key) String() string { return k.ID }
'''

REDACTED_ELSEWHERE_TYPE = '''package vault

type Token struct {
	AccessToken string
}
'''

REDACTED_ELSEWHERE_METHODS = '''package vault

import "log/slog"

func (t *Token) String() string { return "REDACTED" }

func (t *Token) LogValue() slog.Value { return slog.StringValue("REDACTED") }
'''

NOT_A_SECRET = '''package lexer

type Token struct {
	Kind, Text string
}

type Ref struct {
	SecretName string
}
'''


def module(files: dict[str, str]) -> dict[str, str]:
    return {"go.mod": GO_MOD, **files}



GENERIC_SECRET = '''package vault

type Vault[T any] struct {
	Password string
	Item     T
}
'''

VERB_FORMS = '''package config

import "fmt"

func Dump(c any) string { return fmt.Sprintf("%+[1]v", c) }

func Rate(p int) string { return fmt.Sprintf("%d%%+v", p) }
'''

SECRET_ONLY_IN_THE_TYPE = '''package admin

import "example.com/m/internal/auth"

type Manager struct {
	Owner *auth.Credentials
}
'''



ANONYMOUS_SECRET_TYPES = '''package vault

var accounts []struct{ Password string }

var keys = map[string]struct{ APIKey string }{}

type Pair [2]struct{ Secret string }
'''


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case(
        "a slice, map or array of anonymous structs has no name to carry methods, and is not read",
        module({"vault/anon.go": ANONYMOUS_SECRET_TYPES}),
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "an exported generic struct carrying a secret is read",
        module({"vault/vault.go": GENERIC_SECRET}),
        ["[exposure] condition 3", "Vault carries Password"],
    ),
    case(
        "an argument index is caught and an escaped percent is not",
        module({"config/dump.go": VERB_FORMS}),
        ["1 failure(s)", "[exposure] condition 1", "config/dump.go:5"],
    ),
    case(
        "a field whose type, not name, mentions a secret is not read",
        module({"admin/manager.go": SECRET_ONLY_IN_THE_TYPE}),
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "the incident: a provider error written to the client as it came fails",
        module({"api/secret.go": INCIDENT}),
        ["[exposure] condition 2", "http.Error writes err to the response", "api/secret.go:13"],
    ),
    case(
        "an error formatted into the response through an alias fails",
        module({"api/fail.go": WRAPPED_INTO_RESPONSE}),
        ["[exposure] condition 2", "nethttp.Error writes err to the response"],
    ),
    case(
        "an error formatted into a gRPC status fails",
        module({"rpc/translate.go": GRPC_STATUS}),
        ["[exposure] condition 2", "status.Errorf writes err to the response"],
    ),
    case(
        "a generic message with a reference id, the detail logged inside, passes",
        module({"api/fail.go": GENERIC_RESPONSE}),
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "%+v and %#v fail, once each",
        module({"config/dump.go": WHOLE_STRUCT_VERBS}),
        ["2 failure(s)", "[exposure] condition 1", "%+v prints every field", "config/dump.go:11", "%#v prints every field", "config/dump.go:12"],
    ),
    case(
        "a verb in a comment or a test file is not read",
        module({"config/dump.go": VERBS_IN_COMMENTS_AND_TESTS, "config/dump_test.go": VERB_IN_TEST}),
        ["2 file(s), no failures"],
        ok=True,
    ),
    case(
        "a type carrying a secret with no redacting String and LogValue fails",
        module({"vault/creds.go": CREDENTIALS}),
        [
            "2 failure(s)",
            "[exposure] condition 3",
            "Credentials carries Password and declares no String, LogValue",
            "Client carries ClientSecret",
            "vault/creds.go:3",
        ],
    ),
    case(
        "String alone is not enough",
        module({"vault/key.go": ONLY_STRING}),
        ["[exposure] condition 3", "Key carries PrivateKey and declares no LogValue"],
    ),
    case(
        "redacting methods in the same file, or another file of the package, pass",
        module(
            {
                "vault/creds.go": CREDENTIALS_REDACTED,
                "vault/token.go": REDACTED_ELSEWHERE_TYPE,
                "vault/token_log.go": REDACTED_ELSEWHERE_METHODS,
            }
        ),
        ["3 file(s), no failures"],
        ok=True,
    ),
    case(
        "a lexer Token and a field that names a secret's location are not secrets",
        module({"lexer/token.go": NOT_A_SECRET}),
        ["1 file(s), no failures"],
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
