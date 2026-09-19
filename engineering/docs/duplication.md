---
id: duplication
type: doc
clade: engineering
subclade: quality
title: What a duplicate is, and which one is worth a gate
summary: Three definitions of duplication and why only one of them ships, where the five-statement and three-entry floors came from, the condition measurement removed, and the question a reviewer asks about the duplication no script can see.
references:
  - rules/duplication.md
  - docs/simplicity.md
  - docs/clean-code.md
  - docs/bounded-contexts.md
---

# What a duplicate is, and which one is worth a gate

This is the companion to [`rules/duplication.md`](../rules/duplication.md). The rule states two conditions and names what decides each one; this explains which definition of a duplicate they implement, why the other two were refused, where both numbers came from, and what the detector costs when it is wrong.

[`docs/simplicity.md`](./simplicity.md) closed by saying that DRY is where the next argument would be, that duplication and abstraction are not the same question, and that collapsing them is how "extract the common part" becomes a justification for a base class nobody wanted. [`docs/clean-code.md`](./clean-code.md) said the same thing from the other side: duplication is decided by the rule of three rather than by a size threshold, and no artifact carried it. This is that artifact.

## Three things "a duplicate" can mean

The word covers three different claims, and they are three different rules with three different detectors and three different failure modes. Only one of them is worth a gate.

| Definition | What it finds | What it costs |
|---|---|---|
| **The same tokens** | text that was pasted and not touched | nothing, and it finds almost nothing |
| **The same shape** | text that was pasted and renamed | a detector, and the groups that are alike by accident |
| **The same decision** | one rule of the business written out twice | a reader; no script decides it |

**The same tokens is a strict subset of the same shape, and it decays.** A copy survives as a token-identical copy for about as long as it takes somebody to rename one variable in it, which in practice is the same commit: a body pasted into a new function is pasted because it is wanted for different things, and different things have different names. Shipping the token detector means shipping the shape detector with a clause that throws away most of its findings. There is no version of this where the narrow definition is the safer one; it is the same detector, reporting less.

**The same decision is the definition DRY actually has.** Hunt and Thomas state it as one representation per piece of knowledge, and knowledge is the operative word: two functions with no line in common that both decide when an order may be cancelled are one rule written twice, and the day the rule changes one of them will not. Every expensive duplication story is this one. It is also the one no script decides, because deciding it means deciding that two different programs compute the same thing, and the runnable approximation — a similarity score with a threshold on it — is a detector whose output a reader has to triage. `docs/simplicity.md` records what happens to a detector that is wrong about ordinary code: the KISS rule lost a condition to exactly that, and the lesson was that a gate which fires on correct code gets switched off and then stops enforcing the conditions that were right.

**So the rule ships the middle one, and refuses the other two in opposite directions.** The token definition is refused for being the shape definition with its yield reduced. The decision definition is refused for having no detector, and refused from the rule rather than parked in it, so that the rule can declare a hook and cost nothing to load. That is the same move `rules/clean-code.md` makes when it keeps naming out of its conditions and puts the reviewer's questions here instead; the last section of this document is the equivalent for duplication.

**What "the same shape" means precisely.** Two bodies have one shape when either can be obtained from the other by renaming. The detector walks the body, replaces every declared identifier with a token and every literal with a token typed by its Python type, and compares the results. The renaming is consistent rather than blanket: the first distinct name in a body becomes `n0`, the second `n1`, so `a + b` and `a + a` are two shapes and not one. That single decision is most of the detector's precision, and the rule's test suite pins it with three bodies that have identical statements, identical node types and three different wiring patterns.

This is the type-2 clone of the clone-detection literature. The type-3 clone — a copy with a statement added or removed — is not detected, and the rule's boundary section says what that costs.

## Where the five statements came from

The framework's own Python could not place this threshold, and saying so is the honest start. Over its 8 files, 5,191 lines and 156 functions as this rule landed, the clone detector reports **nothing at any floor from two upward**. That number carries no information about where a floor belongs; it only says the corpus has no duplicated bodies in it, which is a fact about a corpus of two gate scripts and their tests.

