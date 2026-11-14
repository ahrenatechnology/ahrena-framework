---
id: nil-safety
type: rule
clade: engineering
subclade: go
title: The nil traps the compiler lets through
statement: Go code never writes to a map that may be nil, never returns a typed nil as an interface, and asserts types with the comma-ok form unless a panic is intended.
enforcement: judgment
references:
  - docs/error-handling.md
  - docs/toolchain.md
---

# The nil traps the compiler lets through

`nil` in Go is not one value. It is the zero value of six kinds of type, and three of them behave in ways a reader who knows another language does not expect: a nil map can be read and cannot be written, an interface holding a nil pointer is not a nil interface, and a type assertion that fails panics unless it is asked not to. Each compiles. Each is a run-time panic or a branch taken the wrong way. The conditions below are those three and the dereference that follows an unchecked result.

[`docs/error-handling.md`](../docs/error-handling.md) works the typed-nil error, the form of the second trap that `if err != nil` turns into a wrong branch.

## Conditions

1. **No element is assigned into a map that may be nil.** A map declared with `var m map[K]V`, or a struct field of map type that no constructor initialises, is made with `make` or a composite literal before the first write. Decided by `staticcheck`'s `SA5000` where the nil is provable, and by a reviewer for a map reached through a field. Source: the Go specification, *Map types* — "A nil map is equivalent to an empty map except that no elements may be added."

2. **A function whose result type is an interface never returns a nil pointer of a concrete type through it.** `var e *MyError; return e` from a function returning `error` gives the caller an interface that is not nil, so `if err != nil` takes the failure branch on success. The success path returns the untyped `nil`. Decided by a reviewer, who reads every return of an interface-typed result that is a variable of pointer type. `staticcheck`'s `SA4023` reports the comparison at the other end when it can prove it is always true or always false. Source: the Go FAQ, *Why is my nil error value not equal to nil?* — "An interface value is `nil` only if the `V` and `T` are both unset."

3. **A type assertion on a value that may hold another type uses the two-result form `v, ok := x.(T)`.** The single-result form panics when the assertion is false, which is correct only where a different type is a programmer's broken invariant. Decided by `forcetypeassert`, enabled by the project, with the exemption granted by a reviewer. Source: the Go specification, *Type assertions* — "If the type assertion is false, a run-time panic occurs."
   - **Exempt:** an assertion whose failure is impossible by construction — the value was put there by the same package under the same key — where the panic is the invariant check [`errors.md`](errors.md) condition 5 allows.

4. **A pointer returned beside an error is not dereferenced before the error is checked, and not after the error said it is invalid.** Decided by the `nilness` analyzer, which `gopls` runs by default in the editor but `go vet` does not run, and by a reviewer. For the `net/http` case, `go vet`'s `httpresponse` analyzer decides it in CI, and [`resources.md`](resources.md) condition 2 holds it.

## Where this stops

**Condition 1 does not reach a nil map read.** Reading, ranging over and taking `len` of a nil map are all defined and return the zero value, which is what makes a nil map a correct "empty" in a struct that is only read. Only the write panics.

**Condition 2 is not decided by a linter, and the reason is the type system.** Whether a pointer variable can be nil at a given `return` is a data-flow question across the function; `nilness` answers part of it in the editor, and nothing in the default CI set answers it at all. A reviewer reads every function that returns an interface and has a pointer-typed local of the type it implements.

**Condition 3 does not reach a type switch.** A `switch v := x.(type)` never panics on a type it does not list; it falls to `default` or does nothing. Whether the missing case is a defect is `exhaustive`'s question for enums and a reviewer's for interfaces.

**Condition 4's analyzer is not in the gate.** `nilness` ships in `golang.org/x/tools` and runs in `gopls`; it is not part of `go vet`'s default set, so a project that wants it in CI adds it through `golangci-lint`'s `govet` settings, as [`docs/toolchain.md`](../docs/toolchain.md) describes. Until it does, condition 4 is a reviewer's.

**A nil function value, a nil channel and a nil pointer receiver are not here.** Calling a nil function panics and `go vet`'s `nilfunc` catches the comparison form; a nil channel blocks forever, which is a goroutine leak and belongs to [`concurrency.md`](concurrency.md); a method on a nil pointer receiver is legal and sometimes deliberate. None of the three is a trap in the sense above — code that compiles and does something other than it reads — so none earns a condition here.
