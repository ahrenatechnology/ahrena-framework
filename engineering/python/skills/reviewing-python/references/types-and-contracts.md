# Python types and contracts

Opened by step 2 of `SKILL.md` when the change touches a signature, an annotation, a dataclass or a public callable. `rules/typing.md` is the rule; `hooks/check-typing.py` decides its mechanical conditions on the changed lines. These are the conditions a reader is left with.

### PY-T1 An annotation that lies about what the function returns

- **State:** a return type that one path violates: annotated `-> Foo` but a branch returns `None`, annotated `-> list[str]` but a path returns a tuple, annotated non-optional but `.get()` or an early `return` yields `None`.
- **Detect:** read every `return` and every implicit fall-off-the-end (which returns `None`). Compare each with the annotation.
- **Exempt:** none — if a path returns `None`, the type is `X | None`.
- **Correct:** widen the annotation to the real union, or make every path return the declared type.

### PY-T2 `Any` that erases a type others depend on

- **State:** `Any` on a public parameter or return, or an untyped container (`list`, `dict` with no parameters) on a surface, where the real type is known. `rules/typing.md` requires every `Any` to carry a justifying comment.
- **Detect:** read the public signatures the change adds or edits. `Any` propagates: a caller of an `Any`-returning function loses checking on everything downstream.
- **Exempt:** a genuine boundary (deserialised external JSON, a dynamic plugin loader) with the comment the rule requires.
- **Correct:** the concrete type, a `Protocol`, a `TypeVar`, or `object` when the body truly treats it opaquely.

### PY-T3 A dataclass or domain value that is mutable or unhashable by accident

- **State:** a `@dataclass` (no `frozen=True`) used as a value that is put in a set, used as a dict key, or shared and assumed immutable; or `eq=True` with `frozen=False`, which sets `__hash__` to `None` and breaks hashing silently.
- **Detect:** read the class and how instances are used. A value object that two owners share must not be mutable.
- **Exempt:** an entity whose identity is a field and whose mutation is intended.
- **Correct:** `@dataclass(frozen=True)` for a value; a stated identity and `eq`/`hash` on it for an entity.

### PY-T4 `Optional` collapsed without a check

- **State:** a value typed `X | None` used as `X` — attribute access, indexing, arithmetic — with no `is None` guard on the path.
- **Detect:** follow each optional the change introduces to its first use. mypy in strict mode catches this; a project not running strict does not.
- **Exempt:** a guard earlier on the same path, or an `assert x is not None` with a reason.
- **Correct:** guard and handle the `None`, or narrow with an early return.

### PY-T5 A protocol or ABC claimed but not met

- **State:** a class annotated as implementing a `Protocol` or subclassing an ABC whose method signatures do not match — a parameter renamed, a return narrowed, a method missing — or a `raise NotImplementedError` left in a concrete type.
- **Detect:** compare the class's methods with the protocol's. A structural `Protocol` mismatch is only caught where an instance is passed to the typed parameter.
- **Exempt:** an intentionally abstract base, declared abstract.
- **Correct:** match the signatures, or stop claiming the protocol.

### PY-T6 A public name added with no annotation at all

- **State:** a new public function, method or module constant on an API surface with no annotations, in a codebase whose `rules/typing.md` requires them.
- **Detect:** the signatures the change adds that are reachable from outside their module.
- **Exempt:** a private helper (leading underscore) whose types are obvious from the body, when the project exempts those.
- **Correct:** annotate every parameter and the return.
