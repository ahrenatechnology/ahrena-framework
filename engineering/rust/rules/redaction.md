---
id: redaction
type: rule
clade: engineering
subclade: rust
title: Nothing sensitive leaves the layer that owns it
statement: Rust never derives `Debug` or `Serialize` over a raw secret, logs named fields rather than whole values, and translates an error before it crosses a boundary.
enforcement: judgment
references:
  - docs/error-handling.md
  - docs/toolchain.md
---

# Nothing sensitive leaves the layer that owns it

On 2026-11-12 an endpoint built with the agency returned a cloud SDK's access-denied message verbatim in an HTTP 500, and the client read the account id, the role, the denied action and the resource path out of it. The general rule — what is sensitive, what an exit is, and that an exit emits an allowlist of named fields — is the security plugin's, tracked in #294. This rule is how Rust holds it: the three places Rust code writes a value out are its formatting traits, its logging and tracing calls, and the errors it returns, and each has a form that emits only what was chosen. [`docs/error-handling.md`](../docs/error-handling.md) shows where an error is translated.

**What the specification says.** `#[derive(Debug)]` writes an implementation that prints every field ([Derive](https://doc.rust-lang.org/reference/attributes/derive.html)), and `serde`'s derive does the same for every format; neither knows which field is a secret. The Rust API Guidelines ask that all public types implement `Debug` ([C-DEBUG](https://rust-lang.github.io/api-guidelines/debuggability.html#c-debug)); this rule keeps that guideline, by having a type that holds a secret implement `Debug` by hand or hold the secret in a type whose `Debug` redacts. `tracing` records a field with `?` through `Debug` and with `%` through `Display` ([Recording Fields](https://docs.rs/tracing/latest/tracing/#recording-fields)), so a whole value passed to either is printed whole.

The rule is new to this plugin, from the owner's directive on #285, item 10.

## Conditions

1. **No type derives `Debug` or `Serialize` over a field that holds a secret as raw text or bytes.** Decided by `hooks/check-rust.py`. A field holds a secret when its name is, or ends in an underscore and, one of `password`, `passwd`, `passphrase`, `secret`, `token`, `api_key`, `apikey`, `private_key`, `secret_key`, `access_key`, `credential` or `credentials`; and holds it raw when its type is `String`, `&str`, `Box<str>`, `Cow<str>`, `Vec<u8>` or `&[u8]`, optionally inside `Option`. The fix is a type that redacts — `secrecy::SecretString`, whose `Debug` prints `[REDACTED]` and which implements no `Serialize` unless asked to — or a hand-written `Debug` that prints a placeholder for the field.

2. **A log, trace or metric records named fields chosen for it, never a whole configuration, request, response, error from a dependency, or struct.** Decided by a reviewer. `tracing::info!(user_id = %user.id, "login")` names what it emits; `info!(?config)`, `error!("{:?}", response)` and `#[instrument]` on a function whose arguments include such a value do not, because `#[instrument]` records every argument unless `skip` or `skip_all` says otherwise.

3. **An error from a dependency — a cloud SDK, a database driver, an HTTP client, a third party's API — is translated before it crosses the boundary of the layer that called it.** Decided by a reviewer. The response, the CLI output or the error a library returns carries the layer's own message and, for a service, a correlation id; the dependency's error, which may name accounts, roles, hosts, queries or paths, goes only to an internal log, under condition 2. In `axum` that is an `IntoResponse` for the service's error type that writes a fixed message per variant and never the source's `Display`.

4. **A hand-written `Debug` or `Display` on a type that holds sensitive data prints an allowlist of fields.** Decided by a reviewer. `f.debug_struct("Config").field("region", &self.region).finish_non_exhaustive()` names what is shown and says that something was left out.

## Where this stops

**Condition 1 reads names and types, not meaning.** A field called `pin` or `ssn` holds a secret and is not on the list; a field called `token` holding a pagination cursor as a `String` is on it and is not one. The list is closed so the hook decides it; a reviewer reading condition 4 catches the first, and the second is a one-line `Debug` or a rename. Measured over a local Cargo registry, 328 crate directories and about 415,000 lines, condition 1 reports 3 fields, all in `urlpattern`: the password component of a URL, held in an `Option<String>` on types that derive `Debug`. Each is a real secret by this rule's reading. The first version also read fields of non-text types and reported 31, among them mio's and syn's `token` fields and CORS's `allow_credentials` flag; the condition now reads text and bytes only, and those cases are in the hook's test file.

**What counts as sensitive, and every exit there is, are #294's.** Personal data, payment data, an access policy, a resource identifier and infrastructure layout are in that rule's closed list and are read by a reviewer under conditions 2 to 4 here; a hook cannot tell an account id from any other number.

**The rule does not reach a value the program prints on purpose.** A CLI whose job is to display a configuration the user owns, to that user, is an exit the user asked for; condition 3 still holds for the errors it meets along the way.
