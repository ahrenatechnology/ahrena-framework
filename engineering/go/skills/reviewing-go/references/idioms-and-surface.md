# Go idioms and surface

Opened by step 2 of `SKILL.md` when the change touches an interface, a nil comparison, a defer, a slice or map aliased, or an exported identifier.

### GO-13 A nil interface that is not nil

- **State:** a typed nil pointer returned as an interface — `var e *MyError; return e` where the signature returns `error` — so the caller's `if err != nil` is true even though the pointer is nil; or a `nil` map written to (which panics) after being returned as an empty map.
- **Detect:** read where a concrete nil pointer becomes an interface value. An interface is nil only when both its type and value are nil.
- **Exempt:** returning the untyped `nil` directly.
- **Correct:** return `nil` explicitly on the success path; check the concrete pointer before wrapping it in the interface.

### GO-14 An interface returned, or defined at the producer

- **State:** a constructor that returns an interface instead of the concrete type, hiding fields and forcing every caller through the abstraction; or an interface declared next to its single implementation rather than where it is consumed.
- **Detect:** read the new interface and count its implementations and consumers. Go's idiom is "accept interfaces, return structs," and interfaces belong to the consumer.
- **Exempt:** an interface with two or more real implementations, or one a package exports as its contract on purpose.
- **Correct:** return the concrete type; define the interface in the consuming package, as small as the consumer needs. This is `rules/yagni.md` in Go's clothing.

### GO-15 A slice aliasing its backing array after append or re-slice

- **State:** a sub-slice (`s[1:3]`) handed out or stored, then the original `append`ed, so the two share the array and one mutates the other; a slice returned from a function that keeps a reference to it; `append` to a slice argument assumed not to affect the caller.
- **Detect:** read where a slice is sub-sliced or appended and also shared. `append` may or may not reallocate, so the aliasing bug is intermittent.
- **Exempt:** a slice copied (`append([]T(nil), s...)` or `copy`) before being shared.
- **Correct:** copy when handing out or retaining a sub-slice; use the three-index slice to cap capacity; document when a function retains a slice argument.

### GO-16 A zero value or an uninitialised map misused

- **State:** a `map` declared but not made (`var m map[k]v`) then written to (panic); a struct used expecting a constructor's defaults that the zero value does not provide; a `time.Time{}` or other zero value flowing where a real value was assumed.
- **Detect:** read the declaration against the first use. Reading a nil map is fine; writing panics.
- **Exempt:** a zero value the type is designed to make useful (`sync.Mutex`, `bytes.Buffer`).
- **Correct:** `make(map...)` before writing; a constructor where the zero value is not valid.

### GO-17 An exported identifier added without a doc comment, or exported by accident

- **State:** a new exported function, type, field or constant on a package's surface with no doc comment, where the package documents its API; or something exported (capitalised) that is only used inside its package.
- **Detect:** read the exported names the change adds. `golint`/`revive` flag the missing comment; a reader catches the needless export.
- **Exempt:** an identifier whose meaning is unmistakable in a package that does not document internals.
- **Correct:** a doc comment starting with the identifier name; lower-case an identifier that has no caller outside the package.

### GO-18 A `defer` for cleanup that the hot path pays for, or a resource with none

- **State:** a resource (file, response body, rows, lock) opened with no `defer` to close it on every path; or `defer` used in a tight loop (see GO-5) where the cleanup should be per-iteration.
- **Detect:** each acquire that has an error path between it and its release. A missing `resp.Body.Close()` leaks a connection.
- **Exempt:** a resource whose lifetime deliberately exceeds the function, handed to a caller that closes it.
- **Correct:** `defer x.Close()` right after a successful acquire; extract a loop body so its defers run each iteration.
