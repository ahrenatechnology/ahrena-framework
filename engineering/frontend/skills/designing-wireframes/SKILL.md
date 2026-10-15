---
name: designing-wireframes
description: Use at the first layer of a frontend feature, before any component is coded. Produces the wireframe as an artifact that fixes the structure, states and flow, hands it back to the design's owner for approval, and writes the end-to-end skeleton red against it — the design gate the rest of the build stacks on.
type: skill
clade: engineering
subclade: frontend
references:
  - rules/wireframe-first.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
---

# Designing wireframes

This is the Designer's procedure, and it is the first layer of an outside-in build. It produces the wireframe, gets it approved, and writes the failing end-to-end test against it, before any component, state or contract code exists. [`rules/wireframe-first.md`](../../rules/wireframe-first.md) is the gate this procedure opens.

## 1. Read the component map first

Run [`ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`](../../../fundamentals/skills/reading-the-component-map/SKILL.md) before drawing anything. Take the frontend component's vocabulary, its sanctioned screens and folders, and its `e2e` testing lane. The wireframe is named in the project's words, and the end-to-end runner is the project's, not this clade's default.

## 2. Draw the structure, the states and the flow

Produce the wireframe as an artifact. It fixes three things and no more: the structure of each screen, every state each screen can be in — empty, loading, error, populated — and the flow between them for the behaviour being built. It is not the visual design and not production markup.

The recurring failure is skipping the off-happy-path states. A wireframe that shows only the populated screen hides exactly the design questions that are expensive to discover later: what the empty state says, what the error offers, what loading looks like. Draw every state the behaviour scenario can reach.

## 3. Hand it back for approval

Hand the wireframe to the design's owner and wait for approval. Do not approve your own wireframe: the approval is the gate, and an agent signing off its own design removes the gate while appearing to pass it. Record who approved it, because the layer above is held to having an approved wireframe below it.

## 4. Write the end-to-end skeleton red against the wireframe

Write the Playwright end-to-end skeleton — or the runner the project's `e2e` lane names — against the approved wireframe, and confirm it fails. It describes the finished behaviour in terms of the wireframe's screens and flow, so that every later layer is driving a failing test toward green rather than inventing its own target.

The skeleton is red on purpose and stays red until the contract layer. A skeleton that passes now is a skeleton testing the wireframe's placeholders, not the behaviour; it must assert the behaviour the feature will have, which nothing yet implements.

## 5. Open the first layer

The approved wireframe and the red skeleton are the first pull request in the stack. The components layer is based on it, and the build proceeds inward from here.

## When this skill does not apply

**A change with no new behaviour.** A refactor, a dependency bump or a signed-off copy fix opens no design question and needs no wireframe layer. This procedure is for a behaviour being built or changed.

**The visual design.** This fixes structure, states and flow. Colour, type, spacing and motion are the visual layer's, and contrast and focus order are the accessibility checks'. A wireframe is approved on being structurally right, not visually final.

**Approving the wireframe.** The Designer produces and hands back; the owner approves. This skill never supplies the approval it waits for.

<!--
Directory layout:

skills/designing-wireframes/
└── SKILL.md

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
