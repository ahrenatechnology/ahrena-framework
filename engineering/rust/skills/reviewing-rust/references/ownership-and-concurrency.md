# Rust ownership and concurrency

Opened by step 2 of `SKILL.md` when the change touches a `clone`, a borrow, a lifetime, an `Rc`/`RefCell`/`Arc`/`Mutex`, or a thread boundary. The borrow checker accepts all of these; a reader asks whether they are the right design.

### RS-7 A `clone` that hides a borrow or a design problem

- **State:** `.clone()` added to satisfy the borrow checker rather than because a copy is wanted — cloning a large `Vec`/`String`/struct in a loop, cloning to pass to a function that only reads, `.to_vec()`/`.to_owned()` where a slice would do.
- **Detect:** each `clone` the change adds. Ask whether the callee needs ownership or only a reference.
- **Exempt:** a cheap clone (`Rc`/`Arc` handle, a `Copy` type), or one that is genuinely the simplest correct option.
- **Correct:** pass `&T`/`&str`/`&[T]`; restructure lifetimes; move once instead of cloning repeatedly; `Cow` when ownership is conditional.

### RS-8 `RefCell`/`Mutex` that moves a borrow error to runtime

- **State:** `RefCell` or `Cell` used to get around the borrow checker, so an aliased-mutable access that would not compile now panics at runtime (`already borrowed`); a `Mutex` the same lock path can re-enter and deadlock.
- **Detect:** read why the interior mutability is there. If it exists only to avoid rethinking ownership, it has converted a compile error into a runtime one.
- **Exempt:** a genuine shared-mutable-state pattern (a graph, an observer) where interior mutability is the known tool.
- **Correct:** restructure ownership so the borrow checker is satisfied statically; narrow the `borrow_mut` scope; avoid holding one `RefCell` borrow across a call that re-borrows.

### RS-9 `Rc`/`Arc` cycles, or the wrong one chosen

- **State:** an `Rc`/`Arc` graph that can form a cycle with no `Weak`, leaking memory; `Rc` used where values cross threads (will not compile — but the fix of reaching for `Arc`+`Mutex` everywhere is its own smell); `Arc<Mutex<T>>` cloned widely where a channel or ownership would be clearer.
- **Detect:** read the reference-counted structure for back-edges and for how widely the handle is shared.
- **Exempt:** a tree with parent `Weak` pointers; a genuinely shared cache behind `Arc`.
- **Correct:** `Weak` for back-references; pass ownership or use channels instead of shared mutable state; keep the locked section small.

### RS-10 A lock held across an `.await` or a blocking call

- **State:** a `std::sync::Mutex`/`RwLock` guard held across an `.await` point (the guard is not `Send`, and it blocks the async runtime), or across I/O that serialises every task.
- **Detect:** read each lock scope in async code for an `.await` between `lock()` and the guard's drop.
- **Exempt:** a short critical section with no await inside.
- **Correct:** drop the guard before awaiting (scope it in a block); use an async-aware lock (`tokio::sync::Mutex`) only when the lock must span an await; compute under the lock, await after.

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
