---
id: networking
type: doc
clade: engineering
subclade: aws
title: Networking on AWS
summary: The network a workload sits in, as AWS documents it — public and private subnets, security groups and network ACLs, NAT, endpoints and PrivateLink, connecting VPCs, reaching an instance without opening a port, and the controls that keep a resource off the internet — with the detector for each state a review cares about.
references:
  - rules/least-privilege.md
  - rules/data-protection.md
  - docs/cost.md
---

# Networking on AWS

This is the reference for the network a workload sits in. It argues the defaults [`skills/designing-on-aws`](../skills/designing-on-aws/SKILL.md) applies and the conditions `IAM-5` and `CST-4` in the review checklist hold a change to. Every claim cites the AWS page it was read from on 2026-11-14.

## Public and private subnets

A subnet is public when "the subnet has a direct route to an internet gateway"; a private subnet does not, and reaches the internet only through a NAT device ([Subnets for your VPC](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html)). The page also defines VPN-only and isolated subnets.

**The default this plugin takes:** a workload's compute and data run in private subnets, and only what must be reached from the internet — a load balancer, a NAT gateway — sits in a public one. The premise is that a resource with no route from the internet needs no rule to keep the internet out; one in a public subnet depends on every security group and every listener being right.

## Security groups and network ACLs

AWS's comparison ([Infrastructure security in Amazon VPC](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html)): a security group is stateful — return traffic is "automatically allowed" — and has allow rules only; a network ACL is stateless — return traffic "must be explicitly allowed" — and has allow and deny rules.

**The default:** security groups carry the workload's access decisions, written as references between groups (the database group admits the application group) rather than CIDR ranges. Network ACLs stay at their defaults unless a subnet-wide deny is needed, because a stateless rule set has to allow ephemeral return ports explicitly and that is where they break.

Detectors for a group open to the world: AWS Config `restricted-ssh` (SSH from `0.0.0.0/0` or `::/0`), `restricted-common-ports` (defaults 20, 21, 3389, 3306, 4333), `vpc-sg-open-only-to-authorized-ports` (only listed ports may be world-open); Checkov `CKV_AWS_24` (port 22) and `CKV_AWS_25` (port 3389); cdk-nag `AwsSolutions-EC23` ([Config rules](https://docs.aws.amazon.com/config/latest/developerguide/restricted-ssh.html), [Checkov index](https://www.checkov.io/5.Policy%20Index/terraform.html), [cdk-nag rules](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md)).

## Reaching an instance without opening a port

Session Manager lets a person reach an instance "without the need to open inbound ports, maintain bastion hosts, or manage SSH keys" ([AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)). That makes an inbound SSH or RDP rule a finding rather than a convenience: the need it served has an AWS-documented alternative with nothing listening. (The page carries a notice that the legacy page is deprecated on 2026-12-31 and its content moves to the Systems Manager unified console; the capability is unchanged.)

## NAT

A NAT gateway lets "instances in a private subnet can connect to services outside your VPC" while outside services cannot open connections in ([NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)). "Each NAT gateway is created in a specific Availability Zone", and "to improve resiliency, create a NAT gateway in each Availability Zone": a shared gateway's zone going down cuts every other zone's internet access ([NAT gateway basics](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html)). The VPC guide also documents a regional NAT gateway that expands across zones; it was not read for this document, so nothing here depends on it.

A NAT gateway is charged "for each hour that your NAT gateway is available and each gigabyte of data that it processes" ([Pricing for NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)). The resiliency recommendation and the hourly charge pull against each other in a non-production environment; [`docs/cost.md`](cost.md) has the trade.

## Endpoints and PrivateLink

**Gateway endpoints** give "connectivity to Amazon S3 and DynamoDB without requiring an internet gateway or a NAT device", and "there is no additional charge for using gateway endpoints" ([Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)). The NAT pricing page itself recommends an interface or gateway endpoint for traffic to AWS services. So traffic from a private subnet to S3 or DynamoDB through NAT is paid twice for nothing — once per GB processed, and once in the path it takes outside the VPC — and the default is a gateway endpoint in every VPC that talks to either.

**Interface endpoints (AWS PrivateLink)** "privately connect your VPC to services and resources as if they were in your VPC", with no internet gateway, NAT device or public IP ([What is AWS PrivateLink?](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)). They are the route to other AWS services (Secrets Manager, ECR, CloudWatch Logs) from a private subnet that should have no NAT at all, and to a service another VPC publishes.

## Connecting VPCs

VPC peering "does not support transitive peering relationships": A peered to B and B peered to C does not connect A to C, and a peer cannot use another VPC's internet gateway, NAT device, VPN, Direct Connect or gateway endpoint ([How VPC peering connections work](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)). Transit Gateway is "a network transit hub used to interconnect virtual private clouds (VPCs) and on-premises networks" ([What is AWS Transit Gateway?](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)).

**The default:** peering for two VPCs that need each other and nothing else; Transit Gateway once a third VPC or an on-premises network joins, because the number of peering connections grows with every pair and none of them carries traffic onward.

## Keeping resources off the internet

Three controls, from widest to narrowest:

- **VPC Block Public Access** "authoritatively prevents public internet access to VPC resources across an entire AWS account", in bidirectional or ingress-only mode, with per-VPC or per-subnet exclusions ([Block public access to VPCs and subnets](https://docs.aws.amazon.com/vpc/latest/userguide/security-vpc-bpa.html)).
- **S3 Block Public Access**: "by default, new buckets, access points, and objects don't allow public access" ([Blocking public access to your Amazon S3 storage](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)), and a bucket created in the console has all four settings enabled ([Creating a general purpose bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)).
- **RDS public access** decides "whether the DB instance also has a public IP address"; the security group still controls access, and the instance's subnet group needs an internet gateway for the address to be reachable ([Working with a DB instance in a VPC](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html)).

Condition 5 of [`rules/least-privilege.md`](../rules/least-privilege.md) holds a change to these and names their detectors.

## Seeing the traffic

VPC Flow Logs "capture information about the IP traffic going to and from network interfaces in your VPC", to CloudWatch Logs, S3 or Amazon Data Firehose, collected outside the traffic path so throughput and latency are unaffected ([Logging IP traffic using VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)). They are what answers "did this packet reach the group at all" during a diagnosis, which is how [`skills/diagnosing-aws-deployments`](../skills/diagnosing-aws-deployments/SKILL.md) uses them.

## Where this stops

This document does not lay out any particular client's address plan, account network or on-premises link: those are client logic (`ahrena-engineering-fundamentals:rules/client-logic.md`). It does not cover Direct Connect, Site-to-Site VPN or DNS design beyond naming them, and it does not cover a load balancer's TLS configuration, which is in [`rules/data-protection.md`](../rules/data-protection.md).
