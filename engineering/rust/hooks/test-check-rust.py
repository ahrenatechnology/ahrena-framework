#!/usr/bin/env python3
"""Tests for check-rust.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing fixture and by the carve-outs it must
not flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

The carve-outs are where the work is. Condition 1 of rules/error-types.md must
stay quiet on a binary, on `pub(crate)`, on test code, on a crate's own error
type and on an alias that resolves to it, and must not read a comment or a
string as a signature. Condition 1 of rules/async-blocking.md must resolve a
name through the file's `use` declarations, so `tokio::fs::read` passes where
`std::fs::read` fails, and must not reach a closure handed to `spawn_blocking`
or a function that is not async.

Usage:
    python3 engineering/rust/hooks/test-check-rust.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-rust.py"

MANIFEST = '[package]\nname = "probe"\nversion = "0.1.0"\nedition = "2024"\n'


TESTED = """
#[cfg(test)]
mod tests {
    #[test]
    fn works() {}
}
"""


def tested(source: str) -> str:
    """The source with a unit test beside it, as rules/unit-tests.md asks."""
    return source + TESTED


def library(source: str) -> dict[str, str]:
    """A library crate whose root module is `source`, with its unit test."""
    return {"Cargo.toml": MANIFEST, "src/lib.rs": tested(source)}



OWN_ERROR = """
#[derive(Debug)]
#[non_exhaustive]
pub enum ParseError {
    Syntax { line: usize },
}

pub fn parse(text: &str) -> Result<usize, ParseError> {
    Ok(text.len())
}
"""

ANYHOW_RESULT = """
pub fn parse(text: &str) -> anyhow::Result<usize> {
    Ok(text.len())
}
"""

BOXED_ERROR = """
pub fn connect(url: &str) -> Result<Vec<String>, Box<dyn std::error::Error + Send + Sync>> {
    Ok(vec![url.to_string()])
}
"""

STRING_ERROR = """
pub struct Parser;

impl Parser {
    pub fn parse(&self, text: &str) -> Result<u8, String> {
        text.parse().map_err(|_| "bad".to_string())
    }
}
"""

STATIC_STR_ERROR = """
pub fn divide(a: i32, b: i32) -> Result<i32, &'static str> {
    if b == 0 { Err("zero") } else { Ok(a / b) }
}
"""

IMPORTED_ANYHOW = """
use anyhow::{Context, Result};

pub fn load(path: &str) -> Result<String> {
    std::fs::read_to_string(path).context("read")
}
"""

OWN_ALIAS = """
#[derive(Debug)]
pub enum Error {
    Io(std::io::Error),
}

pub type Result<T> = std::result::Result<T, Error>;

pub fn load(path: &str) -> Result<String> {
    std::fs::read_to_string(path).map_err(Error::Io)
}
"""

OPAQUE_ALIAS = """
pub type Result<T> = anyhow::Result<T>;
"""

CRATE_PRIVATE = """
pub(crate) fn parse(text: &str) -> anyhow::Result<usize> {
    Ok(text.len())
}

fn private(text: &str) -> Result<usize, String> {
    Ok(text.len())
}
"""

MULTI_LINE = """
pub fn search<P>(
    pattern: P,
    haystack: &[u8],
) -> Result<
    Vec<usize>,
    Box<dyn std::error::Error>,
>
where
    P: AsRef<str>,
{
    let _ = (pattern, haystack);
    Ok(Vec::new())
}
"""

IN_TEST_MODULE = """
pub fn add(a: u8, b: u8) -> u8 {
    a + b
}

#[cfg(test)]
mod tests {
    pub fn helper() -> anyhow::Result<()> {
        Ok(())
    }
}
"""

IN_COMMENT_AND_STRING = """
// pub fn old() -> anyhow::Result<()> was removed in 0.3.
/* pub fn older() -> Result<(), String> */
pub fn describe() -> &'static str {
    "pub fn quoted() -> anyhow::Result<()>"
}
"""

CALLBACK_ALIAS = """
pub type SetupHook = Box<dyn FnOnce(&str) -> Result<(), Box<dyn std::error::Error>> + Send>;
pub type Resolving = Box<dyn std::future::Future<Output = Result<Vec<u8>, BoxError>> + Send>;
"""

ERROR_AS_VALUE = """
pub struct Wrapped;

