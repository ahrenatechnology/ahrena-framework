# Rust errors and surface

Opened by step 2 of `SKILL.md` when the change touches a `Result`/`Option` handled, a `?` conversion, a `pub` item, a trait or a generic bound.

A library's opaque or cause-dropping error type is not here: it is `rules/error-types.md`. RS-13 was retired into that rule and its identifier is not reused.

### RS-14 `?` that converts an error the caller cannot interpret

- **State:** `?` relying on a `From` that flattens several distinct failures into one variant, so the caller cannot tell them apart; or `?` in a function whose error type is `Box<dyn Error>` where a typed error was the contract.
- **Detect:** follow what `?` produces against what the signature promises and what callers match on.
- **Exempt:** a conversion that genuinely preserves the distinction, or an application boundary.
- **Correct:** distinct error variants with their own `From`; keep the typed error on the public signature.

### RS-15 An `Option`/`Result` combinator chain that hides a panic or a swallow

- **State:** `.unwrap_or_default()` that masks a real error as an empty value; `.ok()` discarding an error that mattered; a long `map`/`and_then` chain ending in `.unwrap()`; `.filter_map` that silently drops the `Err`s of a fallible parse.
- **Detect:** read what each combinator does with the failure case. A default or a drop where the caller needed to know is a silent swallow.
- **Exempt:** a default that is genuinely correct for the absence, with the intent clear.
- **Correct:** handle the error explicitly; `collect::<Result<Vec<_>,_>>()` to fail on the first bad element when that is wanted.

### RS-16 A public item exposed or over-constrained by accident

- **State:** a `pub` (rather than `pub(crate)`) item that leaks an internal type or an implementation detail into the crate's API; a returned concrete type where `impl Trait` was meant, or the reverse.
- **Detect:** read the `pub` surface the change adds. In a library, every `pub` is a promise that `semver` then binds.
- **Exempt:** an item meant to be public, taking an owned value because it stores it.
- **Correct:** `pub(crate)` for internal items; expose the narrowest type the callers need. A parameter that should be borrowed is `rules/ownership.md` conditions 1 and 2.

### RS-17 A trait bound, blanket impl or `Default` that is wrong or missing

- **State:** a trait with a method that should have a default and does not (every impl repeats it); a blanket `impl<T> Trait for T` that conflicts or captures more than intended; a `derive(Default)` whose zero value is not a valid instance; `PartialEq`/`Hash` derived inconsistently (see the fundamentals value-semantics rule).
- **Detect:** read the trait and its impls the change adds. A `Default` that produces an invalid state is the common trap.
- **Exempt:** a deliberate design with a comment.
- **Correct:** a default method where impls would repeat; a hand-written `Default` or none; keep `Eq`/`Hash`/`Ord` mutually consistent.
