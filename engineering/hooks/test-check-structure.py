#!/usr/bin/env python3
"""Tests for check-structure.py.

A detector that never accepts is as broken as one that never rejects, so every
condition below is pinned by a failing fixture and by the carve-out it must not
flag. Each case builds a throwaway tree, runs the hook against it as a
subprocess, and asserts on the exit code and the message.

Usage:
    python3 engineering/hooks/test-check-structure.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-structure.py"

CLEAN = '''
class Ledger:
    def __init__(self, rows):
        self.rows = rows

    def total(self):
        return sum(self.rows)

    def record(self, row):
        self.rows.append(row)
'''

# --- rules/solid.md condition 1: LCOM4 -------------------------------------

TWO_ACTORS = '''
class Order:
    def __init__(self, lines, printer):
        self.lines = lines
        self.printer = printer

    def total(self):
        return sum(self.lines)

    def render(self):
        return self.printer.emit()
'''

CONNECTED_BY_CALL = '''
class Report:
    def __init__(self, rows):
        self.rows = rows

    def body(self):
        return self.rows

    def render(self):
        return "".join(self.body())
'''

PROTOCOL = '''
from typing import Protocol


class Repository(Protocol):
    def load(self, key): ...

    def store(self, key, value): ...
'''

ALL_ABSTRACT = '''
from abc import ABC, abstractmethod


class Gateway(ABC):
    @abstractmethod
    def send(self, message):
        raise NotImplementedError

    @abstractmethod
    def receive(self):
        raise NotImplementedError
'''

ENUM = '''
from enum import Enum


class Colour(Enum):
    RED = 1
    BLUE = 2

    def warm(self):
        return self is Colour.RED

    def cool(self):
        return self is Colour.BLUE
'''

STATIC_ONLY = '''
class Tools:
    def __init__(self, seed):
        self.seed = seed

    def next(self):
        return self.seed + 1

    @staticmethod
    def helper(value):
        return value * 2
'''

# --- rules/solid.md condition 2: a member declared and not implemented -----

UNIMPLEMENTED = '''
class FileStore:
    def __init__(self, root):
        self.root = root

    def load(self, key):
        return self.root / key

    def store(self, key, value):
        """Write the value."""
        raise NotImplementedError
'''

GUARD_CLAUSE = '''
class Codec:
    def __init__(self, formats):
        self.formats = formats

    def decode(self, fmt, payload):
        if fmt not in self.formats:
            raise NotImplementedError(fmt)
        return payload
'''

OVERLOADED = '''
from typing import overload


@overload
def parse(value: int) -> int:
    raise NotImplementedError
'''

# --- rules/kiss.md condition 1: nesting depth ------------------------------

DEEP = '''
def sweep(groups):
    for group in groups:
        for item in group:
            for field in item:
                if field:
                    return field
    return None
'''

AT_THE_LIMIT = '''
def sweep(groups):
    for group in groups:
        for item in group:
            if item:
                return item
    return None
'''

LONG_ELIF = '''
def classify(code):
    if code == 1:
        return "a"
    elif code == 2:
        return "b"
    elif code == 3:
        return "c"
    elif code == 4:
        return "d"
    elif code == 5:
        return "e"
    return "z"
'''

NESTED_DEF = '''
def outer(rows):
    def inner(row):
        for cell in row:
            if cell:
                return cell
        return None

    for row in rows:
        if row:
            return inner(row)
    return None
'''

DEEP_IN_HANDLER = '''
def load(paths):
    for path in paths:
        try:
            return open(path)
        except OSError:
            for retry in range(3):
                if retry:
                    return None
    return None
'''

# --- rules/kiss.md condition 2: a flag argument ----------------------------

FLAG_DEFAULT = '''
def render(doc, pretty=False):
    if pretty:
        return doc.upper()
    return doc
'''

FLAG_ANNOTATED = '''
def render(doc, pretty: bool):
    if not pretty:
        return doc
    return doc.upper()
'''

FLAG_COMPARED = '''
def render(doc, pretty=False):
    if pretty is True:
        return doc.upper()
    return doc
'''

FLAG_STORED = '''
class Renderer:
    def __init__(self, pretty=False):
        self.pretty = pretty

    def render(self, doc):
        if self.pretty:
            return doc.upper()
        return doc
'''

FLAG_FORWARDED = '''
def render(doc, pretty=False):
    return doc.render(pretty=pretty)
'''

NON_BOOLEAN = '''
def render(doc, mode="plain"):
    if mode:
        return doc.upper()
    return doc
'''

# A single delegating hop is a facade, not a defect. The condition that would
# have flagged it was dropped when this fixture showed it firing on every
# collection wrapper; rules/kiss.md records why.
FACADE = '''
class Service:
    def __init__(self, repo):
        self.repo = repo

    def save(self, record):
        return self.repo.save(record)

    def load(self, key):
        return self.repo.load(key)
'''

# --- rules/clean-code.md condition 1: function size ------------------------


def _statements(count: int) -> str:
    lines = "\n".join(f"    value_{n} = {n}" for n in range(count))
    return f"def build(seed):\n{lines}\n"


OVER_THE_STATEMENT_LIMIT = _statements(31)
AT_THE_STATEMENT_LIMIT = _statements(30)

BIG_NESTED_DEF = '''
def outer(seed):
    def inner(value):
''' + "\n".join(f"        step_{n} = {n}" for n in range(31)) + '''
        return step_0

    return inner(seed)
'''

DOCSTRING_NOT_COUNTED = '''
def build(seed):
    """A docstring is not a statement of the body."""
''' + "\n".join(f"    value_{n} = {n}" for n in range(30)) + "\n"

# --- rules/clean-code.md condition 2: unreachable code ---------------------

UNREACHABLE = '''
def total(rows):
    return sum(rows)
    rows.clear()
'''

UNREACHABLE_AFTER_RAISE = '''
def total(rows):
    for row in rows:
        raise ValueError(row)
        row.clear()
    return 0
'''

EXIT_INSIDE_A_BRANCH = '''
def total(rows):
    if not rows:
        return 0
    return sum(rows)
'''

EXIT_AT_THE_END_OF_A_LOOP = '''
def first(rows):
    for row in rows:
        if row:
            continue
    return None
'''

# --- rules/clean-code.md condition 3: commented-out code -------------------

COMMENTED_OUT = '''
def total(rows):
    # rows = normalise(rows)
    return sum(rows)
'''

COMMENTED_OUT_CALL = '''
def total(rows):
    # print(rows)
    return sum(rows)
'''

PROSE_COMMENT = '''
def total(rows):
    # the caller has already normalised rows, so summing is enough here
    # Usage: total(rows)
    # see check_links for the shape this mirrors
    return sum(rows)
'''

TOOL_DIRECTIVE = '''
def total(rows):
    # type: ignore
    # noqa: E501
    # pragma: no cover
    return sum(rows)
'''

# The mixed fixture docs/clean-code.md reports against: six commented-out lines
# among ten comments that are prose about code, which is the shape that breaks
# a detector matching anything that parses.
SIXTEEN_COMMENTS = '''
# old = compute(value)
# return old
# import json
# self.cache.clear()
# print("debug")
# blocks.append(("handler", list(handler.body)))
# the limit is 3, and the overflow is rationale that belongs in a doc
# Usage:
# type: ignore
# noqa: E501
# see check_links for the shape this mirrors
# A value above 1 says the class already contains two objects
# Decided by hooks/check-structure.py for Python.
# `raise NotImplementedError` in a concrete type
# returns the map and the line number the body starts on
# `TODO` fix this before the next slice
value = 1
'''
# The last line is quoted because the corpus is sixteen comments of which six
# are code, and an unquoted marker would also be a debt-markers finding and
# make this fixture report seven. The quoting is the escape that rule takes
# from foundation/rules/completeness.md, and the comment is still prose.

# --- rules/value-semantics.md condition 1: parameter count -----------------

FIVE_PARAMETERS = '''
def connect(host, port, timeout, retries, backoff):
    return host
'''

FOUR_PARAMETERS = '''
def connect(host, port, timeout, retries):
    return host
'''

FOUR_PLUS_RECEIVER = '''
class Client:
    def connect(self, host, port, timeout, retries):
        return self.session
'''

VARIADIC = '''
def connect(host, port, timeout, retries, *rest, **extra):
    return host
'''

# --- rules/value-semantics.md condition 2: a data clump --------------------

CLUMP = '''
def connect(host, port, timeout):
    return host


def reconnect(host, port, timeout):
    return port


def probe(host, port, timeout):
    return timeout
'''

LONGER_CLUMP = '''
def connect(host, port, timeout, scheme):
    return host


def reconnect(host, port, timeout, scheme):
    return port


def probe(host, port, timeout, scheme):
    return timeout
'''

CLUMP_OF_TWO = '''
def connect(host, port, timeout):
    return host


def reconnect(host, port, timeout):
    return port
'''

SHORT_RUN = '''
def connect(host, port):
    return host


def reconnect(host, port):
    return port


def probe(host, port):
    return port
'''

# --- rules/value-semantics.md condition 3: a mutable field -----------------

FROZEN_WITH_LIST = '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    name: str
    hops: list[str]
'''

FROZEN_WITH_FACTORY = '''
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Route:
    name: str
    hops: tuple = field(default_factory=dict)
'''

FROZEN_WITH_TUPLE = '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    name: str
    hops: tuple[str, ...]
'''

NAMEDTUPLE_WITH_DICT = '''
from typing import NamedTuple


class Route(NamedTuple):
    name: str
    labels: dict[str, str]
'''

MUTABLE_DATACLASS = '''
from dataclasses import dataclass


@dataclass
class Route:
    name: str
    hops: list[str]
'''

# --- rules/value-semantics.md condition 4: the mutation escape hatch -------

SETATTR_IN_A_METHOD = '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    name: str

    def rename(self, value):
        object.__setattr__(self, "name", value)
        return self
'''

SETATTR_IN_POST_INIT = '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    name: str

    def __post_init__(self):
        object.__setattr__(self, "name", self.name.strip())
'''

# --- rules/value-semantics.md condition 5: equality without hashing --------

EQ_WITHOUT_HASH = '''
class Money:
    def __init__(self, amount):
        self.amount = amount

    def __eq__(self, other):
        return self.amount == other.amount
'''

EQ_WITH_HASH = '''
class Money:
    def __init__(self, amount):
        self.amount = amount

    def __eq__(self, other):
        return self.amount == other.amount

    def __hash__(self):
        return hash(self.amount)
'''

EQ_WITH_HASH_DISCLAIMED = '''
class Money:
    __hash__ = None

    def __init__(self, amount):
        self.amount = amount

    def __eq__(self, other):
        return self.amount == other.amount
'''

EQ_ON_A_DATACLASS = '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    amount: int

    def __eq__(self, other):
        return self.amount == other.amount
'''

# --- rules/cross-cutting-concerns.md condition 1: an inline retry ----------

INLINE_RETRY = '''
import time


def fetch(url):
    for attempt in range(3):
        try:
            return open(url)
        except OSError:
            time.sleep(attempt)
    return None
'''

POLL_WITHOUT_CATCHING = '''
import time


def wait(check):
    while not check():
        time.sleep(1)
    return True
'''

LOOP_WITHOUT_SLEEPING = '''
def scan(paths):
    for path in paths:
        try:
            return open(path)
        except OSError:
            continue
    return None
'''

# --- rules/cross-cutting-concerns.md condition 2: inline transactions ------

INLINE_TRANSACTION = '''
def save(session, record):
    try:
        session.add(record)
        session.commit()
    except RuntimeError:
        session.rollback()
        raise
'''

COMMIT_ONLY = '''
def save(session, record):
    session.add(record)
    session.commit()
    return record
'''

# --- rules/cross-cutting-concerns.md condition 3: an inline timer ----------

INLINE_TIMER = '''
import time


def handle(request):
    started = time.perf_counter()
    result = request.run()
    return result, time.perf_counter() - started
'''

ONE_CLOCK_READ = '''
import time


def stamp(record):
    record.at = time.time()
    return record
'''

TWO_CLOCK_READS_NO_DURATION = '''
import time


def stamp(record):
    record.opened = time.time()
    record.closed = time.time()
    return record
'''

# --- rules/domain-model.md condition 1: the domain imports a mechanism -----

DOMAIN_IMPORTS_ADAPTER = '''
from billing.adapters.sql import rows


def total(order):
    return rows(order)
'''

DOMAIN_IMPORTS_RELATIVE_INFRASTRUCTURE = '''
from ..infrastructure.cache import get


def total(order):
    return get(order)
'''

DOMAIN_IMPORTS_A_DRIVER = '''
import redis


def total(order):
    return redis.Redis().get(order)
'''

DOMAIN_IMPORTS_THE_DOMAIN = '''
from decimal import Decimal

from .money import Money


def total(order):
    return Money(Decimal(order.amount))
'''

ADAPTER_IMPORTS_A_DRIVER = '''
import redis


def load(key):
    return redis.Redis().get(key)
'''

# --- rules/domain-model.md condition 2: a vendor token in a domain name ----

VENDOR_IN_A_CLASS_NAME = '''
class SqlOrderGateway:
    def load(self, key):
        return key
'''

VENDOR_IN_A_FIELD_NAME = '''
class Order:
    json_payload: str
'''

VENDOR_IN_A_FUNCTION_NAME = '''
def build_dto(order):
    return order
'''

CLEAN_DOMAIN_NAMES = '''
class Order:
    placed_at: str

    def total(self):
        return self.placed_at
'''

# --- rules/duplication.md condition 1: a body copied -----------------------

# Five statements, which is the floor: the smallest body the condition
# reports. The three differ in every name and every literal and in nothing
# else, which is the state condition 1 describes.
SETTLE = '''
def settle(order):
    total = order.amount
    fee = total * 2
    if fee > 10:
        fee = 10
    return total + fee
'''

REFUND = '''
def refund(payment):
    gross = payment.value
    charge = gross * 3
    if charge > 20:
        charge = 20
    return gross + charge
'''

ADJUST = '''
def adjust(entry):
    base = entry.units
    extra = base * 7
    if extra > 4:
        extra = 4
    return base + extra
'''

THREE_COPIES = SETTLE + REFUND + ADJUST
TWO_COPIES = SETTLE + REFUND

# The same three bodies one statement shorter. Under the floor, so the
# condition does not see them however many times they are repeated.
FOUR_STATEMENTS = '''
def settle(order):
    total = order.amount
    fee = total * 2
    total = total + fee
    return total


def refund(payment):
    gross = payment.value
    charge = gross * 3
    gross = gross + charge
    return gross


def adjust(entry):
    base = entry.units
    extra = base * 7
    base = base + extra
    return base
'''

# Same statements, same node types, different wiring: the last line reuses a
# different name in each. Renaming is consistent rather than blanket, so these
# are three shapes and not one.
DIFFERENT_WIRING = '''
def first(left, right):
    head = left.value
    tail = right.value
    joined = head + tail
    total = joined + tail
    return total


def second(left, right):
    head = left.value
    tail = right.value
    joined = head + tail
    total = joined + head
    return total


def third(left, right):
    head = left.value
    tail = right.value
    joined = head + tail
    total = joined + joined
    return total
'''

# --- rules/duplication.md condition 2: a table copied ----------------------

STATUS_TABLE = '''
STATUSES = ("open", "settled", "void")


def current(order):
    return STATUSES[order.state]
'''

# The same contents under another name. The name is not the duplicate.
RENAMED_TABLE = '''
ORDER_STATES = ("open", "settled", "void")


def current(order):
    return ORDER_STATES[order.state]
'''

SHORTER_TABLE = '''
STATUSES = ("open", "void")


def current(order):
    return STATUSES[order.state]
'''

OTHER_CONTENTS = '''
STATUSES = ("open", "settled", "cancelled")


def current(order):
    return STATUSES[order.state]
'''

WRAPPED_TABLE = '''
STATUSES = frozenset({"open", "settled", "void"})


def current(order):
    return order.state in STATUSES
'''

# --- rules/debt-markers.md condition 1: a marker naming no issue -----------

# Every fixture below sits inside a string, so the hook reading this test file
# never sees a marker here. That is the same property the detector's own table
# of marker words relies on, and the reason the condition reads comments only.

UNTRACKED_LINE = '''
def fee(cents):
    # TODO: switch to the bank-specific fee table once the spec arrives
    return cents
'''

TRACKED_LINE = '''
def fee(cents):
    # TODO(#172): switch to the bank-specific fee table once the spec arrives
    return cents
'''

FOUR_MARKERS = '''
first = 1  # TODO: handle the edge case
second = 2  # TBD
third = 3  # FIXME: broken for negative numbers
fourth = 4  # XXX: refactor when we have time
'''

QUOTED_MARKER = '''
# a backticked `TODO` in a comment is prose about markers, not a marker
value = 1
'''

MARKER_IN_A_STRING = '''
MARKERS = ("TODO", "TBD", "FIXME", "XXX")
LABEL = "TODO: this is data, not a comment"
'''

NEAR_MISSES = '''
# todo: lowercase is ordinary English, not a convention
# TODOS and XXXX are longer words that happen to contain one
value = 1
'''

LATE_REFERENCE = '''
# FIXME the retry path is broken, see #3 for context
value = 1
'''

ZERO_ISSUE = '''
# TODO(#0): zero is not an issue number
value = 1
'''

ADDS_A_MARKER = CLEAN + '''
# TODO: added by this very change
'''

BROKEN = "def unclosed(:\n"

# Two reserved keys in a case's file map. BASELINE holds the tree that is
# committed first; the rest of the map is then written over it and staged, so
# the hook meets a repository with a real change in it. ARGS is the argv the
# hook is invoked with, the path included, which is how a scoped case names the
# change and how a malformed invocation is pinned. Keeping both inside the map
# leaves `case` at four parameters, which is the cap condition 1 of
# rules/value-semantics.md sets and this suite's own subject.
BASELINE = "@baseline"
ARGS = "@args"

# The staged diff: what a pre-commit hook has, and the reason the condition
# works locally rather than only in CI.
STAGED = ["--changed", "--cached", "."]

GIT_IDENTITY = ("-c", "user.email=gate@example.invalid", "-c", "user.name=gate")


def case(name: str, files: dict[str, str], expect: list[str], ok: bool = False) -> tuple:
    return (name, files, expect, ok)


CASES = [
    case("a clean tree passes", {"a.py": CLEAN}, ["1 file(s), no failures"], ok=True),
    # --- solid, condition 1
    case(
        "a class whose methods share no state fails",
        {"a.py": TWO_ACTORS},
        ["[solid] condition 1", "class Order has LCOM4 = 2", "{render} | {total}"],
    ),
    case(
        "__init__ does not connect the components it touches",
        {"a.py": TWO_ACTORS},
        ["LCOM4 = 2"],
    ),
    case(
        "methods joined only by a sibling call pass",
        {"a.py": CONNECTED_BY_CALL},
        ["no failures"],
        ok=True,
    ),
    case("a Protocol is skipped", {"a.py": PROTOCOL}, ["no failures"], ok=True),
    case("an all-abstract base is skipped", {"a.py": ALL_ABSTRACT}, ["no failures"], ok=True),
    case("an Enum is skipped", {"a.py": ENUM}, ["no failures"], ok=True),
    case(
        "a static method does not form a component of its own",
        {"a.py": STATIC_ONLY},
        ["no failures"],
        ok=True,
    ),
    # --- solid, condition 2
    case(
        "a concrete member that raises NotImplementedError fails",
        {"a.py": UNIMPLEMENTED},
        ["[solid] condition 2", "store is declared and not implemented"],
    ),
    case(
        "an @abstractmethod raising NotImplementedError passes",
        {"a.py": ALL_ABSTRACT},
        ["no failures"],
        ok=True,
    ),
    case(
        "a guard clause raising NotImplementedError passes",
        {"a.py": GUARD_CLAUSE},
        ["no failures"],
        ok=True,
    ),
    case("an @overload stub passes", {"a.py": OVERLOADED}, ["no failures"], ok=True),
    # --- kiss, condition 1
    case(
        "control flow nested 4 deep fails",
        {"a.py": DEEP},
        ["[kiss] condition 1", "sweep nests control flow 4 deep", "the limit is 3"],
    ),
    case("control flow nested 3 deep passes", {"a.py": AT_THE_LIMIT}, ["no failures"], ok=True),
    case("a long elif chain stays at one level", {"a.py": LONG_ELIF}, ["no failures"], ok=True),
    case(
        "a nested def is measured on its own, not on its enclosure",
        {"a.py": NESTED_DEF},
        ["no failures"],
        ok=True,
    ),
    case(
        "depth inside an except handler counts",
        {"a.py": DEEP_IN_HANDLER},
        ["load nests control flow 4 deep"],
    ),
    # --- kiss, condition 2
    case(
        "branching on a boolean-defaulted parameter fails",
        {"a.py": FLAG_DEFAULT},
        ["[kiss] condition 2", "render branches on the boolean parameter 'pretty'"],
    ),
    case(
        "branching on a bool-annotated parameter fails",
        {"a.py": FLAG_ANNOTATED},
        ["branches on the boolean parameter 'pretty'"],
    ),
    case(
        "comparing a boolean parameter against a literal fails",
        {"a.py": FLAG_COMPARED},
        ["branches on the boolean parameter 'pretty'"],
    ),
    case(
        "a boolean stored as state and branched on later passes",
        {"a.py": FLAG_STORED},
        ["no failures"],
        ok=True,
    ),
    case(
        "a boolean passed through without branching passes",
        {"a.py": FLAG_FORWARDED},
        ["no failures"],
        ok=True,
    ),
    case(
        "an ordinary one-hop facade is not a finding",
        {"a.py": FACADE},
        ["no failures"],
        ok=True,
    ),
    case(
        "branching on a non-boolean parameter passes",
        {"a.py": NON_BOOLEAN},
        ["no failures"],
        ok=True,
    ),
    # --- clean-code, condition 1
    case(
        "a function body over 30 statements fails",
        {"a.py": OVER_THE_STATEMENT_LIMIT},
        ["[clean-code] condition 1", "build holds 31 statements", "the limit is 30"],
    ),
    case(
        "a function body of exactly 30 statements passes",
        {"a.py": AT_THE_STATEMENT_LIMIT},
        ["no failures"],
        ok=True,
    ),
    case(
        "a nested def counts as one statement and is measured on its own",
        {"a.py": BIG_NESTED_DEF},
        ["inner holds 32 statements"],
    ),
    case(
        "the docstring is not counted against the limit",
        {"a.py": DOCSTRING_NOT_COUNTED},
        ["no failures"],
        ok=True,
    ),
    # --- clean-code, condition 2
    case(
        "a statement after a return fails",
        {"a.py": UNREACHABLE},
        ["[clean-code] condition 2", "cannot run", "total"],
    ),
    case(
        "a statement after a raise inside a loop fails",
        {"a.py": UNREACHABLE_AFTER_RAISE},
        ["[clean-code] condition 2"],
    ),
    case(
        "an exit inside a branch does not kill what follows the branch",
        {"a.py": EXIT_INSIDE_A_BRANCH},
        ["no failures"],
        ok=True,
    ),
    case(
        "an exit that ends its own block passes",
        {"a.py": EXIT_AT_THE_END_OF_A_LOOP},
        ["no failures"],
        ok=True,
    ),
    # --- clean-code, condition 3
    case(
        "a comment that parses as an assignment fails",
        {"a.py": COMMENTED_OUT},
        ["[clean-code] condition 3", "rows = normalise(rows)"],
    ),
    case(
        "a comment that parses as a bare call fails",
        {"a.py": COMMENTED_OUT_CALL},
        ["[clean-code] condition 3"],
    ),
    case("prose comments pass", {"a.py": PROSE_COMMENT}, ["no failures"], ok=True),
    case("tool directives pass", {"a.py": TOOL_DIRECTIVE}, ["no failures"], ok=True),
    case(
        "six of sixteen comments are code and the other ten are prose about code",
        {"a.py": SIXTEEN_COMMENTS},
        ["6 failure(s) across 1 file(s)"],
    ),
    # --- value-semantics, condition 1
    case(
        "a callable with five parameters fails",
        {"a.py": FIVE_PARAMETERS},
        ["[value-semantics] condition 1", "connect takes 5 parameters", "the limit is 4"],
    ),
    case("a callable with four parameters passes", {"a.py": FOUR_PARAMETERS}, ["no failures"], ok=True),
    case(
        "the receiver does not count against the parameter limit",
        {"a.py": FOUR_PLUS_RECEIVER},
        ["no failures"],
        ok=True,
    ),
    case(
        "star-args and star-kwargs do not count against the limit",
        {"a.py": VARIADIC},
        ["no failures"],
        ok=True,
    ),
    # --- value-semantics, condition 2
    case(
        "a three-name run shared by three callables fails",
        {"a.py": CLUMP},
        ["[value-semantics] condition 2", "host, port, timeout", "3 callables"],
    ),
    case(
        "the longest shared run is reported, not every sub-run of it",
        {"a.py": LONGER_CLUMP},
        ["host, port, timeout, scheme"],
    ),
    case(
        "a run shared by only two callables passes",
        {"a.py": CLUMP_OF_TWO},
        ["no failures"],
        ok=True,
    ),
    case(
        "a two-name run shared by three callables passes",
        {"a.py": SHORT_RUN},
        ["no failures"],
        ok=True,
    ),
    # --- value-semantics, condition 3
    case(
        "a list field on a frozen dataclass fails",
        {"a.py": FROZEN_WITH_LIST},
        ["[value-semantics] condition 3", "Route.hops"],
    ),
    case(
        "a mutable default factory on a frozen dataclass fails",
        {"a.py": FROZEN_WITH_FACTORY},
        ["[value-semantics] condition 3"],
    ),
    case("a tuple field on a frozen dataclass passes", {"a.py": FROZEN_WITH_TUPLE}, ["no failures"], ok=True),
    case(
        "a dict field on a NamedTuple fails",
        {"a.py": NAMEDTUPLE_WITH_DICT},
        ["[value-semantics] condition 3", "Route.labels"],
    ),
    case(
        "a list field on a type that was never declared immutable passes",
        {"a.py": MUTABLE_DATACLASS},
        ["no failures"],
        ok=True,
    ),
    # --- value-semantics, condition 4
    case(
        "object.__setattr__ in a method of a frozen type fails",
        {"a.py": SETATTR_IN_A_METHOD},
        ["[value-semantics] condition 4", "rename"],
    ),
    case(
        "object.__setattr__ in __post_init__ passes",
        {"a.py": SETATTR_IN_POST_INIT},
        ["no failures"],
        ok=True,
    ),
    # --- value-semantics, condition 5
    case(
        "a class defining __eq__ and no __hash__ fails",
        {"a.py": EQ_WITHOUT_HASH},
        ["[value-semantics] condition 5", "Money defines __eq__"],
    ),
    case("a class defining both passes", {"a.py": EQ_WITH_HASH}, ["no failures"], ok=True),
    case(
        "a class that sets __hash__ to None has said so deliberately",
        {"a.py": EQ_WITH_HASH_DISCLAIMED},
        ["no failures"],
        ok=True,
    ),
    case("a dataclass is not asked for __hash__", {"a.py": EQ_ON_A_DATACLASS}, ["no failures"], ok=True),
    # --- cross-cutting-concerns, condition 1
    case(
        "a loop that catches and sleeps is an inline retry",
        {"a.py": INLINE_RETRY},
        ["[cross-cutting-concerns] condition 1", "fetch"],
    ),
    case(
        "a poll loop that catches nothing passes",
        {"a.py": POLL_WITHOUT_CATCHING},
        ["no failures"],
        ok=True,
    ),
    case(
        "a loop that catches without backing off passes",
        {"a.py": LOOP_WITHOUT_SLEEPING},
        ["no failures"],
        ok=True,
    ),
    # --- cross-cutting-concerns, condition 2
    case(
        "commit and rollback in one body is an inline transaction boundary",
        {"a.py": INLINE_TRANSACTION},
        ["[cross-cutting-concerns] condition 2", "save"],
    ),
    case("a commit with no rollback beside it passes", {"a.py": COMMIT_ONLY}, ["no failures"], ok=True),
    # --- cross-cutting-concerns, condition 3
    case(
        "two clock reads and a subtraction is an inline timer",
        {"a.py": INLINE_TIMER},
        ["[cross-cutting-concerns] condition 3", "handle"],
    ),
    case("a single clock read passes", {"a.py": ONE_CLOCK_READ}, ["no failures"], ok=True),
    case(
        "two clock reads with no duration between them pass",
        {"a.py": TWO_CLOCK_READS_NO_DURATION},
        ["no failures"],
        ok=True,
    ),
    # --- domain-model, condition 1
    case(
        "a domain module importing an adapter fails",
        {"billing/domain/order.py": DOMAIN_IMPORTS_ADAPTER},
        ["[domain-model] condition 1", "billing.adapters.sql"],
    ),
    case(
        "a domain module importing infrastructure relatively fails",
        {"billing/domain/order.py": DOMAIN_IMPORTS_RELATIVE_INFRASTRUCTURE},
        ["[domain-model] condition 1", "infrastructure.cache"],
    ),
    case(
        "a domain module importing a driver fails",
        {"billing/domain/order.py": DOMAIN_IMPORTS_A_DRIVER},
        ["[domain-model] condition 1", "redis"],
    ),
    case(
        "a domain module importing the standard library and its own siblings passes",
        {"billing/domain/order.py": DOMAIN_IMPORTS_THE_DOMAIN},
        ["no failures"],
        ok=True,
    ),
    case(
        "an adapter importing a driver is the adapter doing its job",
        {"billing/adapters/store.py": ADAPTER_IMPORTS_A_DRIVER},
        ["no failures"],
        ok=True,
    ),
    # --- domain-model, condition 2
    case(
        "a vendor token in a domain class name fails",
        {"billing/domain/order.py": VENDOR_IN_A_CLASS_NAME},
        ["[domain-model] condition 2", "SqlOrderGateway", "'sql'"],
    ),
    case(
        "a vendor token in a domain field name fails",
        {"billing/domain/order.py": VENDOR_IN_A_FIELD_NAME},
        ["[domain-model] condition 2", "json_payload"],
    ),
    case(
        "a technique token in a domain function name fails",
        {"billing/domain/order.py": VENDOR_IN_A_FUNCTION_NAME},
        ["[domain-model] condition 2", "build_dto"],
    ),
    case(
        "a vendor token in a module outside the domain passes",
        {"billing/adapters/sql_gateway.py": VENDOR_IN_A_CLASS_NAME},
        ["no failures"],
        ok=True,
    ),
    case(
        "domain names in the domain's own vocabulary pass",
        {"billing/domain/order.py": CLEAN_DOMAIN_NAMES},
        ["no failures"],
        ok=True,
    ),
    case(
        "a domain module file named for a vendor fails",
        {"billing/domain/sql_order.py": CLEAN_DOMAIN_NAMES},
        ["[domain-model] condition 2", "sql_order.py"],
    ),
    # --- duplication, condition 1
    case(
        "three function bodies with the same shape fail",
        {"a.py": THREE_COPIES},
        ["[duplication] condition 1", "adjust repeats a 5-statement body", "settle", "refund"],
    ),
    case(
        "two copies are a coincidence and pass",
        {"a.py": TWO_COPIES},
        ["no failures"],
        ok=True,
    ),
    case(
        "three copies of a four-statement body are under the floor and pass",
        {"a.py": FOUR_STATEMENTS},
        ["no failures"],
        ok=True,
    ),
    case(
        "the same statements wired to different names are three shapes, not one",
        {"a.py": DIFFERENT_WIRING},
        ["no failures"],
        ok=True,
    ),
    case(
        "copies spread across three files are still three copies",
        {"a.py": SETTLE, "b.py": REFUND, "c.py": ADJUST},
        ["[duplication] condition 1", "a.py:2", "b.py:2"],
    ),
    case(
        "copies in one context's domain and adapters are counted together",
        {"billing/domain/order.py": TWO_COPIES, "billing/adapters/store.py": ADJUST},
        ["[duplication] condition 1", "inside the context 'billing'"],
    ),
    case(
        "copies in two bounded contexts are two decisions that agree, and pass",
        {"billing/domain/order.py": TWO_COPIES, "support/domain/ticket.py": ADJUST},
        ["no failures"],
        ok=True,
    ),
    # --- duplication, condition 2
    case(
        "three modules declaring the same table fail, whatever they call it",
        {"a.py": STATUS_TABLE, "b.py": STATUS_TABLE, "c.py": RENAMED_TABLE},
        ["[duplication] condition 2", "ORDER_STATES holds the same 3 entries", "STATUSES"],
    ),
    case(
        "the same table in a call wrapper is the same table",
        {"a.py": WRAPPED_TABLE, "b.py": WRAPPED_TABLE, "c.py": WRAPPED_TABLE},
        ["[duplication] condition 2"],
    ),
    case(
        "two modules declaring the same table pass",
        {"a.py": STATUS_TABLE, "b.py": STATUS_TABLE},
        ["no failures"],
        ok=True,
    ),
    case(
        "a two-entry table repeated three times is under the floor and passes",
        {"a.py": SHORTER_TABLE, "b.py": SHORTER_TABLE, "c.py": SHORTER_TABLE},
        ["no failures"],
        ok=True,
    ),
    case(
        "three tables whose contents differ pass",
        {"a.py": STATUS_TABLE, "b.py": RENAMED_TABLE, "c.py": OTHER_CONTENTS},
        ["no failures"],
        ok=True,
    ),
    case(
        "a table repeated across two bounded contexts passes",
        {
            "billing/domain/order.py": STATUS_TABLE,
            "billing/adapters/store.py": STATUS_TABLE,
            "support/domain/ticket.py": STATUS_TABLE,
        },
        ["no failures"],
        ok=True,
    ),
    # --- debt-markers, condition 1, over a tree
    case(
        "a marker naming no issue fails",
        {"a.py": UNTRACKED_LINE},
        ["[debt-markers] condition 1", "leaves TODO with no issue behind it"],
    ),
    case("a marker naming an issue passes", {"a.py": TRACKED_LINE}, ["no failures"], ok=True),
    case(
        "all four markers are reported and nothing else is",
        {"a.py": FOUR_MARKERS},
        ["4 failure(s) across 1 file(s)", "leaves TBD", "leaves FIXME", "leaves XXX"],
    ),
    case("a quoted marker is prose about markers", {"a.py": QUOTED_MARKER}, ["no failures"], ok=True),
    case(
        "a marker in a string literal is data, not a comment",
        {"a.py": MARKER_IN_A_STRING},
        ["no failures"],
        ok=True,
    ),
    case(
        "a lowercase spelling and a longer word are not markers",
        {"a.py": NEAR_MISSES},
        ["no failures"],
        ok=True,
    ),
    case(
        "an issue number further along the line does not redeem the marker",
        {"a.py": LATE_REFERENCE},
        ["[debt-markers] condition 1", "leaves FIXME"],
    ),
    case("zero is not an issue number", {"a.py": ZERO_ISSUE}, ["[debt-markers] condition 1"]),
    # --- debt-markers, condition 1, scoped to a change
    case(
        "a marker the change did not touch is out of scope",
        {BASELINE: {"a.py": UNTRACKED_LINE}, ARGS: STAGED, "b.py": CLEAN},
        ["2 file(s), no failures"],
        ok=True,
    ),
    case(
        "a marker the change adds is reported",
        {BASELINE: {"a.py": CLEAN}, ARGS: STAGED, "a.py": ADDS_A_MARKER},
        ["[debt-markers] condition 1", "added by this very change"],
    ),
    case(
        "a marker the change rewrites is reported, reference removed",
        {BASELINE: {"a.py": TRACKED_LINE}, ARGS: STAGED, "a.py": UNTRACKED_LINE},
        ["[debt-markers] condition 1", "leaves TODO with no issue behind it"],
    ),
    case(
        "the other nineteen conditions are not scoped to the change",
        {BASELINE: {"a.py": DEEP}, ARGS: STAGED, "b.py": CLEAN},
        ["[kiss] condition 1", "sweep nests control flow 4 deep"],
    ),
    case(
        "--changed with no revision is an error, not a pass",
        {ARGS: ["--changed"], "a.py": UNTRACKED_LINE},
        ["needs a revision or range"],
    ),
    case(
        "--changed outside a repository is an error, not a pass",
        {ARGS: ["--changed", "HEAD", "."], "a.py": UNTRACKED_LINE},
        ["--changed:"],
    ),
    # --- the walk itself
    case(
        # An unimplemented member touches no state, so it is also always its own
        # LCOM4 component. The two findings co-occur by construction and both
        # are reported, because the fixes differ.
        "findings from every condition are reported in one pass",
        {"a.py": DEEP, "b.py": UNIMPLEMENTED},
        [
            "3 failure(s) across 2 file(s)",
            "[kiss] condition 1",
            "[solid] condition 1",
            "[solid] condition 2",
        ],
    ),
    case(
        "a file this interpreter cannot parse is skipped, not failed",
        {"a.py": CLEAN, "broken.py": BROKEN},
        ["1 file(s), no failures (1 skipped)"],
        ok=True,
    ),
    case(
        "generated and vendored trees are not walked",
        {"a.py": CLEAN, "node_modules/pkg/b.py": DEEP, "__pycache__/c.py": DEEP},
        ["1 file(s), no failures"],
        ok=True,
    ),
]


def write(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_IDENTITY, *args], cwd=str(root), capture_output=True, check=True)


def invoke(root: Path, argv: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HOOK), *argv], cwd=str(root), capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr


def run(files: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        baseline = files.get(BASELINE)
        tree = {rel: text for rel, text in files.items() if rel not in (BASELINE, ARGS)}
        if baseline is not None:
            write(root, baseline)
            git(root, "init", "-q")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "the tree before the change")
        write(root, tree)
        if baseline is not None:
            git(root, "add", "-A")
        return invoke(root, list(files.get(ARGS, ["."])))


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    found = []
    if ok and code != 0:
        found.append("expected the hook to pass, it failed")
    if not ok and code == 0:
        found.append("expected the hook to fail, it passed")
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def main() -> int:
    failed = 0
    for name, files, expect, ok in CASES:
        code, output = run(files)
        problems = problems_for(expect, ok, code, output)
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
        print("      --- hook output ---")
        for line in output.splitlines():
            print(f"      {line}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
