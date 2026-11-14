---
id: exposure
type: rule
clade: engineering
subclade: go
title: Nothing sensitive leaves the layer that owns it, in Go
statement: Go code emits named fields only: no %+v or %#v, no error in a response, a String and LogValue that redact on every type carrying a secret.
enforcement: judgment
references:
  - docs/logging-and-observability.md
  - docs/error-handling.md
  - docs/toolchain.md
---

# Nothing sensitive leaves the layer that owns it, in Go

The rule this one serves is the security plugin's, opened as #294 after a real leak: an application built by the agency answered a client's request with a cloud provider's access-denied error as it came, and the client read the account id, the role, the denied action and the resource path out of one HTTP 500. That rule says, for every language, that a credential, personal data, an access policy, a resource identifier, infrastructure layout, or a whole configuration, error or upstream response never reaches an output, a log, a trace, an error message or a response, and that what a unit emits is an allowlist of named fields. This rule is how Go holds it.

Go makes the whole-object leak a one-character choice. The `fmt` package documentation: "when printing structs, the plus flag (`%+v`) adds field names", and `%#v` is "a Go-syntax representation of the value"; a type that implements `String` is printed through it under `%v` and `%+v`, but `%#v` uses `GoString` instead and, without one, prints every field. `log/slog` resolves a value that implements `LogValuer` through its `LogValue` method, which its documentation offers for exactly this — "you can redact secret information like passwords" — and otherwise prints the struct. An `error` carries whatever its producer put in its message, and a cloud SDK puts the account, the role and the resource there. The conditions below are those three doors and the boundary they open onto.

## Conditions

1. **No format string outside a test uses the `%+v` or `%#v` verb.** Both print every field of a struct; `%#v` also bypasses the type's `String` method. Name the fields to print, or give the type a `String` method and use `%v`. Decided by [`hooks/check-exposure.py`](../hooks/check-exposure.py), over string literals, so the verb is caught whether the call is `fmt`, `log`, `errors` or a logger's own formatting method.

2. **No error is written into an HTTP or gRPC response.** `http.Error` and the gRPC `status.Error` and `status.Errorf` are not given `err`, a variable named for an error, or anything's `.Error()`. The caller receives a generic message and a correlation identifier; the detail goes to an internal log that holds no secret. Decided by [`hooks/check-exposure.py`](../hooks/check-exposure.py), under whatever name the file imports `net/http` or `google.golang.org/grpc/status` as. The hook's first failing fixture is the incident of #294, anonymised.

3. **A struct with a field named for a secret has a `String` and a `LogValue` method in its package that print only what the type allows.** A field is named for a secret when its name ends in one of a closed list — `Password`, `Passwd`, `Passphrase`, `Secret`, `PrivateKey`, `APIKey`, `AccessKey`, `Credential`, `Credentials`, `AccessToken`, `RefreshToken`, `SessionToken`, `BearerToken`, `AuthToken`, `IDToken` — compared without case. Decided by [`hooks/check-exposure.py`](../hooks/check-exposure.py), which reads every non-test file in the package's directory for the methods. Sources: the `fmt` documentation for `String`; the `log/slog` documentation for `LogValuer`.

4. **An error from a dependency is translated before it crosses the layer that received it.** A store, a client or an adapter that receives an error from a database, a cloud SDK or another service returns its own error — a sentinel or a type of its package, wrapped with `%v` or replaced — not the dependency's, so the next layer up cannot pass the provider's message on. Decided by a reviewer, who follows each error a change returns to where it leaves the process. This is condition 3 of [`errors.md`](errors.md) read for exposure rather than for matching.

5. **A log line, a trace attribute and a metric label carry named fields, never a whole request, response, configuration, policy or error value from a dependency.** `slog` is given `"order_id", id`, not `"order", order` for a type that has no `LogValue`, and never `"config", cfg` or `"resp", resp`. Decided by a reviewer, who reads each logging and tracing call the change adds.

6. **A JSON response is encoded from a type built for it, whose fields are the allowlist.** A handler does not encode a domain type, a stored record, a configuration or an upstream response: `encoding/json` writes every exported field, and the next field someone adds to that type is published without a review. Decided by a reviewer.

## Where this stops

**The general rule, its closed list of sensitive classes and its list of exits are #294's.** This rule does not restate them; it names the Go constructs that leak and the Go constructs that hold. Until #294's rule lands in the security plugin, the classes are those its issue lists, and the security plugin's `reviewing-sensitive-data` discipline reads the rest.

**Condition 1 reads the verb, not the operand.** `%#v` applied to a string, to quote it in a panic, is reported too; `%q` does the same without the risk, and that substitution is the fix. A verb assembled at run time, or a format string held in a variable, is not seen.

**Condition 2 recognises two exits by name.** An error written with `w.Write([]byte(err.Error()))`, `fmt.Fprint(w, err)`, `json.NewEncoder(w).Encode(err)` or a framework's own error helper reaches the client the same way and is not seen. A reviewer reads those under condition 4, which is the cause: an error translated at the boundary has nothing left to leak, whatever writes it.

**Condition 3 is decided by a field's name, and the list is closed.** A field named `Token` in a lexer is not a secret, and a field named `SecretName` locates a secret without carrying it, so neither is on the list. A secret held in a field named `Value` or in a `map[string]string` is not seen, and a type whose `String` and `LogValue` exist but print the secret anyway passes. The methods also do not cover `encoding/json`, which ignores both; a type that carries a secret and is ever encoded needs `json:"-"` on the field or its own `MarshalJSON`, which condition 6 asks a reviewer to read.

**What the hook measured.** On the Go 1.27.4 source of `net/http`, `database`, `context` and `cmd/go` — 440 files — it reports 12, 14 and 2 for conditions 1 to 3. Each report read by hand is the state its condition names: `%+v` and `%#v` in `panic` messages and `log.Printf` calls in `cmd/go`; `http.Error(w, err.Error(), …)` in `cmd/go`'s test web server `vcweb` and in `net/http/triv.go`; and two unexported types holding a `password` field with no redacting method, one of them the parsed `.netrc` line. The Go repository is not held to this rule; a report there is a measurement.

**Secrets in code are not here.** A credential written as a literal is the security plugin's `reviewing-secrets` discipline and its detectors.
