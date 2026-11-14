---
id: networking
type: doc
clade: engineering
subclade: cloud
title: Networking on Azure
summary: How a workload's PaaS dependencies are taken off the public internet with private endpoints and private DNS, what an NSG admits by default, what changed in default outbound access, which entry point serves which traffic, and the benchmark controls and Defender recommendations that check it.
references:
  - rules/identity-and-access.md
  - rules/exposure.md
---

# Networking on Azure

The companion of condition 4 of [`rules/identity-and-access.md`](../rules/identity-and-access.md) (nothing public by default) and of the layout items in [`rules/exposure.md`](../rules/exposure.md). Pages read on 2026-11-14.

The Well-Architected Framework's networking guidance is SE:06, *isolate, filter, and control network traffic across both ingress and egress flows*; it asks for private endpoints for PaaS services, defence in depth at every boundary, and rules that allow only the traffic the application needs and deny everything else ([Architecture strategies for networking and connectivity](https://learn.microsoft.com/en-us/azure/well-architected/security/networking)). The Microsoft cloud security benchmark carries the same ground as NS-1 *Establish network segmentation boundaries*, NS-2 *Secure cloud native services with network controls*, NS-3 *Deploy firewall at the edge of enterprise network*, NS-5 *Deploy DDOS protection* and NS-6 *Deploy web application firewall* ([MCSB: Network Security](https://learn.microsoft.com/en-us/security/benchmark/azure/mcsb-network-security)).

## Taking PaaS off the internet: private endpoints

A private endpoint is a network interface with a private IP address from the workload's virtual network, connected to one instance of a PaaS service ([What is a private endpoint?](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)). Two facts from that page shape the rule.

**A private endpoint does not close the public endpoint.** Microsoft says private endpoints provide a private IP for the service but don't necessarily restrict public network access to it. The service's public network access is a separate setting, and a design that adds a private endpoint and leaves public access enabled has added a route, not removed one. That is why condition 4 checks both.

**It needs DNS.** The service's public name has to resolve to the private IP from inside the network, which is done with a private DNS zone; Azure publishes a CNAME on the public name that redirects resolution to the private zone, and an existing public DNS configuration has to be overridden ([Private endpoint DNS](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns)). A private endpoint with no zone link is the most common reason a client inside the network still reaches the public endpoint, or fails to resolve at all once public access is disabled.

**Service endpoints are the older, coarser option.** A service endpoint applies to all instances of the target service, needs no DNS change and does not let the service disable its public address; a private endpoint targets one instance, needs DNS, and does. Microsoft recommends Private Link ([Virtual network integration for Azure services](https://learn.microsoft.com/en-us/azure/virtual-network/vnet-integration-for-azure-services)). The framework recommends the private endpoint for the same reason: a service endpoint opens a path to every storage account in the region, including ones the workload does not own.

Which services start public matters for a review. A new Azure SQL Database server's *Public network access* defaults to Disable ([Connectivity settings](https://learn.microsoft.com/en-us/azure/azure-sql/database/connectivity-settings)). Microsoft's Key Vault security guidance asks to disable public network access and use private endpoints only ([Secure your Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault)). Anonymous read access to blob data is prohibited by default and controlled for the whole account by `AllowBlobPublicAccess` ([Remediate anonymous read access](https://learn.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-prevent)). Anything else is read from the template, not assumed.

## Filtering inside the network: NSGs

A network security group has three default inbound rules that cannot be removed, only overridden by a rule of higher priority: `AllowVnetInBound` (65000), `AllowAzureLoadBalancerInBound` (65001) and `DenyAllInBound` (65500) ([Network security groups](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview)). The first means everything inside the virtual network can reach everything else by default; segmentation is a rule someone writes. A service tag names a group of an Azure service's address prefixes, and an application security group lets a rule name a tier of the application instead of addresses.

Defender for Cloud reports the commonest failures by name: *Management ports should be closed on your virtual machines*, *Internet-facing virtual machines should be protected with network security groups*, and *Subnets should be associated with a network security group* ([Networking recommendations](https://learn.microsoft.com/en-us/azure/defender-for-cloud/recommendations-reference-networking)).

## Outbound traffic

A virtual machine with no explicit outbound method is given an outbound public IP by Azure, which is *default outbound access*. For the API released after 31 March 2026, new virtual networks default to private subnets, without it; existing networks are unchanged. Microsoft recommends a NAT gateway on the subnet as the explicit method for most scenarios ([Default outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access)). A workload that has to filter egress routes it through Azure Firewall, a cloud-native network firewall service ([What is Azure Firewall?](https://learn.microsoft.com/en-us/azure/firewall/overview)).

## Entry points

Microsoft's load-balancing guide places the four services on two axes ([Load balancing options](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/load-balancing-overview)):

| Service | Scope | Traffic |
|---|---|---|
| Azure Front Door | global | HTTP(S) |
| Application Gateway | regional | HTTP(S), TCP, TLS |
| Azure Load Balancer | regional or global | non-HTTP(S), layer 4 |
| Traffic Manager | global | DNS-based, non-HTTP(S) |

A web application firewall runs on Application Gateway, Application Gateway for Containers and Azure Front Door, and on Azure Content Delivery Network in preview ([Azure Web Application Firewall](https://learn.microsoft.com/en-us/azure/web-application-firewall/overview)). A public HTTP entry point therefore gets its WAF from whichever of those it already uses, not from a separate product.

Every Azure service has the default infrastructure-level DDoS protection against common network-layer attacks; DDoS Network Protection (per virtual network) and DDoS IP Protection (per public IP) add tuned protection and support, at layers 3 and 4 ([Azure DDoS Protection overview](https://learn.microsoft.com/en-us/azure/ddos-protection/ddos-protection-overview)). Whether a workload buys one is a cost decision recorded in the design.

## Topology

In a hub-spoke topology, shared services (Azure Firewall, Azure Bastion, a VPN or ExpressRoute gateway, monitoring) sit in a hub virtual network, and each environment deploys to its own spoke for isolation; a hub is regional ([Hub-spoke network topology](https://learn.microsoft.com/en-us/azure/architecture/networking/architecture/hub-spoke)). The Cloud Adoption Framework puts shared resources in the platform landing zone and workload resources in a workload landing zone (see `architecture-framework.md`), so in an organisation that has one, the hub is the platform's and the workload is a spoke; the workload design names the hub it attaches to and does not build one.

## What a layout gives away

Address ranges, a private endpoint's IP, private DNS records and NSG rules are the map of where a workload's data lives and which paths reach it. They are needed inside the platform team and nowhere else, which is why [`rules/exposure.md`](../rules/exposure.md) lists them.

## Where this stops

The address plan, the hub and the peering of a client's estate are the client's, decided in its landing zone; this doc says how a workload attaches to them, not what they are. Hybrid connectivity (VPN, ExpressRoute) and firewall rule design are not covered.
