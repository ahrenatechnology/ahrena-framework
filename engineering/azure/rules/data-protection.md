---
id: data-protection
type: rule
clade: engineering
subclade: cloud
title: Data protection on Azure
statement: On Azure, data is encrypted at rest and reached over TLS 1.2 or later only; a resource never sets a minimum below 1.2 or allows plain HTTP.
enforcement: judgment
references:
  - docs/architecture-framework.md
  - docs/identity-and-access.md
---

# Data protection on Azure

Encryption at rest and in transit for the data a workload keeps on Azure. Most of it is the platform's default, so the conditions are about the settings a deployment can turn the wrong way, and about the ones whose default is not the safe value. The reasons and the pages behind each are in the Security pillar section of [`docs/architecture-framework.md`](../docs/architecture-framework.md).

## Conditions

1. **No data store is configured to accept a TLS version below 1.2.** The Well-Architected Framework's encryption guidance says not to use versions lower than TLS 1.2. On a storage account the `minimumTlsVersion` property is set to `TLS1_2` or later explicitly, because an account created through the CLI, PowerShell or a template leaves it unset, and an unset account accepts TLS 1.0. On every other service that exposes a minimum-TLS setting, the setting is not lowered below 1.2; Azure SQL Database already accepts nothing lower. Decided by a reviewer reading the template, and in a running subscription by the built-in Azure Policy definitions *Storage accounts should have the specified minimum TLS version*, *Azure SQL Database should be running TLS version 1.2 or newer* and *App Service apps should use the latest TLS version*.

2. **No data path accepts plain HTTP.** A storage account keeps *secure transfer required* (`supportsHttpsTrafficOnly`) enabled; it is enabled by default and a template that sets it to `false` fails. A web front end or API redirects or refuses HTTP; the Well-Architected guidance asks for HTTPS on all website communication regardless of the data's sensitivity. Decided by a reviewer, and by the built-in Azure Policy definitions *Secure transfer to storage accounts should be enabled* and *App Service apps should only be accessible over HTTPS*.

3. **No encryption at rest is turned off where the service allows it.** Azure Storage encryption cannot be disabled; Azure SQL Database enables Transparent Data Encryption on every new database; Azure Database for PostgreSQL flexible server always encrypts data at rest. The state that fails is a template or script that disables TDE on a database, or a service whose at-rest encryption is optional and left off. Decided by a reviewer, and for Azure SQL by the built-in Azure Policy definition *Transparent Data Encryption on SQL databases should be enabled*.

4. **A Key Vault that holds a production key or secret keeps its deleted objects recoverable.** Soft delete is on by default and cannot be turned off once on; purge protection is optional and off by default. A production vault enables purge protection, so that a deleted key cannot be purged before its retention period ends. The vault uses the Azure RBAC permission model rather than legacy access policies. Decided by a reviewer, and by the built-in Azure Policy definitions *Key vaults should have deletion protection enabled* and *Azure Key Vault should use RBAC permission model*.

5. **A customer-managed key is used where a requirement names one, and only then.** Azure encrypts data at rest with platform-managed keys by default. The Microsoft cloud security benchmark's control DP-5 asks for a customer-managed key *when required*: by a regulation, a contract or the data's classification. The state that fails is data whose recorded requirement names a customer-managed key, stored with the platform-managed key. A customer-managed key added with no requirement is not a failure, but it is a cost (the key's rotation, its vault, its access) the design has to own. Decided by a reviewer reading the design record.

## Where this stops

**Classification is the project's.** Which data is sensitive, and which requirement calls for a customer-managed key, is decided by the project and by the client, not by this rule; condition 5 checks that a recorded requirement is honoured.

**Encryption at the application layer is not covered.** Field-level encryption, envelope encryption in code and the choice of cipher are `ahrena-engineering-security`'s sensitive-data discipline.

**A client that cannot speak TLS 1.2 is not served by lowering the floor.** The rule has no exception for a legacy client; the answer is a gateway in front of the store, recorded in the design, or retiring the client.

**Backups and replicas inherit the account's settings, and the rule does not re-check them.** A copy exported out of Azure (a database dump to a laptop, a blob downloaded into a pipeline artefact) leaves this rule's reach; the exposure rule, [`exposure.md`](exposure.md), governs where it may go.
