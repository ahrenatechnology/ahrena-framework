---
id: error-handling
type: doc
clade: engineering
subclade: rust
title: Errors in Rust, from the failure to the caller
summary: Where the line between a panic and a returned error falls and why, how a library's error type is shaped and why its callers need one, what an application does differently, how `?` and `From` carry a failure up, and how a panic reaches the logs of a server.
references:
  - rules/panics.md
  - rules/error-types.md
  - rules/redaction.md
  - docs/libraries.md
---

# Errors in Rust, from the failure to the caller

This is the companion to [`rules/panics.md`](../rules/panics.md) and [`rules/error-types.md`](../rules/error-types.md). The rules state what is not allowed; this explains the model they come from. It ports the predecessor's `codex-rust-error-handling`, which was built on Andrew Gallant's [Error Handling in Rust](https://burntsushi.net/rust-error-handling/) and [Using unwrap() in Rust is Okay](https://burntsushi.net/unwrap/), and keeps their argument while dropping the source's restatements of the rules.

**What the specification says.** RFC 236, [Error conventions](https://rust-lang.github.io/rfcs/0236-error-conventions.html), is the source of the split this page argues: contract violations fail the thread, obstructions are `Result`s. The Reference's [Panic](https://doc.rust-lang.org/reference/panic.html) chapter defines unwinding and abort; the `?` operator is defined in [The try propagation expression](https://doc.rust-lang.org/reference/expressions/operator-expr.html#r-expr.try); the `Error` trait is the standard library's. What an error type should look like is community practice, from the API Guidelines' [C-GOOD-ERR](https://rust-lang.github.io/api-guidelines/interoperability.html#c-good-err).

## A panic is a bug report

Rust has two ways to stop: return an `Err` and let the caller decide, or panic and unwind the thread. They are not two styles of error handling. A panic says the program is wrong — an invariant the code relies on was broken — and the only useful response is to fix the code. An `Err` says the world is not as hoped — the file is missing, the input is malformed, the server refused — and the program has a decision to make about it.

So the question for every `unwrap` is not "can this fail?" but "if this fails, is it a bug?". `Regex::new(r"\d+")` on a literal fails only if the literal is wrong, which a test catches once and for ever: that is a bug, an `expect` with the reason is right, and [`rules/regex-compilation.md`](../rules/regex-compilation.md) condition 4 adds the lint that catches the typo at compile time. `"42".parse::<u32>()` on a value read from a file fails whenever the file says so: that is not a bug, and the function returns the error.

`expect` survives where `unwrap` does not because it forces the author to write the reason down. "the pattern is a literal" is a claim a reviewer can check. "failed to parse" is a description of the panic, not a reason it cannot happen, and is the tell of a `?` that was not written.

## The shape of a library's error

A library's caller needs to tell failures apart, so the error is an enum of the kinds of failure the library can report, each carrying what the caller needs to act on it:

```rust
#[derive(Debug, thiserror::Error)]
#[non_exhaustive]
pub enum Error {
    #[error("reading {path}")]
    Io { path: PathBuf, #[source] source: std::io::Error },
    #[error("line {line}: expected a key")]
    Syntax { line: usize },
}
```

Each choice there is a condition somewhere. The variant names a kind, not a call site: one `Io` variant for every file the library opens, with the path that failed, rather than one variant per function. The cause is kept with `#[source]` (or `#[from]`, which also writes the `From` impl), so `Error::source()` returns it and a reporter can print the chain — [`rules/error-types.md`](../rules/error-types.md) condition 3. The enum is `#[non_exhaustive]`, so a new kind of failure is not a breaking release — [`rules/non-exhaustive.md`](../rules/non-exhaustive.md). And it holds nothing that is not `Send + Sync`, so it crosses threads and `.await` points — condition 2.

Two alternatives come up. **A struct with a private kind**: `pub struct Error { kind: ErrorKind, … }` with `pub fn kind(&self) -> &ErrorKind`, the shape `std::io::Error` and ripgrep's regex crates use; it lets the library add context fields without touching the enum, at the cost of one more type. **One error type per module** rather than per crate: worth it when the modules are used independently and fail in unrelated ways, as in a workspace of separately published crates; within one crate it mostly produces conversions between the crate's own errors.

A type alias, `pub type Result<T> = std::result::Result<T, Error>;`, is conventional and harmless. It is not opaque — the hook reads through it — because the error it names is the crate's own.

## What an application does instead

An application is the last caller. Nobody matches on its errors; a person reads them. So it wants the opposite trade: one error type that anything converts into, and a message that says what the program was doing at each level. That is `anyhow::Result` and `.context()`:

```rust
let text = std::fs::read_to_string(&path)
    .with_context(|| format!("reading {}", path.display()))?;
```

The printed chain is "reading config.toml: No such file or directory", which tells the person what to fix. The line between the two styles is the crate boundary: a workspace's library crates use `thiserror`, and the binary crate that ties them together uses `anyhow`. [`libraries.md`](libraries.md) gives the reasons for these two crates over their alternatives.

## `?`, `From` and where conversion happens

`?` returns early on an `Err` after converting it with `From::from` into the function's own error type. That makes the `From` impls the map of which failures turn into which: `#[from] std::io::Error` means every `?` on an I/O call in this crate becomes `Error::Io`. Two consequences follow.

A `From` that flattens distinct failures into one variant hides the distinction from the caller. If the library reads two files and both convert through one `From<io::Error>`, the caller cannot tell which failed; the variant carries the path, set with `.map_err` at the call site, and not a blanket `From`.

`map_err` that discards its argument is the cause-dropping the rule forbids. `.map_err(|e| Error::Parse { line, source: e })` keeps it; `.map_err(|_| Error::Parse { line })` does not, and `clippy::map_err_ignore` says so.

## `Option` is not an error

`Option<T>` says a value may be absent and that absence is normal: a lookup that finds nothing, an iterator that ends. Converting it to an error is a decision the caller makes with `.ok_or(Error::NotFound { key })` when absence is a failure in its context. A library returns `Option` for "not found" and leaves that decision to the caller, rather than returning `Err(NotFound)` and forcing every caller who expected absence to match it away.

## Translating an error at the boundary

An error carries its cause, and the cause carries whatever the dependency put in it: an SDK's access-denied message names the account, the role, the action and the resource; a driver's error names the host and the query. That detail is what the operator needs and what the caller must never see, and the 2026-11-12 incident that [`rules/redaction.md`](../rules/redaction.md) begins with is this mistake. So the boundary of each layer translates:

```rust
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let id = Uuid::new_v4();
        tracing::error!(error_id = %id, error = %self.source_chain(), "request failed");
        (self.status(), Json(Problem::new(self.kind(), id))).into_response()
    }
}
```

The response carries a status, a kind the API documents and a correlation id; the full chain goes to the log, under the field allowlist [`rules/redaction.md`](../rules/redaction.md) condition 2 asks for. A library does the same one level down: its error enum names the kind of failure and keeps the dependency's error as `#[source]`, so the decision about how much to show is left to the application that owns the boundary. A `Display` that interpolates `{source}` into its own message, as `#[error("upload failed: {0}")]` does, moves the dependency's text into every place the error is printed; `#[error("upload failed")]` with the source attached keeps it in the chain, where a logger that walks `source()` finds it and a response that prints only `Display` does not.

## Panics in a server

A panic in a request handler unwinds that task, not the process: Tokio catches it at the task boundary, and `axum` turns it into a 500 when the `tower-http` `CatchPanic` layer is installed. That keeps one bug from taking down every request in flight, and it is a reason to install that layer, not a reason to panic. What it does not do is record the panic anywhere but stderr. A server installs a panic hook with `std::panic::set_hook` that sends the panic's message and location through `tracing`, so a panic reaches the same place every other failure does; the predecessor's `codex-rust-system-design` asked for this and the advice stands.

## Where this stops

**`unsafe` code's errors are not covered.** An `unsafe` block's precondition is not an error to return; it is an invariant to argue, and [`rules/unsafe-code.md`](../rules/unsafe-code.md) owns it.

**Error codes for an HTTP API are a contract question.** Mapping a library's variants to statuses and problem documents is the API's contract, which `ahrena-engineering-fundamentals` treats as authored, not derived. Meilisearch's `meilisearch-types` crate, which the predecessor cited, is an example of keeping that mapping in one place.

**Retries are not error handling.** Whether to try again is a reliability decision about the failure's kind, and [`libraries.md`](libraries.md) names the crate; `ahrena-engineering-reliability`'s review reads where retries are placed.