impl Wrapped {
    pub fn into_boxed(self) -> Box<dyn std::error::Error + Send + Sync> {
        todo!()
    }
}
"""

LOCAL_BOX_ALIAS = """
type BoxError = Box<dyn std::error::Error + Send + Sync>;

pub fn serve() -> Result<(), BoxError> {
    Ok(())
}
"""

DOC_HIDDEN = """
#[doc(hidden)]
pub fn check_invariants(&self) -> Result<(), String> {
    Ok(())
}
"""

BINARY_MAIN = """
fn main() -> anyhow::Result<()> {
    Ok(())
}

pub fn run() -> anyhow::Result<()> {
    Ok(())
}
"""


ASYNC_CLEAN = """
use tokio::fs;

pub async fn load(path: &str) -> std::io::Result<Vec<u8>> {
    fs::read(path).await
}
"""

FULL_PATH_SLEEP = """
pub async fn wait() {
    std::thread::sleep(std::time::Duration::from_millis(5));
}
"""

IMPORTED_MODULE = """
use std::fs;

pub async fn load(path: &str) -> std::io::Result<Vec<u8>> {
    fs::read(path)
}
"""

IMPORTED_TYPE = """
use std::fs::File;

pub async fn open(path: &str) -> std::io::Result<File> {
    File::open(path)
}
"""

NESTED_USE_TREE = """
use std::{fs::{self, File}, thread};

pub async fn wait() {
    thread::sleep(std::time::Duration::from_millis(5));
}
"""

RENAMED_IMPORT = """
use std::thread::sleep as nap;

pub async fn wait() {
    nap(std::time::Duration::from_millis(5));
}
"""

ASYNC_BLOCK = """
pub fn job() -> impl std::future::Future<Output = ()> {
    async move {
        let _ = std::fs::read_to_string("config.toml");
    }
}
"""

BLOCKING_METHOD = """
pub async fn drain(mut rx: tokio::sync::mpsc::Receiver<u8>) -> Option<u8> {
    rx.blocking_recv()
}
"""

BLOCKING_CLIENT = """
pub async fn fetch(url: &str) -> Result<String, reqwest::Error> {
    reqwest::blocking::get(url)?.text()
}
"""

SPAWN_BLOCKING = """
use std::fs;

pub async fn load(path: String) -> Vec<u8> {
    tokio::task::spawn_blocking(move || {
        fs::read(&path).unwrap_or_default()
    })
    .await
    .unwrap_or_default()
}
"""

SYNC_FUNCTION = """
use std::fs;

pub fn load(path: &str) -> std::io::Result<Vec<u8>> {
    std::thread::sleep(std::time::Duration::from_millis(5));
    fs::read(path)
}
"""

ASYNC_COMMENT = """
pub async fn wait() {
    // std::thread::sleep(d) blocked here before tokio::time::sleep replaced it.
    tokio::time::sleep(std::time::Duration::from_millis(5)).await;
}
"""

ASYNC_TEST = """
pub fn add(a: u8, b: u8) -> u8 {
    a + b
}

#[cfg(test)]
mod tests {
    #[tokio::test]
    async fn waits() {
        std::thread::sleep(std::time::Duration::from_millis(1));
    }
}
"""


# #287: rules/dependency-direction.md, conditions 1 and 2

MODULE_ROOT = tested("pub mod a;\npub mod b;\n")

CYCLE_A = tested("""use crate::b::Beta;

pub struct Alpha;

pub fn from_beta(_: Beta) -> Alpha {
    Alpha
}
""")

CYCLE_B = tested("""pub struct Beta;

pub fn back() -> crate::a::Alpha {
    crate::a::Alpha
}
""")

ONE_WAY_B = tested("""pub struct Beta;
""")

NESTED_ROOT = tested("pub mod a;\npub mod b;\npub use crate::a::Alpha;\n")

NESTED_A = tested("pub mod inner;\npub struct Alpha;\n")

NESTED_INNER = tested("""use super::super::b::Beta;
use crate::Alpha;

