# Sensitive data

The conditions `reviewing-sensitive-data` applies. Each gives the state, how it is detected, what exempts it, and the correction.

### DAT-1 Sensitive data in a log, a trace or an error

- **State:** personal data, payment data, a credential, a session token or a whole request or response body written to a log, a trace attribute, a metric label or an error report.
- **Detect:** each logging and tracing call the route pointed at, and what object it is handed.
- **Exempt:** an internal identifier that is not itself personal data.
- **Correct:** log identifiers and counts; redact by an allow-list of fields and not a deny-list.

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
