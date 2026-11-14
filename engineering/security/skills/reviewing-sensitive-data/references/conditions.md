# Sensitive data

The conditions `reviewing-sensitive-data` applies. Each gives the state, how it is detected, what exempts it, and the correction.

### DAT-1 Sensitive data at an exit

- **State:** personal data, payment data, a credential, a session token, authorization or infrastructure configuration — an access policy, a role, an identifier that locates a cloud account or an infrastructure resource (an account, project or subscription identifier, an ARN or resource name, a bucket, queue or table name, a secret or parameter path), network topology, deployment state, an internal hostname or path — or a whole request, response, record, configuration or error, written to a log, a trace attribute, a metric label, an error report, standard output, a pipeline log or an infrastructure output. The sensitive classes and the exits are the closed lists of [`rules/layer-exposure.md`](../../../rules/layer-exposure.md).
- **Detect:** each logging, tracing, printing and output line the route pointed at, and what object it is handed; run `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/check-exposure.py" --changed <base>...<head>` (or `--changed <base>` when the head is the working tree) over the changed files, which reports the whole error, the whole upstream response and the policy or whole configuration it can see.
- **Exempt:** an application record's identifier that is not itself personal data; one named field handed to a layer that needs it, such as a role identifier passed to the application as a configuration input.
- **Correct:** emit identifiers, counts and the named fields the reader needs; redact by an allow-list of fields and not a deny-list.

### DAT-2 A response that returns the record

- **State:** a handler that serialises a whole persisted object, so a field added later is exposed by default; a field the caller's role should not see included in a list or an export.
- **Detect:** how each changed response is built.
- **Exempt:** a response built from a schema that names its fields.
- **Correct:** serialise through a response schema that lists the fields.

### DAT-3 A password or secret stored recoverably

- **State:** a password stored in plain text, encrypted reversibly, or hashed with a fast general-purpose hash; an API key stored in plain text where only comparison is needed.
- **Detect:** where the credential is written and compared.
- **Exempt:** a secret the system must present to a third party, kept in the secret store.
- **Correct:** a password hashing function designed for the purpose, with a per-credential salt; store a hash of an API key and show the key once.

### DAT-4 Cryptography chosen by hand

- **State:** a broken or unauthenticated primitive, a constant key, initialisation vector or salt, a non-cryptographic random source used for a token, or certificate verification switched off.
- **Detect:** each hash, cipher, signing, random and transport-security call the route pointed at.
- **Exempt:** a fast hash used as a checksum or cache key with no security claim; verification disabled inside a test against a local server.
- **Correct:** the platform's authenticated encryption with a generated nonce, the cryptographic random source for tokens, and verification left on.

### DAT-5 Data sent to a new recipient

- **State:** personal or confidential data sent to a third party the repository did not send it to before.
- **Detect:** each new outbound call and what its payload holds.
- **Exempt:** a recipient the repository's documents already name for that category of data.
- **Correct:** send the fields the purpose needs. Whether the recipient may receive them at all is a **question** for the organisation.