pub fn pair(_: Alpha, _: Beta) {}
""")

NESTED_B = tested("""use crate::a::inner;

pub struct Beta;

pub fn call() {
    inner::pair(crate::a::Alpha, Beta);
}
""")

WORKSPACE = """[workspace]
members = ["crates/*"]

[workspace.metadata.ahrena]
layers = ["domain", "application", "infrastructure"]
"""


def member(name: str, layer: str, dependencies: str = "") -> str:
    return (
        f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2024"\n\n'
        f'[package.metadata.ahrena]\nlayer = "{layer}"\n\n[dependencies]\n{dependencies}'
    )


# #287: rules/unit-tests.md, condition 1

UNTESTED = """
pub fn add(a: u8, b: u8) -> u8 {
    a + b
}
"""

ONLY_DECLARATIONS = """
pub mod parse;

pub use parse::Parsed;

pub trait Source {
    fn read(&self) -> Vec<u8>;
}
"""

ONLY_MAIN = """
fn main() {
    probe::run();
}
"""

# #287: rules/redaction.md, condition 1

SECRET_DEBUG = """
#[derive(Debug, Clone)]
pub struct Config {
    pub url: String,
    pub api_key: String,
}
"""

SECRET_WRAPPED = """
#[derive(Debug, Clone)]
pub struct Config {
    pub url: String,
    pub api_key: secrecy::SecretString,
}
"""

SECRET_SERIALIZED = """
#[derive(serde::Serialize)]
pub struct Login {
    pub user: String,
    pub password: String,
}
"""

SECRET_VARIANT = """
#[derive(Debug)]
pub enum Auth {
    Anonymous,
    Bearer { access_token: String },
}
"""

HAND_WRITTEN_DEBUG = """
pub struct Config {
    pub api_key: String,
}

impl std::fmt::Debug for Config {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Config").field("api_key", &"[redacted]").finish()
    }
}
"""

INNOCENT_NAMES = """
#[derive(Debug)]
pub struct Page {
    pub cache_key: String,
    pub token_count: usize,
    pub tokens: Vec<String>,
}
"""


CFG_TEST_FIELD = """
pub struct Probe {
    #[cfg(test)]
    pub calls: usize,
}

impl Probe {
    pub fn parse(&self) -> anyhow::Result<u8> {
        Ok(1)
    }
}
"""

NESTED_CFG_TEST = """
#[cfg(test)]
mod tests {
    #[cfg(test)]
    fn helper() {}

    #[test]
    fn works() {}
}

