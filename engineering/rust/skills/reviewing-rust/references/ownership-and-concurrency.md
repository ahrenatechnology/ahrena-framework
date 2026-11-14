# Rust ownership and concurrency

Opened by step 2 of `SKILL.md` when the change touches an `Rc`/`Arc` structure, a `Send`/`Sync`/`'static` bound, or an iterator chain. The borrow checker accepts all of these; a reader asks whether they are the right design.

A needless clone, an `Rc` or `RefCell` added to quiet the borrow checker, and a guard held across an `.await` are not here: they are `rules/ownership.md` conditions 3 and 4 and `rules/async-blocking.md` condition 2. RS-7, RS-8 and RS-10 were retired into those rules and their identifiers are not reused.

### RS-9 `Rc`/`Arc` cycles, or the wrong one chosen

- **State:** an `Rc`/`Arc` graph that can form a cycle with no `Weak`, leaking memory; `Rc` used where values cross threads (will not compile — but the fix of reaching for `Arc`+`Mutex` everywhere is its own smell); `Arc<Mutex<T>>` cloned widely where a channel or ownership would be clearer.
- **Detect:** read the reference-counted structure for back-edges and for how widely the handle is shared.
- **Exempt:** a tree with parent `Weak` pointers; a genuinely shared cache behind `Arc`.
- **Correct:** `Weak` for back-references; pass ownership or use channels instead of shared mutable state; keep the locked section small.

### RS-11 A `Send`/`Sync`/`'static` bound widened or an `unsafe impl`

- **State:** `unsafe impl Send`/`Sync` for a type with no argument that it is sound; a `'static` bound added to a public generic to make a spawn compile, over-constraining callers; a trait object `Box<dyn Trait>` where `+ Send` is silently required by a later change.
- **Detect:** read the bounds the change adds to a public signature and any `unsafe impl`.
- **Exempt:** a sound `unsafe impl` with a safety comment; a `'static` that is genuinely required.
- **Correct:** justify the `unsafe impl` or remove it; take the narrowest bound that works; add `+ Send` deliberately and document it on the surface.

### RS-12 An iterator or allocation pattern that does needless work

- **State:** `.collect::<Vec<_>>()` only to iterate once; `.clone()` inside `.map`; indexing in a loop where an iterator reads clearer; building a `String` with `+` in a loop instead of `push_str`/`write!`.
- **Detect:** read the iterator chain the change adds. A collect that feeds a single `for` is an allocation for nothing.
- **Exempt:** a collect needed because the borrow ends, or because the result is reused.
- **Correct:** chain the iterator without collecting; borrow in the closure; `push_str` or `format!` once.
