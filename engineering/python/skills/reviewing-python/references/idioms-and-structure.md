# Python idioms and structure

Opened by step 2 of `SKILL.md` when the change touches an import, a package boundary or a module's public surface. `rules/module-boundaries.md` owns the import graph; this covers the reading it leaves and the idioms a reader judges.

### PY-I1 A resource opened without a context manager

- **State:** a file, a socket, a lock, a database connection or cursor opened and closed by hand, so an exception between the two leaks it; or a bare `open()` whose handle is never closed.
- **Detect:** read each acquire. A `try/finally` by hand is the weaker form; a missing close is the defect.
- **Exempt:** a resource deliberately kept open past the block, handed to a caller that owns closing it.
- **Correct:** `with`. For several, one `with a, b:` or `ExitStack`.

### PY-I2 A wildcard import, or a public surface left undeclared

- **State:** `from x import *`; or a module that grew a public API with no `__all__`, so `import *` and tooling cannot tell public from private.
- **Detect:** read the import block and the module's top level. A wildcard import makes the origin of a name unfindable and shadows silently.
- **Exempt:** a package `__init__.py` re-exporting a curated surface, with `__all__` set.
- **Correct:** import the names used; declare `__all__` on a module others import from.

### PY-I3 A circular or layering-violating import worked around

- **State:** an import placed inside a function to dodge a circular import; an import that crosses the layer direction `rules/module-boundaries.md` sets (a lower layer importing a higher one).
- **Detect:** a function-local import of a first-party module is the tell. Follow it: it usually means the two modules each need the other.
- **Exempt:** a function-local import that breaks a genuinely optional or heavy dependency, with a comment, or one the boundaries rule's own hook accepts.
- **Correct:** move the shared type to a lower module both depend on; invert the dependency with a protocol.

### PY-I4 A comprehension or generator doing too much

- **State:** a comprehension with side effects, nested two or more levels deep, or wrapping a multi-clause expression that a loop would read more clearly; a comprehension built only to be discarded (used as a loop).
- **Detect:** read the comprehension. If it mutates, calls for its effect, or needs a second read to parse, it is a loop written sideways.
- **Exempt:** a flat, single-clause comprehension that maps or filters — the idiom this is not about.
- **Correct:** a `for` loop for effects; a named helper for the inner clause; keep comprehensions to one map and one filter.

### PY-I5 Equality, ordering or representation that disagree

- **State:** a class that defines `__eq__` but not `__hash__` (unhashable, see PY-T3) or `__lt__` without the rest; a `__repr__` that is not reconstructive where the project expects one; mixed rich-comparison that is not total.
- **Detect:** read the dunder methods the change adds. Partial ordering breaks `sorted` and `min`/`max` in ways that depend on input order.
- **Exempt:** a class that defines only what it needs and is never sorted or hashed.
- **Correct:** `functools.total_ordering` for ordering from one operator; define `__hash__` with `__eq__`; `@dataclass` generates a consistent set.

### PY-I6 Metaprogramming where a plain definition would do

- **State:** `setattr`/`getattr` with a computed name, `__getattr__`, a metaclass, `exec`/`eval`, or `**kwargs` passthrough, used where the set of names is fixed and known.
- **Detect:** read what the dynamism buys. If the keys are a closed set the author knows, it hides them from the reader and from the type checker for nothing.
- **Exempt:** a genuine framework seam where the names are not known at authoring time.
- **Correct:** name the attributes; use a dataclass or a dict; pass explicit parameters.
