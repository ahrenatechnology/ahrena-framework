---
id: external-calls
type: rule
clade: engineering
subclade: architecture
title: Ports and adapters only where there is an external call
statement: An external call lives in an adapter behind a consumer-declared port; internal code gets no port, and a port with one adapter and no test double is deleted.
enforcement: judgment
references:
  - docs/external-calls.md
---

# Ports and adapters only where there is an external call

Five conditions: ADP-1 to ADP-4 of the PR quality rubric (#323), and a fifth that states the boundary of the four. `docs/external-calls.md` explains why an external call is the case where a seam pays for itself and where an internal one does not.

An external call is a call that leaves the process or the project's own memory: an HTTP request, a vendor SDK, a database, the file system, a child process, a queue. A port is the type the consumer declares for what it needs; an adapter is the module that implements it by making the call.

**These conditions add structure, so they are gated by the abstraction trigger** in condition 1 of `rules/yagni.md`: an abstraction is justified by a second real consumer in the tree, or by a test that exists today requiring the seam. An external call meets the second branch by its nature, because the test that exercises the use case cannot call the vendor and so needs a double behind a seam. That is the argument; it holds for an external call and for nothing else, which is why condition 4 deletes a port that shows neither branch. The pattern selection in `rules/pattern-selection.md` applies as written: no pattern is chosen for the call before the trigger is met.

## Conditions

1. **ADP-1. An external call is made only in an adapter module.** The threshold is 0 calls outside, on new and changed lines. The adapter modules are those the project's layer map names; a call is a use of an HTTP client, a vendor SDK, a database driver, the file-system API, a process-spawn API or a queue client. Decided by a static search for those imports outside the adapter paths, and by a reviewer for the layer a search cannot place.

2. **ADP-2. A use case imports the port, never the concrete adapter; only the composition root binds the two.** The threshold is 0 imports of a concrete adapter from a domain or use-case module. The port is declared on the consumer's side, in the domain or use-case module that needs it, so the dependency points inward as `rules/solid.md` condition 6 requires. Decided by the import-graph check the project runs for layer direction, and by a reviewer where none exists.

3. **ADP-3. An adapter translates the vendor's error into the domain's error; no vendor type or error crosses the port.** The threshold is 0 vendor types in a port signature and 0 vendor errors thrown or returned through it. The translation lands in the `Result` of `rules/result-errors.md`, with the vendor's error kept for the span and never for the caller. Decided by a reviewer reading each port's signature and each adapter's error path.

4. **ADP-4. A port with no second adapter and no test double does not exist.** The threshold is 0 orphan ports. A port is justified by an adapter plus a double used in a test that exists today, or by two adapters; one adapter and no double is the single-implementation interface that condition 1 of `rules/yagni.md` inlines. Decided by a count, per port, of adapters plus doubles in the tree, which a script the project owns can make once it knows the port's naming.

5. **Internal code gets no port.** A call from one module of the project to another, within one deployment unit, is made directly. Decided by a reviewer, and by condition 1 of `rules/yagni.md`.

## Where this stops

**ADP-1 does not reach the adapter's own tests or the composition root.** A test of an adapter calls the vendor by design, and the root constructs both sides by design. Exclude both by path.

**ADP-1 does not make a pure library call an external call.** A date library, a hashing function, a parser and a collection type run in the process and have no failure the caller can act on. The line is the call that can be slow, absent or different tomorrow.

**ADP-2 does not require a framework container.** The composition root may be a function that passes arguments; the condition is which side declares the type and which module imports which, not the mechanism that wires them.

**ADP-3 does not forbid the vendor's detail from being recorded.** The adapter attaches it to the span and the log record so the diagnosis keeps it. It forbids the detail crossing the port, where a caller would start to match on it.

**ADP-4 does not delete a port that has a real adapter and a double.** An in-memory adapter used as the test double counts as the double, so a port with it and one real adapter stays; a second real adapter satisfies the first branch of the trigger. An anticipated second adapter does not.

**Condition 5 does not forbid a seam an internal call genuinely needs.** A second real consumer in the tree, or a test that requires the seam, still justifies one; condition 5 says an internal call earns no port by being "clean". Nor does it reach a boundary between deployment units, which is an external call from the caller's side.

**These conditions are judgment, and the detectors are tracked in the detectors sub-issue of #323.** The layer map and the adapter paths are the project's, so no script ships in this plugin.
