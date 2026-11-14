---
id: well-architected
type: doc
clade: engineering
subclade: aws
title: The Well-Architected Framework, as this Plugin Uses It
summary: The six pillars and their design principles as AWS publishes them today, the best practices this plugin's rules and review conditions trace to by identifier, how a design or a review walks the pillars, and what the predecessor's summary carried that AWS's text does not.
references:
  - rules/least-privilege.md
  - rules/data-protection.md
  - rules/cost-ownership.md
  - docs/identity-and-access.md
  - docs/cost.md
---

# The Well-Architected Framework, as this Plugin Uses It

The AWS Well-Architected Framework is the vendor's own statement of what a sound workload on AWS looks like. This plugin uses it in two ways: its rules and review conditions trace to its best practices by identifier, and a design or a review walks its pillars so that none is skipped. The framework text read for this document carries the publication date November 6, 2024, which is also the newest entry on its [revisions page](https://docs.aws.amazon.com/wellarchitected/latest/framework/document-revisions.html); every quotation below was read on 2026-11-14.

## The six pillars and their design principles

The framework has "six pillars of operational excellence, security, reliability, performance efficiency, cost optimization, and sustainability" ([The pillars of the framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html)). The design principles, verbatim from each pillar's page:

| Pillar | Design principles |
|---|---|
| [Operational excellence](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) | Organize teams around business outcomes; Implement observability for actionable insights; Safely automate where possible; Make frequent, small, reversible changes; Refine operations procedures frequently; Anticipate failure; Learn from all operational events and metrics; Use managed services |
| [Security](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) | Implement a strong identity foundation; Maintain traceability; Apply security at all layers; Automate security best practices; Protect data in transit and at rest; Keep people away from data; Prepare for security events |
| [Reliability](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) | Automatically recover from failure; Test recovery procedures; Scale horizontally to increase aggregate workload availability; Stop guessing capacity; Manage change through automation |
| [Performance efficiency](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf-dp.html) | Democratize advanced technologies; Go global in minutes; Use serverless architectures; Experiment more often; Consider mechanical sympathy |
| [Cost optimization](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) | Implement Cloud Financial Management; Adopt a consumption model; Measure overall efficiency; Stop spending money on undifferentiated heavy lifting; Analyze and attribute expenditure |
| [Sustainability](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus-design-principles.html) | Understand your impact; Establish sustainability goals; Maximize utilization; Anticipate and adopt new, more efficient hardware and software offerings; Use managed services; Reduce the downstream impact of your cloud workloads |

"Use managed services" appears in two pillars and "Stop spending money on undifferentiated heavy lifting" in a third. That is the premise [`docs/services.md`](services.md) argues its recommendations from: where AWS runs the component, the workload does not carry its operation.

## The best practices this plugin traces to

A rule or a review condition here names the best practice it comes from. These are the ones in use, with the question each sits under.

| Best practice | Question | Where this plugin holds it |
|---|---|---|
| SEC02-BP02 Use temporary credentials | [SEC 2](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-02.html) How do you manage authentication for people and machines? | [`rules/least-privilege.md`](../rules/least-privilege.md) conditions 3 and 4 |
| SEC02-BP03 Store and use secrets securely | SEC 2 | [`rules/data-protection.md`](../rules/data-protection.md) condition 4 |
| SEC03-BP02 [Grant least privilege access](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_least_privileges.html) | [SEC 3](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-03.html) How do you manage permissions for people and machines? | `rules/least-privilege.md` conditions 1 and 2 |
| SEC03-BP07 Analyze public and cross-account access | SEC 3 | `rules/least-privilege.md` conditions 5 and 6 |
| SEC08-BP02 [Enforce encryption at rest](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_data_rest_encrypt.html) | [SEC 8](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-08.html) How do you protect your data at rest? | `rules/data-protection.md` condition 1 |
| SEC09-BP02 [Enforce encryption in transit](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_data_transit_encrypt.html) | [SEC 9](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-09.html) How do you protect your data in transit? | `rules/data-protection.md` conditions 2 and 3 |
| COST02-BP05 [Implement cost controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost_govern_usage_controls.html) | [COST 2](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-02.html) How do you govern usage? | [`rules/cost-ownership.md`](../rules/cost-ownership.md) condition 3 |
| COST03-BP02 [Add organization information to cost and usage](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost_monitor_usage_org_information.html) | [COST 3](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-03.html) How do you monitor your cost and usage? | `rules/cost-ownership.md` conditions 1 and 2 |
| COST04 decommissioning | [COST 4](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-04.html) How do you decommission resources? | review condition `CST-3` (log retention) |
| REL09 backups | [REL 9](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-09.html) How do you back up data? | review condition `REL-2` |
| REL10-BP01 [Deploy the workload to multiple locations](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html) | [REL 10](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-10.html) How do you use fault isolation to protect your workload? | review condition `REL-1` |
| OPS08 observability | [OPS 8](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops-08.html) How do you utilize workload observability in your organization? | the design's observability section; `ahrena-engineering-observability:reviewing-observability` holds the code |

The security pillar's "Protect data in transit and at rest" and "Implement a strong identity foundation" are rules here, not review suggestions, because a breach of either is a defect with no trade-off on the other side. Reliability, performance and sustainability stay review conditions and design questions: whether a workload needs two Availability Zones is a decision about what an outage costs, which only the project can price.

## How a design or a review walks the pillars

[`skills/designing-on-aws`](../skills/designing-on-aws/SKILL.md) ends with one pass over the six pillars: for each, the decision the design made and the trade-off it accepted, in a sentence. A pillar with nothing to say is written as "nothing at this scale" with the reason, not left out, so that a reader can tell a considered pillar from a forgotten one. [`skills/reviewing-aws`](../skills/reviewing-aws/SKILL.md) groups its conditions by the same pillars.

## The tool and the lenses

AWS provides the Well-Architected Tool, "a service for reviewing your workloads at no charge" ([framework welcome page](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)). Lenses "consistently measure your architectures against best practices", each with "its own set of questions, best practices, notes, and improvement plan"; the catalog includes Serverless Applications, SaaS, Financial Services Industry, Container Build, DevOps, Generative AI and Machine Learning among others ([Using lenses](https://docs.aws.amazon.com/wellarchitected/latest/userguide/lenses.html), [Lens Catalog](https://docs.aws.amazon.com/wellarchitected/latest/userguide/lens-catalog.html)). A formal review of a running workload is done in the tool by the workload's owner; this plugin's review reads a change and does not replace it.

## What the predecessor carried and this does not

The predecessor's summary of the framework (`codex-aws-well-architected`) is merged here, with three departures.

- **Its design principles were paraphrased and partly out of date** — five for operational excellence where AWS now lists eight, and wording that is not AWS's. This document quotes the current list.
- **Its RTO and RPO table by tier** ("Tier 1 ... <1h ... <5min") had no source; no page of the framework read here states those figures. Recovery objectives are the project's to set, and REL 9 and REL 10 are where the design records them.
- **Its figures for Graviton** ("up to 40% better cost-performance", "~40% more energy efficient") had no source and are not repeated. A design that chooses an architecture for its price-performance cites the AWS page it relied on, for the instance family, on the day.

## Where this stops

This document indexes the framework; it is not a substitute for it. The full best-practice text, implementation guidance and risk levels are on AWS's pages, and a reader who needs them follows the link. Industry lenses that apply to a particular client are that client's to adopt.