pub async fn wait() {
    std::thread::sleep(std::time::Duration::from_millis(5));
}
"""

NON_SECRET_TYPES = """
#[derive(Debug)]
pub struct Waker {
    pub token: mio::Token,
    pub brace_token: syn::token::Brace,
    pub allow_credentials: bool,
}
"""

SECRET_OPTION = """
#[derive(Debug)]
pub struct Login {
    pub client_secret: Option<String>,
}
"""

TRIANGLE_A = tested("pub fn a() { crate::b::b(); }\n")
TRIANGLE_B = tested("pub fn b() { crate::c::c(); crate::a::a(); }\n")
TRIANGLE_C = tested("pub fn c() { crate::a::a(); }\n")


def case(
    name: str, files: dict[str, str], expect: list[str], ok: bool = False
) -> tuple[str, dict[str, str], list[str], bool]:
    return (name, files, expect, ok)


CASES = [
    case("a library returning its own error type passes", library(OWN_ERROR), ["no failures"], ok=True),
    case(
        "anyhow::Result on a public function of a library fails",
        library(ANYHOW_RESULT),
        ["[error-types] condition 1", "parse returns anyhow::Result", "src/lib.rs:2"],
    ),
    case(
        "a boxed dyn Error on a public function fails",
        library(BOXED_ERROR),
        ["[error-types] condition 1", "connect returns Box<dyn std::error::Error"],
    ),
    case(
        "a String error on a public method fails",
        library(STRING_ERROR),
        ["[error-types] condition 1", "parse returns String as its error", "src/lib.rs:5"],
    ),
    case(
        "a static str error fails",
        library(STATIC_STR_ERROR),
        ["[error-types] condition 1", "divide returns &'static str as its error"],
    ),
    case(
        "Result imported from anyhow is anyhow's",
        library(IMPORTED_ANYHOW),
        ["[error-types] condition 1", "load returns anyhow::Result"],
    ),
    case("an alias over the crate's own error passes", library(OWN_ALIAS), ["no failures"], ok=True),
    case(
        "a public alias over anyhow fails",
        library(OPAQUE_ALIAS),
        ["[error-types] condition 1", "type Result is anyhow::Result"],
    ),
    case("a boxed error inside a callback type is not an error channel", library(CALLBACK_ALIAS), ["no failures"], ok=True),
    case("a boxed error returned as the value is not an error channel", library(ERROR_AS_VALUE), ["no failures"], ok=True),
    case(
        "an alias for a boxed error in the same file is followed",
        library(LOCAL_BOX_ALIAS),
        ["[error-types] condition 1", "serve returns BoxError, an alias of Box<dyn std::error::Error"],
    ),
    case("an item hidden from the documentation is not the surface", library(DOC_HIDDEN), ["no failures"], ok=True),
    case("pub(crate) and private functions are not the surface", library(CRATE_PRIVATE), ["no failures"], ok=True),
    case(
        "a signature split over lines is read whole, and reported where it starts",
        library(MULTI_LINE),
        ["[error-types] condition 1", "search returns Box<dyn std::error::Error>", "src/lib.rs:2"],
    ),
    case("a test module is not the surface", library(IN_TEST_MODULE), ["no failures"], ok=True),
    case("a comment and a string are not signatures", library(IN_COMMENT_AND_STRING), ["no failures"], ok=True),
    case(
        "a binary crate may return anyhow",
        {"Cargo.toml": MANIFEST, "src/main.rs": tested(BINARY_MAIN)},
        ["no failures"],
        ok=True,
    ),
    case(
        "a binary target beside a library may return anyhow",
        {
            "Cargo.toml": MANIFEST,
            "src/lib.rs": tested(OWN_ERROR),
            "src/bin/tool.rs": tested(BINARY_MAIN),
            "src/main.rs": tested(BINARY_MAIN),
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "integration tests and examples of a library are not its surface",
        {
            "Cargo.toml": MANIFEST,
            "src/lib.rs": tested(OWN_ERROR),
            "tests/load.rs": ANYHOW_RESULT,
            "examples/demo.rs": ANYHOW_RESULT,
        },
        ["no failures"],
        ok=True,
    ),
    case("a file outside any crate is not read as a library", {"loose.rs": ANYHOW_RESULT}, ["no failures"], ok=True),
    case("tokio's fs awaited inside async passes", library(ASYNC_CLEAN), ["no failures"], ok=True),
    case(
        "std::thread::sleep by its full path inside async fails",
        library(FULL_PATH_SLEEP),
        ["[async-blocking] condition 1", "std::thread::sleep", "src/lib.rs:3"],
    ),
    case(
        "fs imported from std is std's",
        library(IMPORTED_MODULE),
        ["[async-blocking] condition 1", "std::fs::read"],
    ),
    case(
        "a type imported from std::fs opens synchronously",
        library(IMPORTED_TYPE),
        ["[async-blocking] condition 1", "std::fs::File::open"],
    ),
    case(
        "a nested use tree is expanded",
        library(NESTED_USE_TREE),
        ["[async-blocking] condition 1", "std::thread::sleep"],
    ),
    case(
        "a renamed import is followed to its path",
        library(RENAMED_IMPORT),
        ["[async-blocking] condition 1", "std::thread::sleep"],
    ),
    case(
        "an async block inside a sync function is async",
        library(ASYNC_BLOCK),
        ["[async-blocking] condition 1", "std::fs::read_to_string", "src/lib.rs:4"],
    ),
    case(
        "a blocking_ method inside async fails",
        library(BLOCKING_METHOD),
        ["[async-blocking] condition 1", "blocking_recv"],
    ),
    case(
        "reqwest's blocking client inside async fails",
        library(BLOCKING_CLIENT),
        ["[async-blocking] condition 1", "reqwest::blocking::get"],
    ),
    case("a closure handed to spawn_blocking may block", library(SPAWN_BLOCKING), ["no failures"], ok=True),
    case("a function that is not async may block", library(SYNC_FUNCTION), ["no failures"], ok=True),
    case("a comment inside async is not a call", library(ASYNC_COMMENT), ["no failures"], ok=True),
    case("a test module is not read", library(ASYNC_TEST), ["no failures"], ok=True),
    case(
        "a tests.rs file is a test module declared elsewhere",
        {"Cargo.toml": MANIFEST, "src/lib.rs": "#[cfg(test)]\nmod tests;\n", "src/tests.rs": FULL_PATH_SLEEP},
        ["no failures"],
        ok=True,
    ),
    case(
        "a binary is held to the async condition too",
        {"Cargo.toml": MANIFEST, "src/main.rs": tested(FULL_PATH_SLEEP)},
        ["[async-blocking] condition 1", "src/main.rs:3"],
    ),
    case(
        "two modules that use each other are a cycle",
        {"Cargo.toml": MANIFEST, "src/lib.rs": MODULE_ROOT, "src/a.rs": CYCLE_A, "src/b.rs": CYCLE_B},
        ["[dependency-direction] condition 1", "crate::a -> crate::b -> crate::a", "src/a.rs:1"],
    ),
    case(
        "a dependency in one direction is not a cycle",
        {"Cargo.toml": MANIFEST, "src/lib.rs": MODULE_ROOT, "src/a.rs": CYCLE_A, "src/b.rs": ONE_WAY_B},
        ["no failures"],
        ok=True,
    ),
    case(
        "super paths resolve, nested files count, and a module may use its ancestors",
        {
            "Cargo.toml": MANIFEST,
            "src/lib.rs": NESTED_ROOT,
            "src/a.rs": NESTED_A,
            "src/a/inner.rs": NESTED_INNER,
            "src/b.rs": NESTED_B,
        },
        ["[dependency-direction] condition 1", "crate::a::inner -> crate::b -> crate::a::inner"],
    ),
    case(
        "a crate that depends on a crate of a higher layer fails",
        {
            "Cargo.toml": WORKSPACE,
            "crates/core/Cargo.toml": member("core", "domain", 'store = { path = "../store" }\n'),
            "crates/core/src/lib.rs": tested(""),
            "crates/store/Cargo.toml": member("store", "infrastructure"),
            "crates/store/src/lib.rs": tested(""),
        },
        ["[dependency-direction] condition 2", "core (domain) depends on store (infrastructure)"],
    ),
    case(
        "a crate that depends downward passes, and dev-dependencies are not read",
        {
            "Cargo.toml": WORKSPACE,
            "crates/core/Cargo.toml": member("core", "domain") + '\n[dev-dependencies]\nstore = { path = "../store" }\n',
            "crates/core/src/lib.rs": tested(""),
            "crates/store/Cargo.toml": member(
                "store", "infrastructure", 'domain-core = { package = "core", path = "../core" }\n'
            ),
            "crates/store/src/lib.rs": tested(""),
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a member whose layer the workspace does not list is reported",
        {
            "Cargo.toml": WORKSPACE,
            "crates/core/Cargo.toml": member("core", "domian"),
            "crates/core/src/lib.rs": tested(""),
        },
        ["[dependency-direction] condition 2", "core declares layer domian, which the workspace does not list"],
    ),
    case(
        "a source file with a function and no test fails",
        {"Cargo.toml": MANIFEST, "src/lib.rs": UNTESTED},
        ["[unit-tests] condition 1", "src/lib.rs has functions and no #[test] beside them"],
    ),
    case(
        "a file of declarations owes no test",
        {"Cargo.toml": MANIFEST, "src/lib.rs": ONLY_DECLARATIONS, "src/parse.rs": tested("pub struct Parsed;")},
        ["no failures"],
        ok=True,
    ),
    case(
        "a main that only calls the library owes no test",
        {"Cargo.toml": MANIFEST, "src/lib.rs": tested(""), "src/main.rs": ONLY_MAIN},
        ["no failures"],
        ok=True,
    ),
    case(
        "a unit whose tests sit in a sibling tests.rs it declares is tested",
        {
            "Cargo.toml": MANIFEST,
            "src/lib.rs": tested("pub mod parse;\n"),
            "src/parse.rs": UNTESTED + "\n#[cfg(test)]\nmod tests;\n",
            "src/parse/tests.rs": "#[test]\nfn adds() {}\n",
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a declared sibling tests.rs with no test in it does not count",
        {
            "Cargo.toml": MANIFEST,
            "src/lib.rs": tested("pub mod parse;\n"),
            "src/parse.rs": UNTESTED + "\n#[cfg(test)]\nmod tests;\n",
            "src/parse/tests.rs": "fn helper() {}\n",
        },
        ["[unit-tests] condition 1", "src/parse.rs has functions"],
    ),
    case(
        "a binary under src/bin is read as its own root",
        {"Cargo.toml": MANIFEST, "src/lib.rs": tested(""), "src/bin/tool.rs": ONLY_MAIN + UNTESTED},
        ["[unit-tests] condition 1", "src/bin/tool.rs has functions"],
    ),
    case(
        "an integration test file is not a unit",
        {"Cargo.toml": MANIFEST, "src/lib.rs": tested(UNTESTED), "tests/add.rs": UNTESTED},
        ["no failures"],
        ok=True,
    ),
    case(
        "a derived Debug over a secret field fails",
        library(SECRET_DEBUG),
        ["[redaction] condition 1", "Config derives Debug over api_key", "src/lib.rs:2"],
    ),
    case("a secret held in a redacting type passes", library(SECRET_WRAPPED), ["no failures"], ok=True),
    case(
        "a derived Serialize over a password fails",
        library(SECRET_SERIALIZED),
        ["[redaction] condition 1", "Login derives Serialize over password"],
    ),
    case(
        "a secret field of an enum variant counts",
        library(SECRET_VARIANT),
        ["[redaction] condition 1", "Auth derives Debug over access_token"],
    ),
    case("a hand-written Debug is the redaction", library(HAND_WRITTEN_DEBUG), ["no failures"], ok=True),
    case("names that only resemble a secret pass", library(INNOCENT_NAMES), ["no failures"], ok=True),
    case(
        "a cfg(test) field does not hide the impl after it",
        library(CFG_TEST_FIELD),
        ["[error-types] condition 1", "parse returns anyhow::Result"],
    ),
    case(
        "a cfg(test) inside a test module does not hide the item after the module",
        {"Cargo.toml": MANIFEST, "src/lib.rs": NESTED_CFG_TEST},
        ["[async-blocking] condition 1", "std::thread::sleep"],
    ),
    case("a token or a flag that is not text is not a secret", library(NON_SECRET_TYPES), ["no failures"], ok=True),
    case(
        "a secret inside an Option is still text",
        library(SECRET_OPTION),
        ["[redaction] condition 1", "Login derives Debug over client_secret"],
    ),
    case(
        "one cycle among three modules is one finding, however many paths run round it",
        {
            "Cargo.toml": MANIFEST,
            "src/lib.rs": tested("pub mod a;\npub mod b;\npub mod c;\n"),
            "src/a.rs": TRIANGLE_A,
            "src/b.rs": TRIANGLE_B,
            "src/c.rs": TRIANGLE_C,
        },
        ["1 failure(s)", "crate::a -> crate::b -> crate::a; crate::c is in the same cycle"],
    ),
]


def write(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp), files)
        result = subprocess.run([sys.executable, str(HOOK), "."], cwd=tmp, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    """What went wrong with this case, or nothing."""
    wanted = "pass" if ok else "fail"
    found = [] if ok == (code == 0) else [f"expected the hook to {wanted}, it did the other"]
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def report_failure(name: str, problems: list[str], output: str) -> None:
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")


def summarise(failed: int, total: int) -> int:
    print()
    if failed:
        print(f"{failed} of {total} cases failed.")
        return 1
    print(f"{total} cases passed.")
    return 0


def main() -> int:
    failed = 0
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            report_failure(name, problems, output)
        else:
            print(f"ok    {name}")
    return summarise(failed, len(CASES))


if __name__ == "__main__":
    sys.exit(main())
