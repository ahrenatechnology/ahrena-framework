---
id: wireframe-first
type: doc
clade: engineering
subclade: frontend
title: Why the wireframe comes first
summary: Why a frontend feature is built outside-in with the wireframe as an approved design gate, what the gate prevents, and the cases that look like they need a wireframe and do not.
references:
  - rules/wireframe-first.md
---

# Why the wireframe comes first

This is the companion to [`rules/wireframe-first.md`](../rules/wireframe-first.md). The rule states that no component is coded before its wireframe is approved as the first layer; this explains why that order is the cheap one, what a wireframe is and is not, and where the gate deliberately does not reach.

## Outside-in, and why the wireframe is the outer edge

A frontend feature is built in four layers that nest from the outside in: the wireframe fixes what the user sees and how they move through it; the components fill that structure; the state drives the components; the contract feeds the state. Each layer constrains the one inside it. The components exist to realise the wireframe, the state exists to make the components behave, the contract exists to supply the state.

Building from the outside in means validating each layer before starting the one it constrains. The alternative — building the contract first and discovering at the screen that it answers the wrong question — is the expensive order, because the mistake is found after everything downstream of it has been built on top.

The wireframe is the outermost edge, so it is validated first. It is also the cheapest artifact in the stack: a structure, its states and its flow, with nothing yet implemented. A design error caught against a wireframe costs a redraw. The same error caught against a finished integration costs the integration, every test written against it, and the review time already spent.

## The gate, and why an agent does not open it alone

Approval is what makes the wireframe a gate rather than a step. The design's owner — the person who is accountable for what the feature does and how it behaves — accepts the wireframe before any code is written against it. An agent producing the wireframe and then approving its own wireframe has removed the gate while appearing to pass it, which is worse than no gate, because the stack now carries a signed-off first layer that nobody with authority signed.

This is why the first layer is delegated to a Designer and handed back, not produced and consumed inside one step. The hand-back is the gate.

## Behaviour leads the wireframe

The wireframe is not the first thing that exists; the behaviour is. The scenario the feature must satisfy is written first, and the wireframe is drawn to serve it. The end-to-end test is then written red against the wireframe, so that from the first layer onward there is a failing test describing the finished behaviour, and every later layer is driving it toward green rather than inventing its own target.

A red skeleton written against the wireframe is not coding the behaviour. It is the executable statement of what the behaviour will be, and the rule's third condition keeps it ahead of the components so that the components are built to pass a test, not have a test retrofitted to them.

## What the gate prevents

Three failures, each of which looks like ordinary progress until the design turns out to be wrong.

A component built against an unvalidated design is defective work that passes its own tests, because its tests encode the same wrong assumption the component does. A state layer wired to components that realise the wrong flow is correct against the wrong thing. A contract shaped to feed a state the user never needed is a backend commitment made for a frontend that will change. In each case the work is internally consistent and externally wrong, and the wireframe is where that gap is cheapest to close.

## Where this stops

**It is not a method for visual design.** This doc argues for validating structure, states and flow before code. How the validated structure is then made to look — colour, type, spacing, motion — is the visual layer's subject, and the accessibility checks are where contrast and focus order are judged. A wireframe is approved on being structurally right, not visually final.

**It does not cover changes with no new behaviour.** A refactor, a dependency bump or a signed-off copy fix opens no design question. The rule and this doc reach a behaviour being built or changed; they say nothing about frontend lines that change nothing a user experiences.

**It does not make the wireframe immutable.** A later layer can prove the wireframe wrong. The point is that the design is validated before code, not that validation happens once. When a layer forces a change, the wireframe is re-approved and the gate holds again.

**It does not name the tools.** Which wireframing tool, which end-to-end runner, which component workbench a project uses is the project's, stated in its component map. This doc argues the order; the project supplies the vocabulary.
