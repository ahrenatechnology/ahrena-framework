---
id: <filename-without-md>
type: rule
clade: <plugin-clade>
subclade: <optional>
title: <noun phrase, title case>
statement: <one line, max 160 chars, the only line that reaches the agent>
enforcement: <hook|judgment>
enforced-by: <hooks/<name>.py, only when enforcement is hook>
enforced-in: <tree|forge, optional, only when enforcement is hook; omitted means tree>
references:
  - docs/<rationale-companion>.md
---

# <Title>

## <The condition, stated>

What is never allowed, in the fewest words that are still unambiguous.

State it as a detectable condition, not as a maxim. "A class should do one
thing" cannot be checked. "A module with LCOM4 greater than 1 is a split
candidate" can.

## Conditions

Numbered, each one independently decidable, each one naming what decides it.

1. <condition> — decided by `<hook path>`, or by a reviewer when the rule is judgment.
2. <condition>

## Where this stops

The cases the rule deliberately does not reach, and the point at which
applying it harder makes the code worse. A rule that cannot say where it
stops produces dogma.

<!--
Rationale does not go here. If a paragraph explains why the rule exists,
move it to the doc named in `references` and let the rule point at it.
-->