So the floor was measured against a control corpus large enough to contain the state: **the CPython 3.11 standard library, 564 files and 288,485 lines, excluding its own test tree**. The detector is the shipped one, run over that tree in 1.5 seconds.

| Floor, in statements | Groups of three or more copies |
|---|---|
| 2 | 116 |
| 3 | 58 |
| 4 | 29 |
| **5** | **13** |
| 6 | 10 |
| 7 | 8 |
| 8 | 7 |

The count alone does not pick a number; it only falls. What picks it is reading the groups each floor adds, and they change in kind between four and five.

**Below five the groups are alike by accident.** The 29 groups that appear at three and vanish at four are five unrelated `__eq__` methods in `uuid`, `datetime` and `traceback`; eight copies of `__subclasshook__`; six accessors returning a flag from `_pyio`, `chunk`, `socket` and `zipfile`. The 16 that appear at four are better and still mixed: `ast.visit_ListComp`, `visit_GeneratorExp` and `visit_SetComp` are a real copy differing only in two delimiters, while `__init__` in `argparse`, `difflib` and `doctest` are three unrelated constructors that collide because each assigns four parameters to four fields. Three statements is a shape the language reaches on its own; four is nearly so.

**At five and above every group in that corpus is a genuine repetition.** All thirteen are listed in the next section. There is nothing in them that is merely similar.

So five is the bottom of the clean span, and the bottom is the right end of it. This is the placement method `docs/clean-code.md` used for its statement count and `rules/progressive-disclosure.md` used for its ten-line cap, with the direction reversed: the statement cap is a maximum, so it sits at the bottom of the gap to stay strict, while this floor is a minimum, so the bottom of the clean span is the strictest placement that still fires on nothing accidental. Taking six instead would buy a margin the measurement does not ask for and would drop three true findings, including the `setnchannels` body copied verbatim across `aifc`, `sunau` and `wave`.

## Where the three entries came from

The table floor was placed the same way and needed less work, because the noise is concentrated at the very bottom.

| Floor, in entries | Groups of three or more copies |
|---|---|
| none | 7 |
| 1 | 4 |
| 2 | 2 |
| **3** | **2** |
| 4 | 2 |
| 5 | 2 |

With no floor the detector reports `{}` in 52 modules, `[]` in 21, `()` in 3, `['Popen']` in 4 and `[0]` in 3. Five of the seven groups are empty or one-element containers and none of them is a finding anybody wants. Two entries removes all five, and three through five report the same two, so the floor sits inside a wide clean span rather than on an edge.

Three rather than two, because three is already this plugin's number for "values that travel together": Fowler's Data Clumps, taken by condition 2 of `rules/value-semantics.md` for the parameter run. The measurement gives no reason to prefer two and the corpus gives a reason to prefer the number already in use.

## The condition that measurement removed

`rules/duplication.md` was drafted with a third condition, and it was the one that came closest to catching the definition the rule had to refuse.

**The third occurrence of the same predicate.** A business rule written as a condition — `order.total > LIMIT and order.status == OPEN` — appearing in three places is a decision expressed three times, and unlike a whole body it is the shape a policy actually takes in code. The detector was the exact expression, names and literals kept rather than renamed, on the argument that a predicate over domain objects is written with the domain's names and so does not drift the way a body does.

Run over the same 288,485 lines with a floor of twelve AST nodes it produced 60 groups, and roughly half of them were correct code. `isinstance(filename, (str, bytes, os.PathLike))` in `bz2`, `gzip` and `lzma` is the standard argument check. `not isinstance(data, (bytes, bytearray, memoryview))` appears six times across `asyncio` and is a type guard. Excluding type guards by name left 23 groups and the ratio barely moved: `context is not None and keyfile is not None` across `ftplib`, `poplib` and `smtplib` is a genuine copied validation, and `on == 1 and sn == 0` in `_pydecimal` is arithmetic inside one algorithm.

