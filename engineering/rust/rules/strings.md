---
id: strings
type: rule
clade: engineering
subclade: rust
title: A string is sliced on a character boundary
statement: Rust slices a `str` only at an index known to be a char boundary, and counts characters with `chars()`, never with `len()`.
enforcement: judgment
references:
  - docs/api-design.md
  - docs/toolchain.md
---

# A string is sliced on a character boundary

A `str` is UTF-8, so a character is one to four bytes, and every index into a `str` is a byte offset. `&s[0..n]` compiles for any `s` and panics at run time when byte `n` falls inside a character, which it does as soon as the text leaves ASCII: `"hello"[0..2]` is fine and `"ação"[0..2]` panics, because `ç` occupies bytes 1 and 2. The same confusion makes `s.len()` a byte count that a reader takes for a character count. Both are invisible in tests that only use English. [`docs/api-design.md`](../docs/api-design.md) covers the parameter half of string handling.

Inherited from the predecessor's `lex-rust-string-types`, which drew on the first edition of the Rust book. Two of its four conditions are not here. Indexing a `str` by an integer does not compile, so a rule against it guards nothing. Accepting `&str` rather than `String` or `&String` for a read-only parameter is [`ownership.md`](ownership.md) conditions 1 and 2, decided by the same Clippy lints, and stating it twice would give one condition two owners.

**What the specification says.** A `str` is a sequence of bytes that is valid UTF-8 ([String slice type](https://doc.rust-lang.org/reference/types/str.html)), and slicing it is the standard library's `Index` implementation, documented to panic when a bound is not on a character boundary ([`str` indexing](https://doc.rust-lang.org/std/primitive.str.html#method.get)). `len` returns a length in bytes, as its documentation says. The conditions below are the reading those two facts call for.

## Conditions

1. **A `str` is sliced by a range only when each bound is a char boundary the code established: a value from `find`, `char_indices`, `match_indices` or a regex match, `0`, or `len()`.** Decided by a reviewer, with Clippy's `clippy::string_slice`, from the `restriction` group, as a finder: it reports every range slice of a string, and the reviewer reads each one for where its bounds came from. A bound computed by arithmetic — `n`, `n + 1`, `len() - 3` — is a finding unless the text is ASCII by a check the code makes, and `str::get(range)` returns `None` instead of panicking when it is not.

2. **A count, limit or truncation that is about characters is computed over `chars()`, and one about display width or grapheme clusters says so and uses a crate that computes it.** Decided by a reviewer. `s.len() > 80` limits bytes. A limit shown to a person is almost never about bytes, and truncating to it with condition 1's slice is the panic again. `unicode-segmentation` counts grapheme clusters and `unicode-width` counts terminal columns; neither is in the standard library.

## Where this stops

**Byte-oriented text is out of scope.** A protocol whose fields are byte lengths, a parser over ASCII tokens, a search that works on `&[u8]`: each counts bytes because bytes are what it means, and [`utf8-io.md`](utf8-io.md) is the rule for data that may not be UTF-8 at all.

**`clippy::string_slice` is not required to be denied.** It reports every correct slice as well as the wrong ones, so denying it turns condition 1 into an `allow` on every parser. It is the reviewer's search tool.

**Normalisation and case folding are not addressed.** Two strings that render the same may differ in bytes; comparing them correctly is a question about the domain's text, and the rule does not pick an answer.
