---
id: networking
type: doc
clade: engineering
subclade: gcp
title: Networking on Google Cloud
summary: The network a Google Cloud product starts from (custom-mode VPC, no default network, private paths to Google APIs and managed services, a load balancer as the only public door), the vendor page behind each choice, and the findings that report when it drifts.
references:
  - docs/identity-and-access.md
  - docs/services.md
---

# Networking on Google Cloud

What a request can reach is decided before IAM is asked. This document sets out the network shape this plugin designs to and reviews against, and cites the Google Cloud page behind each choice. Pages were read on 2026-11-14 under `docs.cloud.google.com`.

## No default network

Every new project gets a network called `default` unless an organization policy prevents it. It is an auto-mode VPC with a subnet in every region, and its pre-populated firewall rules allow SSH (TCP 22) and RDP (TCP 3389) from any address ([VPC networks](https://docs.cloud.google.com/vpc/docs/vpc); [VPC firewall rules](https://docs.cloud.google.com/vpc/docs/firewalls)). Google recommends custom-mode networks for production and deleting the default network when it is not used ([VPC networks](https://docs.cloud.google.com/vpc/docs/vpc); [Best practices for VPC design](https://docs.cloud.google.com/architecture/best-practices-vpc-design)). `compute.skipDefaultNetworkCreation` stops it being created ([Organization policy constraints](https://docs.cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints)); Security Command Center reports one that exists as `DEFAULT_NETWORK` ([Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings)).

## One network, shared by environment

Google's landing-zone guidance recommends, for most uses, one Shared VPC per environment: a host project owns the network and service projects attach to it; it advises against peering environments with each other ([Decide the network design](https://docs.cloud.google.com/architecture/landing-zones/decide-network-design)). Network administration then sits with one team, and the Network User role is granted on the subnet a service project uses, not on the whole host ([Best practices for VPC design](https://docs.cloud.google.com/architecture/best-practices-vpc-design)). A hub-and-spoke design with network appliances is the option for layer-7 inspection (same landing-zone page).

How many environments, and which projects attach to which network, are a client's decisions, made in its installation.

## Firewalls

Ingress is denied unless a rule allows it, egress is allowed unless a rule denies it, rules are stateful, and the lower priority number wins ([VPC firewall rules](https://docs.cloud.google.com/vpc/docs/firewalls)). Hierarchical firewall policies attach to the organization or a folder and cover many networks in one or more projects at once ([Firewall policies overview](https://docs.cloud.google.com/firewall/docs/firewall-policies-overview)). Google's VPC guidance asks for fewer, broader rule sets, and for isolating VMs by service account where possible ([Best practices for VPC design](https://docs.cloud.google.com/architecture/best-practices-vpc-design)).

The findings that report an open door are `OPEN_FIREWALL`, `OPEN_SSH_PORT`, `OPEN_RDP_PORT`, `PUBLIC_IP_ADDRESS`, `FLOW_LOGS_DISABLED` and `FIREWALL_RULE_LOGGING_DISABLED` ([Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings)). `compute.vmExternalIpAccess` with an empty allowlist denies every VM an external address, which is what the enterprise foundations blueprint sets ([Preventative controls](https://docs.cloud.google.com/architecture/blueprints/security-foundations/preventative-controls)).

## Administrative access without a public port

IAP TCP forwarding reaches SSH or RDP on a VM with no external address: the firewall allows only Google's IAP range, and the user needs `roles/iap.tunnelResourceAccessor` on the instance ([Using IAP for TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding)). The same page notes the default network's SSH and RDP rules allow every address, and suggests disabling them.

## Private paths to Google and to managed services

- **Private Google Access** lets a VM with only an internal address reach Google APIs; it is set per subnet ([Private Google Access](https://docs.cloud.google.com/vpc/docs/private-google-access)).
- **Private Service Connect** puts an internal address in the consumer's VPC for a Google API bundle or a producer's service ([Private Service Connect](https://docs.cloud.google.com/vpc/docs/private-service-connect)).
- **Private services access** connects a managed service's network, such as Cloud SQL's private IP, through VPC Network Peering from an allocated range; peering is not transitive ([Private services access](https://docs.cloud.google.com/vpc/docs/private-services-access)).
- **Cloud Run** reaches a VPC through Direct VPC egress, which Google labels recommended over a Serverless VPC Access connector ([Connecting to a VPC](https://docs.cloud.google.com/run/docs/configuring/connecting-vpc)); `run.allowedVPCEgress` can require it ([Organization policy constraints](https://docs.cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints)).
- **Cloud NAT** gives private workloads outbound internet and admits no unsolicited inbound connection ([Cloud NAT](https://docs.cloud.google.com/nat/docs/overview)).

A Cloud SQL instance with a public address is reported as `SQL_PUBLIC_IP`, and one that accepts connections from any address as `PUBLIC_SQL_INSTANCE`; `sql.restrictPublicIp` prevents the first ([Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings); [Preventative controls](https://docs.cloud.google.com/architecture/blueprints/security-foundations/preventative-controls)).

## The public door

The one public entry for HTTP is an external Application Load Balancer, a layer-7 proxy that supports serverless backends and Cloud Armor ([External Application Load Balancer](https://docs.cloud.google.com/load-balancing/docs/https)). Cloud Armor adds WAF rules and is always on against layer-3 and layer-4 attacks; layer-7 protection needs a security policy on the backend ([Cloud Armor overview](https://docs.cloud.google.com/armor/docs/cloud-armor-overview)).

Cloud Run's ingress setting decides whether its `run.app` URL is reachable at all: `internal` admits only internal traffic, `internal-and-cloud-load-balancing` also admits the external load balancer and refuses direct requests from the internet, and `all` admits everything ([Cloud Run ingress](https://docs.cloud.google.com/run/docs/securing/ingress)). `run.allowedIngress` restricts which values a project may use ([Organization policy constraints](https://docs.cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints)). Ingress is not authentication: a public service is one that grants `roles/run.invoker` to `allUsers` or turns off the invoker IAM check, and domain-restricted sharing blocks the first ([Allowing public access](https://docs.cloud.google.com/run/docs/authenticating/public)).

## A perimeter against exfiltration

VPC Service Controls draws a perimeter around Google-managed services such as Cloud Storage and BigQuery. Inside it, communication is free; across its edge, it is blocked unless an ingress or egress rule allows it. Its purpose is to reduce the risk of data leaving through stolen credentials, an insider, or a misconfigured IAM grant ([VPC Service Controls overview](https://docs.cloud.google.com/vpc-service-controls/docs/overview)). It is a second line behind IAM, not a replacement for it.

## Seeing the traffic

VPC Flow Logs sample traffic per subnet into Cloud Logging ([VPC Flow Logs](https://docs.cloud.google.com/vpc/docs/flow-logs)); the enterprise foundations blueprint enables them on every subnet ([Detective controls](https://docs.cloud.google.com/architecture/blueprints/security-foundations/detective-controls)). Firewall policy rule logging is opt-in per rule ([Firewall rules logging](https://docs.cloud.google.com/firewall/docs/firewall-rules-logging)). Connectivity Tests simulate a packet's path through the network configuration, which is the first tool when a service cannot reach another ([Connectivity Tests](https://docs.cloud.google.com/network-intelligence-center/docs/connectivity-tests/concepts/overview)).

## Where this stops

This document does not design a client's address plan, its hybrid connection, or the number of environments; those are recorded in the client's installation. It does not repeat the identity side of access, which is [`docs/identity-and-access.md`](identity-and-access.md). A network layout is itself sensitive and does not leave the infrastructure (condition 4 of [`rules/exposure.md`](../rules/exposure.md)).