The mistake was the same one `docs/simplicity.md` records for the deleted indirection condition: the detector was matching a shape that correlates with the defect rather than the defect. A repeated predicate is duplication when the predicate is a policy and idiom when it is a guard, and telling those apart needs to know what the expression is about. One in two is not a rate this plugin ships — `docs/clean-code.md` sets the standard at one true positive and zero false positives over 2,291 lines — so the condition was removed rather than tuned, and it is recorded here so the next person to think of it has the numbers.

## What the detectors cost, measured

Over the 288,485-line control corpus the two shipped conditions produce **15 findings**: 13 from condition 1 and 2 from condition 2. Over the framework's own 5,191 lines they produce none.

The thirteen bodies, in the order the hook reports them:

| Group | Statements | Copies |
|---|---|---|
| `throw`, `athrow`, `throw` in `_collections_abc` | 7 | 3 |
| `add`, `divide`, `divmod`, `multiply`, `subtract` and two more in `_pydecimal` | 5 | 7 |
| `sock_recv`, `sock_recv_into`, `sock_recvfrom` in `asyncio` | 12 | 3 |
| `_sock_recv`, `_sock_recv_into`, `_sock_recvfrom` in `asyncio` | 8 | 3 |
| `finish_recv` and `finish_send` in `asyncio.windows_events` | 5 | 5 |
| `_get_build_version` in `ctypes.util` and `get_build_version` in two `distutils` compilers | 15 | 3 |
| `find_library_file` in three `distutils` compilers | 9 | 3 |
| `get_atext`, `get_ttext`, `get_attrtext`, `get_extended_attrtext` in `email` | 8 | 4 |
| `get_token`, `get_attribute`, `get_extended_attribute` in `email` | 12 | 3 |
| `is_dir`, `is_file`, `is_symlink` and four siblings in `pathlib` | 6 | 7 |
| `setnchannels` and `setnframes` across `aifc`, `sunau`, `wave` | 5 | 3 |
| `open` across `aifc`, `sunau`, `wave` | 9 | 3 |
| `unpack_uint`, `unpack_int`, `unpack_float`, `unpack_double` in `xdrlib` | 6 | 4 |

The two tables are the weekday and month name lists, each written out three times: `_weekdayname` in `wsgiref.handlers`, `DAYS` in `http.cookiejar` and `_weekdayname` in `http.cookies`; and `_monthname` in `wsgiref.handlers`, `_MONTHNAMES` in `datetime` and `_monthname` in `http.cookies`. Three copies of the same vocabulary under three names, which is the state condition 2 describes and the reason the name is not compared.

**The false-positive rate, stated so it can be disagreed with.** Every one of the fifteen is a real repetition: none of them is code that merely resembles other code. By that reading the rate over 288,485 lines is zero, and that is the number the floor was chosen to produce.

By a stricter reading — a false positive is a finding whose fix a maintainer would decline — the rate is **2 in 13**. `throw` and `athrow` have one shape because a generator and an async generator do the same thing, and they cannot have one body. `pathlib`'s seven `is_*` methods differ only in the predicate each hands to the same `try`/`except`, and collapsing them trades seven names a reader recognises for one parameterised call. Both are named in the rule's boundary section, because a carve-out stated before it is encountered is a rule working and a carve-out discovered afterwards is a rule losing an argument.

That second rate is the one to plan against, and it is the rate this rule accepts: roughly one finding in six is a question whose answer is "no, and here is why", recorded once as a path exclusion. It is higher than the zero that `docs/clean-code.md` reports for its three conditions, and it is the price of a condition whose subject is judgment-adjacent at all. What makes it payable is that the refusals are stable — a sync/async pair and a family of stat calls do not change next week — and that the finding costs a sentence rather than a redesign.

## Why the count stops at the context boundary

Both conditions count copies inside one bounded context and never across two. This is the only part of the rule that is not about detection, and it is the part that keeps the rule from doing damage.

`docs/bounded-contexts.md` sets out why a context is a directory and what the layout buys. The relevant half here is what a context is for: inside one, a word means one thing; across two, the same word is two concepts that happen to share spelling. "Customer" in billing and "customer" in support is the standard example, and the whole value of the idea is refusing to merge them.

