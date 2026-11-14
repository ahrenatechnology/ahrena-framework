#!/usr/bin/env python3
"""Tests for check-python.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing fixture and by the carve-out it must not
flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

The hook serves four rules, and the carve-outs are where each one earns its
place. error-handling must stay quiet on a handler that re-raises or exits,
on a handler that `check-typing.py` already reports, and on a loop that ends
inside a `finally`. immutability must read only a `domain/` tree and must let
a frozen class, a justified class and a method's own receiver through.
testing must let a patch into an adapter through. security must accept a
literal command, a safe YAML loader, a filtered archive and a reason.

The criteria of the issue this suite was written for:

    #286/AC-3 every condition the hook decides has a case here that failed
              against an accepting stub before the hook existed, and passes
    #286/AC-6 the plugin carries no `.gitkeep`, checked by `placeholders`
    #286/AC-7 this suite passes, beside test-check-typing.py and
              test-check-boundaries.py

Usage:
    python3 engineering/python/hooks/test-check-python.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-python.py"

CLEAN = '''
def add(left: int, right: int) -> int:
    return left + right
'''


BASE_LOGGED_NOT_RAISED = '''
import logging

logger = logging.getLogger(__name__)


def run() -> None:
    try:
        work()
    except BaseException:
        logger.exception("work failed")
'''

BARE_LOGGED_NOT_RAISED = '''
import logging


def run() -> None:
    try:
        work()
    except:
        logging.exception("work failed")
'''

BASE_RE_RAISED = '''
import logging


def run() -> None:
    try:
        work()
    except BaseException:
        logging.exception("work failed")
        raise
'''

BASE_RE_RAISED_BY_NAME = '''
def run() -> None:
    try:
        work()
    except BaseException as failure:
        cleanup()
        raise failure
'''

BASE_TRANSLATED = '''
class WorkFailed(Exception):
    pass


def run() -> None:
    try:
        work()
    except BaseException as failure:
        raise WorkFailed("work failed") from failure
'''

ENTRY_POINT_EXITS = '''
import logging
import sys


def main() -> None:
    try:
        work()
    except BaseException:
        logging.exception("work failed")
        sys.exit(1)
'''

LEFT_TO_TYPING = '''
def run() -> None:
    try:
        work()
    except:
        pass
'''

CANCELLATION_SWALLOWED = '''
import asyncio


async def run() -> None:
    try:
        await work()
    except asyncio.CancelledError:
        await cleanup()
'''

CANCELLATION_IMPORTED_SWALLOWED = '''
from asyncio import CancelledError


async def run() -> None:
    try:
        await work()
    except (TimeoutError, CancelledError):
        return None
'''

CANCELLATION_RE_RAISED = '''
import asyncio


async def run() -> None:
    try:
        await work()
    except asyncio.CancelledError:
        await cleanup()
        raise
'''

BASE_JUSTIFIED = '''
import logging


def main() -> int:
    try:
        work()
    except BaseException:  # a cost recorder must never fail the session that runs it
        logging.exception("record failed")
    return 0
'''

INTERRUPT_NAMED = '''
def main() -> int:
    try:
        work()
    except KeyboardInterrupt:
        return 130
    return 0
'''


VANILLA_CALL = '''
def charge(amount: int) -> None:
    if amount < 0:
        raise Exception("amount must be positive")
'''

VANILLA_BARE = '''
def charge(amount: int) -> None:
    if amount < 0:
        raise BaseException
'''

SPECIFIC_RAISE = '''
class NegativeAmount(ValueError):
    pass


def charge(amount: int) -> None:
    if amount < 0:
        raise NegativeAmount(amount)
    raise ValueError("unreachable")
'''


RETURN_IN_FINALLY = '''
def load() -> int:
    try:
        return parse()
    finally:
        return 0
'''

BREAK_IN_FINALLY = '''
def drain(items: list[int]) -> None:
    for item in items:
        try:
            handle(item)
        finally:
            break
'''

CONTINUE_IN_FINALLY = '''
def drain(items: list[int]) -> None:
    for item in items:
        try:
            handle(item)
        finally:
            continue
'''

FINALLY_OWNS_NOTHING_IT_NESTS = '''
def close(handles: list[int]) -> None:
    try:
        work()
    finally:
        for handle in handles:
            if handle < 0:
                break
            if handle == 0:
                continue

        def report() -> int:
            return 1

        report()
'''


DOMAIN_DATACLASS_MUTABLE = '''
from dataclasses import dataclass


@dataclass
class Money:
    amount: int
    currency: str
'''

DOMAIN_DATACLASS_CALLED_MUTABLE = '''
import dataclasses


@dataclasses.dataclass(eq=True)
class Money:
    amount: int
    currency: str
'''

DOMAIN_ATTRS_MUTABLE = '''
import attrs


@attrs.define
class Money:
    amount: int
    currency: str
'''

DOMAIN_DATACLASS_FROZEN = '''
from dataclasses import dataclass

import attrs


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str


@attrs.frozen
class Rate:
    value: int
'''

DOMAIN_DATACLASS_JUSTIFIED = '''
from dataclasses import dataclass


# the ledger entity is identified by its id and its balance moves on purpose
@dataclass
class Ledger:
    entity_id: str
    balance: int
'''


DOMAIN_APPENDS_TO_ARGUMENT = '''
def enrich(tags: list[str]) -> list[str]:
    tags.append("enriched")
    return tags
'''

DOMAIN_WRITES_INTO_ARGUMENT = '''
def enrich(metadata: dict[str, bool]) -> dict[str, bool]:
    metadata["enriched"] = True
    return metadata
'''

DOMAIN_DELETES_FROM_ARGUMENT = '''
def strip(metadata: dict[str, bool]) -> None:
    del metadata["internal"]
'''

DOMAIN_COPIES_ITS_ARGUMENT = '''
class Basket:
    def __init__(self, items: list[str]) -> None:
        self.items = list(items)

    def add(self, item: str) -> None:
        self.items.append(item)


def enrich(tags: list[str]) -> list[str]:
    copied = list(tags)
    copied.append("enriched")
    return [*tags, "enriched"]
'''


PATCH_DOMAIN_BY_STRING = '''
from unittest import mock


def test_fee() -> None:
    with mock.patch("billing.domain.fees.calculate_fee", return_value=0):
        assert charge() == 0
'''

PATCH_APPLICATION_WITH_MOCKER = '''
def test_fee(mocker) -> None:
    mocker.patch("components.billing.application.create_invoice.CreateInvoice.execute")
    assert charge() == 0
'''

PATCH_OBJECT_FROM_DOMAIN = '''
from unittest.mock import patch

from billing.domain.fees import FeeSchedule


def test_fee() -> None:
    with patch.object(FeeSchedule, "rate", return_value=0):
        assert charge() == 0
'''

MONKEYPATCH_DOMAIN = '''
from billing.domain import fees


def test_fee(monkeypatch) -> None:
    monkeypatch.setattr(fees, "calculate_fee", lambda amount: 0)
    assert charge() == 0
'''

PATCH_AN_ADAPTER = '''
from unittest import mock

from billing.infra import gateway


def test_fee(monkeypatch) -> None:
    monkeypatch.setattr(gateway, "post", lambda payload: None)
    with mock.patch("billing.infra.clock.now", return_value=0):
        with mock.patch.dict("os.environ", {"MODE": "test"}):
            assert charge() == 0
'''


HTTP_PATCH_IS_NOT_A_MOCK = '''
import httpx
import requests


def update(order_id: str) -> None:
    httpx.patch("https://api.domain.example/orders", json={"id": order_id})
    requests.patch("https://payments.application.io/x")
'''

DOMAIN_EXTENDS_ITS_ARGUMENT_IN_PLACE = '''
def enrich(tags: list[str], seen: set[str], count: int) -> int:
    tags += ["enriched"]
    seen |= {"enriched"}
    count += 1
    return count
'''

EVAL_OF_A_VALUE = '''
def compute(expression: str) -> int:
    return eval(expression)
'''

EXEC_OF_A_LITERAL = '''
def warm() -> None:
    exec("import json")
'''

PICKLE_LOADS = '''
import pickle


def restore(blob: bytes) -> object:
    return pickle.loads(blob)
'''

PICKLE_IMPORTED_BY_NAME = '''
from pickle import load


def restore(handle) -> object:
    return load(handle)
'''

YAML_UNSAFE = '''
import yaml


def read(text: str) -> object:
    return yaml.load(text, Loader=yaml.Loader)
'''

YAML_SAFE = '''
import yaml


def read(text: str) -> object:
    first = yaml.load(text, Loader=yaml.SafeLoader)
    second = yaml.load(text, yaml.CSafeLoader)
    return yaml.safe_load(text) or first or second
'''

SHELL_TRUE = '''
import subprocess


def archive(name: str) -> None:
    subprocess.run(f"tar czf {name}.tgz data", shell=True, check=True)
'''

OS_SYSTEM = '''
import os


def archive(name: str) -> None:
    os.system("tar czf " + name)
'''

SHELL_LITERAL = '''
import subprocess


def disk() -> str:
    return subprocess.run("df -h | tail -1", shell=True, capture_output=True, text=True).stdout
'''

TAR_UNFILTERED = '''
import tarfile


def unpack(path: str, target: str) -> None:
    with tarfile.open(path) as archive:
        archive.extractall(target)
'''

TAR_FILTERED = '''
import tarfile


def unpack(path: str, target: str) -> None:
    with tarfile.open(path) as archive:
        archive.extractall(target, filter="data")
'''

ZIP_UNFILTERED = '''
import zipfile


def unpack(path: str, target: str) -> None:
    with zipfile.ZipFile(path) as archive:
        archive.extractall(target)
'''

ZIP_BESIDE_TAR = '''
import tarfile
import zipfile


def unpack(path: str, target: str) -> None:
    with zipfile.ZipFile(path) as archive:
        archive.extractall(target)
    with tarfile.open(path) as bundle:
        bundle.extractall(target, filter="data")
'''

TLS_OFF = '''
import httpx


def fetch(url: str) -> bytes:
    return httpx.get(url, verify=False).content
'''

TLS_UNVERIFIED_CONTEXT = '''
import ssl


def context() -> ssl.SSLContext:
    return ssl._create_unverified_context()
'''

SECURITY_JUSTIFIED = '''
import pickle


def restore(path: str) -> object:
    with open(path, "rb") as handle:
        # the cache file is written by this process alone, under a 0600 directory
        return pickle.load(handle)
'''

SECURITY_DIRECTIVE_IS_NOT_A_REASON = '''
import pickle


def restore(blob: bytes) -> object:
    return pickle.loads(blob)  # noqa: S301
'''


BROKEN = "def unclosed(:\n"


Case = tuple[str, dict[str, str], list[str], bool]


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> Case:
    return (name, files, expect, ok)


CASES = [
    case("a clean module passes", {"a.py": CLEAN}, ["1 file(s), no failures"], ok=True),
    case(
        "except BaseException that logs and carries on fails",
        {"a.py": BASE_LOGGED_NOT_RAISED},
        ["[error-handling] condition 1", "a.py:10", "KeyboardInterrupt"],
    ),
    case(
        "a bare except that logs and carries on fails",
        {"a.py": BARE_LOGGED_NOT_RAISED},
        ["[error-handling] condition 1", "`except:`"],
    ),
    case("re-raising with a bare raise passes", {"a.py": BASE_RE_RAISED}, ["no failures"], ok=True),
    case("re-raising the bound name passes", {"a.py": BASE_RE_RAISED_BY_NAME}, ["no failures"], ok=True),
    case(
        "translating BaseException into an ordinary error still fails",
        {"a.py": BASE_TRANSLATED},
        ["[error-handling] condition 1"],
    ),
    case("an entry point that exits passes", {"a.py": ENTRY_POINT_EXITS}, ["no failures"], ok=True),
    case(
        "a handler check-typing already reports is left to it",
        {"a.py": LEFT_TO_TYPING},
        ["no failures"],
        ok=True,
    ),
    case(
        "swallowing asyncio.CancelledError fails",
        {"a.py": CANCELLATION_SWALLOWED},
        ["[error-handling] condition 1", "cancellation"],
    ),
    case(
        "CancelledError imported by name and caught in a tuple fails",
        {"a.py": CANCELLATION_IMPORTED_SWALLOWED},
        ["[error-handling] condition 1"],
    ),
    case(
        "re-raising CancelledError after cleanup passes",
        {"a.py": CANCELLATION_RE_RAISED},
        ["no failures"],
        ok=True,
    ),
    case(
        "catching BaseException with a reason passes",
        {"a.py": BASE_JUSTIFIED},
        ["no failures"],
        ok=True,
    ),
    case("naming KeyboardInterrupt is a decision", {"a.py": INTERRUPT_NAMED}, ["no failures"], ok=True),
    case(
        "raise Exception(...) fails",
        {"a.py": VANILLA_CALL},
        ["[error-handling] condition 2", "a.py:4", "Exception"],
    ),
    case("raise BaseException fails", {"a.py": VANILLA_BARE}, ["[error-handling] condition 2"]),
    case("raising a named class passes", {"a.py": SPECIFIC_RAISE}, ["no failures"], ok=True),
    case(
        "a return inside finally fails",
        {"a.py": RETURN_IN_FINALLY},
        ["[error-handling] condition 3", "a.py:6", "return"],
    ),
    case("a break inside finally fails", {"a.py": BREAK_IN_FINALLY}, ["[error-handling] condition 3", "break"]),
    case(
        "a continue inside finally fails",
        {"a.py": CONTINUE_IN_FINALLY},
        ["[error-handling] condition 3", "continue"],
    ),
    case(
        "a loop or a function nested in finally owns its own exits",
        {"a.py": FINALLY_OWNS_NOTHING_IT_NESTS},
        ["no failures"],
        ok=True,
    ),
    case(
        "a mutable dataclass under domain/ fails",
        {"billing/domain/money.py": DOMAIN_DATACLASS_MUTABLE},
        ["[immutability] condition 1", "money.py:5", "Money"],
    ),
    case(
        "a dataclass called without frozen=True fails",
        {"billing/domain/money.py": DOMAIN_DATACLASS_CALLED_MUTABLE},
        ["[immutability] condition 1"],
    ),
    case(
        "an attrs.define class under domain/ fails",
        {"billing/domain/money.py": DOMAIN_ATTRS_MUTABLE},
        ["[immutability] condition 1"],
    ),
    case(
        "frozen dataclasses and attrs.frozen pass",
        {"billing/domain/money.py": DOMAIN_DATACLASS_FROZEN},
        ["no failures"],
        ok=True,
    ),
    case(
        "a mutable domain dataclass with a reason passes",
        {"billing/domain/ledger.py": DOMAIN_DATACLASS_JUSTIFIED},
        ["no failures"],
        ok=True,
    ),
    case(
        "a mutable dataclass outside domain/ is not read",
        {"billing/infra/models.py": DOMAIN_DATACLASS_MUTABLE},
        ["no failures"],
        ok=True,
    ),
    case(
        "a domain function appending to its argument fails",
        {"billing/domain/tags.py": DOMAIN_APPENDS_TO_ARGUMENT},
        ["[immutability] condition 2", "tags.py:3", "enrich", "tags"],
    ),
    case(
        "a domain function writing a key into its argument fails",
        {"billing/domain/meta.py": DOMAIN_WRITES_INTO_ARGUMENT},
        ["[immutability] condition 2", "metadata"],
    ),
    case(
        "a domain function deleting from its argument fails",
        {"billing/domain/meta.py": DOMAIN_DELETES_FROM_ARGUMENT},
        ["[immutability] condition 2"],
    ),
    case(
        "a copy, and a method changing its own receiver, pass",
        {"billing/domain/basket.py": DOMAIN_COPIES_ITS_ARGUMENT},
        ["no failures"],
        ok=True,
    ),
    case(
        "an argument mutated outside domain/ is not read",
        {"billing/infra/tags.py": DOMAIN_APPENDS_TO_ARGUMENT},
        ["no failures"],
        ok=True,
    ),
    case(
        "patching a domain function by its dotted path fails",
        {"tests/test_fee.py": PATCH_DOMAIN_BY_STRING},
        ["[testing] condition 1", "test_fee.py:6", "billing.domain.fees.calculate_fee"],
    ),
    case(
        "patching a use case with mocker fails",
        {"tests/test_fee.py": PATCH_APPLICATION_WITH_MOCKER},
        ["[testing] condition 1", "application"],
    ),
    case(
        "patch.object on a class imported from domain fails",
        {"tests/test_fee.py": PATCH_OBJECT_FROM_DOMAIN},
        ["[testing] condition 1", "FeeSchedule"],
    ),
    case(
        "monkeypatch.setattr on a domain module fails",
        {"tests/test_fee.py": MONKEYPATCH_DOMAIN},
        ["[testing] condition 1", "fees"],
    ),
    case(
        "patching an adapter, a clock and the environment passes",
        {"tests/test_fee.py": PATCH_AN_ADAPTER},
        ["no failures"],
        ok=True,
    ),
    case(
        "an HTTP PATCH call is not a mock patch",
        {"tests/test_orders.py": HTTP_PATCH_IS_NOT_A_MOCK},
        ["no failures"],
        ok=True,
    ),
    case(
        "an augmented assignment on a list or set parameter fails, on an int it does not",
        {"billing/domain/tags.py": DOMAIN_EXTENDS_ITS_ARGUMENT_IN_PLACE},
        ["[immutability] condition 2", "`tags`", "`seen`"],
    ),
    case(
        "eval of a value fails",
        {"a.py": EVAL_OF_A_VALUE},
        ["[security] condition 1", "a.py:3", "eval"],
    ),
    case("exec of a string literal passes", {"a.py": EXEC_OF_A_LITERAL}, ["no failures"], ok=True),
    case("pickle.loads fails", {"a.py": PICKLE_LOADS}, ["[security] condition 2", "pickle.loads"]),
    case(
        "pickle's load imported by name fails",
        {"a.py": PICKLE_IMPORTED_BY_NAME},
        ["[security] condition 2", "pickle.load"],
    ),
    case(
        "yaml.load with an unsafe loader fails",
        {"a.py": YAML_UNSAFE},
        ["[security] condition 2", "yaml.load"],
    ),
    case("yaml with a safe loader passes", {"a.py": YAML_SAFE}, ["no failures"], ok=True),
    case(
        "shell=True with an interpolated command fails",
        {"a.py": SHELL_TRUE},
        ["[security] condition 3", "a.py:6", "shell"],
    ),
    case("os.system with a built command fails", {"a.py": OS_SYSTEM}, ["[security] condition 3", "os.system"]),
    case("a shell with a literal command passes", {"a.py": SHELL_LITERAL}, ["no failures"], ok=True),
    case(
        "a tar archive extracted with no filter fails",
        {"a.py": TAR_UNFILTERED},
        ["[security] condition 4", "a.py:7", "filter"],
    ),
    case("a tar archive extracted with a filter passes", {"a.py": TAR_FILTERED}, ["no failures"], ok=True),
    case("a zip archive is not read", {"a.py": ZIP_UNFILTERED}, ["no failures"], ok=True),
    case(
        "a zip archive beside a tar import is still not read",
        {"a.py": ZIP_BESIDE_TAR},
        ["no failures"],
        ok=True,
    ),
    case("verify=False fails", {"a.py": TLS_OFF}, ["[security] condition 5", "verify=False"]),
    case(
        "an unverified SSL context fails",
        {"a.py": TLS_UNVERIFIED_CONTEXT},
        ["[security] condition 5", "_create_unverified_context"],
    ),
    case(
        "a reason on the line above satisfies a security condition",
        {"a.py": SECURITY_JUSTIFIED},
        ["no failures"],
        ok=True,
    ),
    case(
        "a tool directive is not a reason",
        {"a.py": SECURITY_DIRECTIVE_IS_NOT_A_REASON},
        ["[security] condition 2"],
    ),
    case(
        "a file this interpreter cannot parse is skipped, not failed",
        {"a.py": CLEAN, "broken.py": BROKEN},
        ["1 file(s), no failures (1 skipped)"],
        ok=True,
    ),
    case(
        "generated, vendored and dot-prefixed trees are not walked",
        {
            "a.py": CLEAN,
            "node_modules/vendor/b.py": PICKLE_LOADS,
            "__pycache__/c.py": VANILLA_CALL,
            ".venv/lib/domain/d.py": DOMAIN_DATACLASS_MUTABLE,
        },
        ["1 file(s), no failures"],
        ok=True,
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


def placeholders() -> list[Path]:
    """Every `.gitkeep` left in the plugin, which should hold content instead."""
    plugin = Path(__file__).resolve().parent.parent
    return sorted(plugin.rglob(".gitkeep"))


def main() -> int:
    failed = 0
    left = placeholders()
    if left:
        failed += 1
        print("FAIL  the plugin carries no .gitkeep")
        for path in left:
            print(f"        {path}")
    else:
        print("ok    the plugin carries no .gitkeep")
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            report_failure(name, problems, output)
        else:
            print(f"ok    {name}")
    return summarise(failed, len(CASES) + 1)


if __name__ == "__main__":
    sys.exit(main())
