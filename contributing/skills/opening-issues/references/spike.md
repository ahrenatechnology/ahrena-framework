# Spike

A question that must be answered before the work that depends on it can be planned or built. Timeboxed, and it produces a decision, not a feature. Native type: `Spike` if the organisation has it, otherwise `Task`.

Title: the question. "Can the ledger take 5,000 writes a second on the current schema?"

```markdown
## Question

The one question this answers. If there are two, it is two spikes.

## Why it blocks

What cannot be planned, estimated or built until this is answered, each by
number. Those items are blocked by this spike.

## Timebox

The most time this is worth, and what happens if it runs out: the
decision is taken on what is known by then.

## Acceptance criteria

- AC-1: The question is answered, with the evidence that answers it: the measurement, the prototype's result, the documentation read. (checked by review)
- AC-2: The decision is recorded, as a decision record when it will be questioned later, or as a comment here when it will not. (checked by review)
- AC-3: The items it blocked are updated, or new ones opened, to match the answer. (checked by review)

## Left to other issues

- <the work this spike informs but does not do, each by number>
```

A spike's code is thrown away or rewritten under its own issue. Nothing it produces lands on trunk as a feature, so its criteria are all judged by a reader.
