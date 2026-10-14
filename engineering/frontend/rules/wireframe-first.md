---
id: wireframe-first
type: rule
clade: engineering
subclade: frontend
title: The wireframe is the first layer
statement: No component is coded before its wireframe is approved as the first layer; code built against an unvalidated design is defective.
enforcement: judgment
references:
  - docs/wireframe-first.md
---

# The wireframe is the first layer

## The design gate

A wireframe for the behaviour being built exists and is approved before any component, state or contract code for that behaviour is written. The wireframe is the first of the four outside-in layers, and it is a gate: the layers below it do not start until it is approved.

The subject is order, not artistry. A wireframe is the cheapest place to find out that the design is wrong — that a field is missing, a flow dead-ends, a state has no screen. Finding it there costs a redraw. Finding it in a finished integration costs the integration. A component coded against a design nobody validated is defective the moment the design turns out to be wrong, and it looks finished until then.

Three terms, used in the same sense throughout. `docs/wireframe-first.md` works each through.

- **A wireframe** is an artifact that fixes the structure, the states and the flow of the behaviour, handed back for approval before code. It is not the visual design and not the production markup.
- **Approved** means the owner of the design accepted the wireframe. An agent does not approve its own wireframe, because the approval is the gate and a self-approval is no gate.
- **Coded** means production component, state or contract code for the behaviour. The red end-to-end skeleton written against the wireframe is not coding the behaviour; it is the test the behaviour will later satisfy.

## Conditions

1. A wireframe for the behaviour exists as an artifact before any production component, state or contract code for it. Decided by a reviewer: the pull-request stack carries the wireframe as its first layer, and a components layer whose stack has no approved wireframe below it is this state.
2. The wireframe was approved by the design's owner, not by the agent that produced it. Decided by a reviewer reading who approved the first layer.
3. The end-to-end skeleton was written red against the wireframe, not against the finished components. Decided by a reviewer: the skeleton's commit precedes the components layer.

## Where this stops

**It is not a visual-design rule.** The wireframe fixes structure, states and flow. Whether the colours, type and spacing are right is the visual layer's concern and the accessibility checks', not this rule's. A wireframe is approved on its structure being correct, not its pixels being final.

**A change with no new behaviour does not need a new wireframe.** A refactor that moves code without changing what the user sees, a dependency bump, a copy fix the owner already signed off — none of these opens a design question, so none needs a wireframe layer. The rule reaches a behaviour being built or changed, not every line that touches the frontend.

**It does not say the wireframe is immutable.** A later layer can surface something the wireframe got wrong. The rule requires that the wireframe be approved before code, not that it never changes; when a layer forces a wireframe change, the wireframe is re-approved and the gate holds again, rather than the code proceeding against the stale design.

**This rule declares judgment rather than a hook, and the reason is not effort.** Whether a wireframe was approved, and by whom, before code began is a fact about people and sequence that no script in this repository can read. It takes the judgment route, its statement is injected, and a reviewer is the gate.
