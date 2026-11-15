---
id: log-through-observer
type: doc
clade: engineering
subclade: architecture
title: Why logging belongs to an observer at the edge
summary: What an explicit log call in the domain costs, how an event and an observer replace it, and where the zero threshold came from.
references:
  - rules/log-through-observer.md
  - rules/cross-cutting-concerns.md
  - docs/cross-cutting-concerns.md
---

# Why logging belongs to an observer at the edge

This is the companion to [`rules/log-through-observer.md`](../rules/log-through-observer.md). The decision of 14 November 2026 is no explicit log in the domain, only through an observer.

## What an inline log call costs

A `logger.info("order " + id + " rejected for " + email)` in a use case does four things nobody chose together. It fixes a severity, it interpolates a string where the telemetry standard wants attributes, it carries a personal datum into the log, and it ties the domain to a logging library. Redacting the email now means finding every such call. With an observer, the domain returns an event named `order.rejected` with the order id, and one function turns it into a record, redacts the attributes, sets the severity and adds the resource and trace attributes the log rules require.

This is the argument of [`docs/cross-cutting-concerns.md`](cross-cutting-concerns.md) for retries and metrics, applied to the one concern it does not list: it is declared once at a boundary, and an inline copy is the defect.

## Where the zero came from

The threshold is declared maintainer policy (#34). No measured figure backs it, and none could: the claim is that zero is the only count with a detector that carries no judgment, since a threshold of two calls per use case is an argument about which two. On a new line the count is 0; the total on legacy code is a ratchet that must not rise.

## Where this stops

This document does not choose the event bus, and it does not say what the observer exports to; the observability plugin's rules on records and on the SDK cover that.
