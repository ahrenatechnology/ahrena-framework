---
id: utf8-io
type: rule
clade: engineering
subclade: rust
title: Bytes from outside are not assumed to be UTF-8
statement: Rust reading files, stdin, pipes or sockets of unguaranteed encoding handles invalid UTF-8 as data, and a test feeds it invalid bytes.
enforcement: judgment
references:
  - docs/performance.md
  - docs/toolchain.md
---

# Bytes from outside are not assumed to be UTF-8

A Rust `String` is valid UTF-8 by construction, so turning bytes into one is a check that can fail. Files written by other programs, logs, source trees, command output and anything a user pipes in are bytes, and a few of them are not UTF-8: a Latin-1 file, a binary blob in a text directory, a truncated multi-byte sequence. A program that reads them as strings either stops at the first one or skips it without saying so. [`docs/performance.md`](../docs/performance.md) explains why ripgrep reads bytes and what `bstr` gives a program that does the same.

Inherited from the predecessor's `lex-rust-no-assume-utf8-on-io`, drawn from Andrew Gallant's [A byte string library for Rust](https://burntsushi.net/bstr/).

**What the specification says.** A `str` is valid UTF-8 as a library invariant, not a language one: the Reference treats `str` like `[u8]` and says the methods working on it "assume and ensure" valid UTF-8 ([String slice type](https://doc.rust-lang.org/reference/types/str.html)), and does not list invalid UTF-8 as undefined behaviour. The standard library is what enforces it, which is why `String::from_utf8` and `BufRead::lines` return an error on invalid bytes and `from_utf8_unchecked` is `unsafe`. Which bytes are text is a property of the input, not of Rust, and the conditions below are about the input.

## Conditions

1. **Bytes read from a source whose encoding no protocol guarantees are not converted with `String::from_utf8(…).unwrap()`, `read_to_string`, `BufRead::lines` or `str::from_utf8(…)?` as the only path.** Decided by a reviewer. A source is guaranteed when a protocol or a schema states the encoding and the program rejects what violates it — a JSON body, a database column with a declared UTF-8 encoding, a configuration file this program wrote. Anything else is read as bytes (`Vec<u8>`, `&[u8]`, `bstr`'s `ByteSlice` and `BufReadExt::byte_lines`), converted lossily where the output is for display (`String::from_utf8_lossy`), or validated with the invalid case handled as a value, not as a failure of the whole read.

2. **`lines()` and its relatives do not drop the lines that fail to decode.** Decided by Clippy's `clippy::lines_filter_map_ok`, in the default `suspicious` group, denied. `reader.lines().filter_map(Result::ok)` silently skips every line that is not valid UTF-8, and loops for ever on a reader that keeps failing; the lint's own documentation names the second consequence.

3. **A function that reads such a source has a test that feeds it bytes that are not UTF-8, and asserts what it does with them.** Decided by a reviewer, who looks for the test. `b"caf\xe9\n"` (Latin-1) and `b"\xff\xfe"` are enough. Without the test, condition 1 is a claim about code nobody ran on the input it is about.

## Where this stops

**Paths are not strings either, and this rule does not reach them.** A file name on Unix is bytes and on Windows is UTF-16-ish; `Path` and `OsStr` exist so a program does not have to convert. Converting a path to `&str` to print it is `Path::display`; converting it to manipulate it is the defect, and `reviewing-rust` reads it.

**A program may decide that it only handles UTF-8, and say so.** A tool documented to accept UTF-8 input, which reports invalid input with a clear error naming the file and the byte offset, satisfies condition 1: the invalid case is handled, as an error the user can act on. What the rule refuses is the panic, the silent skip, and the error that does not say which file.

**Protocols with a declared encoding are trusted to the extent the program enforces them.** An HTTP body whose `Content-Type` says UTF-8 is still bytes until the decoder accepts it; the rule does not ask a program to second-guess a decoder that already returned an error on invalid input.

**Text processing beyond decoding is out of scope.** Normalisation, grapheme clusters and case folding are the domain's choice; [`strings.md`](strings.md) covers the one Unicode trap the standard library's API sets.