Duplication is how that refusal gets overturned. Two contexts independently grow a six-statement body that computes the same thing today, a detector reports three copies, somebody extracts them into a shared module, and the two contexts now have one implementation of a rule they each own separately. The next divergence — and there is always one, because the contexts were separated for a reason — arrives as a breaking change to both, and the usual repair is a flag argument, which is condition 2 of `rules/kiss.md` and condition 4 of `rules/yagni.md` arriving together.

So the count is scoped rather than the finding being carved out afterwards. Three copies in `billing/` are three copies; two in `billing/` and one in `support/` are a coincidence the detector never sees. A tree with no layer directories at all is one context, which is the right default: a codebase that has not drawn a boundary has not claimed that two of its parts mean different things.

The cost is the same one `rules/domain-model.md` pays for choosing a layout over a configuration, and it is the same trade: a project laid out differently gets one context and a slightly noisier count, rather than a configurable map that drifts from the tree and is wrong invisibly.

## What a reviewer asks instead

The rule catches copies. The duplication that costs most has no shape in common, and naming what to ask about it is more useful than pretending a script will get there.

**Where is this decided, and how many places could answer?** Take one rule the business would recognise — when an order may be cancelled, how a fee is rounded, which statuses are terminal — and find every place the code could answer it. One place is correct. Two places is the defect, and it is the defect whether or not the two look alike.

**Which copy is authoritative?** When there are two, one of them is usually a convenience: a validation repeated at the edge for a better error message, a constant inlined in a migration, a projection that recomputes rather than reads. That is not always wrong, and it is only survivable when the code says which one is the source. A duplication with a named authority is a cache; one without is two sources of truth.

**Would the change have to be made twice?** This is the question that separates duplication from resemblance, and it is worth asking in the opposite direction too. Two functions that look identical and would change for different reasons are not duplication, and collapsing them couples two things that have no reason to move together. `docs/simplicity.md` makes the same point about the abstraction trigger: the cost of the wrong collapse is paid continuously by every reader who has to work out which side of the seam their change belongs on.

**And what does the copy cost right now?** Three copies of a body that has not changed in two years cost nothing, and the fix costs a review. The rule of three says when a repetition has become a pattern; it does not say the pattern is urgent.

## Where this stops

**This document does not teach DRY.** Hunt and Thomas's *The Pragmatic Programmer* states the principle and Fowler's *Refactoring* supplies the rule of three and the Data Clumps figure; neither is reproduced. What is here is the part this framework will hold a reviewer to and the measurements behind it.

**The choice of the function body as the unit is argued, not measured.** Extending condition 1 to arbitrary statement windows inside bodies would find the block pasted into three longer functions, which is real duplication the rule misses. It was not built, and the reason given in the rule's boundary section — that the fix for a duplicated window is a new function rather than a call to an existing one, so the detector would be proposing the gated move on every match — is reasoning rather than a count. `docs/patterns.md` marks its own cost claims the same way, and the honest position is that a reader who disagrees has a specific claim to disagree with.

**It says nothing about duplication outside code.** The same constant in a configuration file and a migration, the same enum in a schema and a type, the same copy in a template and a translation file are all one representation split in two, and none of them is reachable by a parser that reads Python. The condition that would catch them is a scanner the consuming project runs over its own artifacts, which is the position `rules/contract-first.md` takes about its own detectors.

**It carries no worked examples outside Python.** The two conditions are stated in language-neutral terms and the one shipped detector parses Python, because the Python standard library contains a Python parser and nothing else. The shape comparison is the most portable material in this plugin — every language with a parser has a normalised dump — and a detector for another language belongs with the plugin for it.

**The control corpus is one corpus.** 288,485 lines of the standard library is large, old, written by many hands and unusually well reviewed, which makes it a good place to look for coincidental similarity and a poor place to look for the copy-paste a team under deadline produces. The floors are placed where coincidence stops in that tree. A run over a large application would be worth more than another argument, and it has not been done.
