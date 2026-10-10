# Access and sensitive data

Opened by step 1 of `SKILL.md` when the `access` route fires: an added line authenticates, authorises, scopes by owner, handles a credential or a session, hashes, signs, encrypts or logs.

Three parties gain here: an anonymous caller, a user of another tenant, and a user of the same tenant without the role.

How this repository authenticates and where the owner identity comes from were read in step 2. Each condition below is applied against that answer and not against a general idea of good practice.

## Who is asking

### ACC-1 An entry point with no authentication

- **State:** a new route, handler, consumer or job trigger that is reachable without the check the repository's other entry points pass through.
- **Detect:** find two existing entry points of the same kind and compare how they are registered and guarded with how the new one is.
- **Exempt:** an endpoint the repository's documents list as public: a health check, a login, a webhook receiver that verifies a signature (ACC-6).
- **Correct:** register it behind the same guard as its neighbours. Where it may be meant to be public and nothing says so, the finding is a **question**.

### ACC-2 A token accepted without being verified

- **State:** a token decoded and trusted with no signature check, with the algorithm taken from the token itself, or with no check of expiry, issuer or audience.
- **Detect:** each decode call and its options.
- **Exempt:** decoding to read a claim for logging, after a verified decode has already decided access.
- **Correct:** verify with a fixed algorithm and key, and check expiry, issuer and audience.

### ACC-3 A session that outlives its reason

- **State:** a session or token not replaced at login, not invalidated at logout or password change, or with no expiry; a session cookie without the `HttpOnly`, `Secure` and `SameSite` attributes.
- **Detect:** the login, logout and credential-change handlers, and where the cookie is set.
- **Exempt:** a deliberately long-lived machine credential that can be revoked and is stored hashed.
- **Correct:** issue a new session at login, revoke on logout and on credential change, set an expiry and the three cookie attributes.

## What they may do

### ACC-4 A permission checked only where it is shown

- **State:** an action hidden or disabled in the interface for users without a role, with no matching check in the handler that performs it.
- **Detect:** for each new or changed action, open the server handler and look for the role or permission check there.
- **Exempt:** none. The interface is a convenience and the server is the control.
- **Correct:** check in the handler, with the same helper the neighbouring handlers use.

### ACC-5 A record fetched by its identifier alone

- **State:** a read, update or delete that selects by an identifier the caller supplied, with no predicate tying the record to the caller's tenant or ownership.
- **Detect:** each query and each storage, cache, lock or queue key built in the change. Check where the owner part comes from: the authenticated identity is right, the request body or path is not.
- **Exempt:** a table of data that is the same for every tenant.
- **Correct:** add the owner predicate from the authenticated identity, and include the owner in every key.

### ACC-6 A webhook taken at its word

- **State:** an inbound webhook or callback acted on with no signature verification, verified over a re-serialised body in place of the raw bytes, compared with a non-constant-time comparison, or with no protection against replay.
- **Detect:** the receiver, from the first read of the body to the first effect.
- **Exempt:** none for a receiver that causes an effect.
- **Correct:** verify the provider's signature over the raw body with a constant-time comparison, and reject a timestamp outside a stated window or an event identifier already seen.

### ACC-7 A browser trusted across origins

- **State:** a cross-origin policy that reflects the request's origin or allows every origin together with credentials; a state-changing route reachable by a cross-site form with a cookie and no anti-forgery check.
- **Detect:** the cross-origin configuration and each new state-changing route that authenticates by cookie.
- **Exempt:** an API that authenticates by a header the browser does not attach on its own.
- **Correct:** list the allowed origins; require the anti-forgery token, or authenticate by header.

### ACC-8 An answer that tells the caller too much

- **State:** a response that distinguishes "does not exist" from "exists and is not yours", an error that returns a stack trace or a query, or a login and recovery flow that confirms which accounts exist.
- **Detect:** the error paths of each changed handler.
- **Exempt:** detail returned only in a development mode that cannot be enabled in production.
- **Correct:** return the same response for absent and forbidden, and a generic error with a correlation identifier.

## What is kept and shown

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
