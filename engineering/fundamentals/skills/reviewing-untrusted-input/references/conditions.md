# Untrusted input

The conditions `reviewing-untrusted-input` applies. Each gives the state, how it is detected, what exempts it, and the correction. Every one is decided on a pair: where the value enters and where it lands. The party who gains is whoever controls the value.

### INP-1 A query built from text

- **State:** an outside value concatenated, formatted or interpolated into a query string, including an `ORDER BY` column, a table name or a `LIMIT`.
- **Detect:** at each query call, read how the string was built and follow each part back to its origin.
- **Exempt:** an identifier chosen by the server from a closed set, such as a sort column looked up in a dictionary of allowed names.
- **Correct:** bind values as parameters; map an identifier through an allow-list and reject what is not on it.

### INP-2 A command built from text

- **State:** an outside value inside a shell command line, or passed as an argument that the program reads as an option.
- **Detect:** each process call. A single string run through a shell is the state; so is an argument list whose outside value may begin with `-`.
- **Exempt:** an argument list with no shell, where the outside value follows a `--` separator or is validated against a pattern first.
- **Correct:** pass an argument list with the shell disabled, validate the value's shape, and separate options from operands with `--`.

### INP-3 A path the caller chooses

- **State:** an outside value joined into a filesystem path, an archive entry extracted to its own stored name, or an upload saved under the name the client sent.
- **Detect:** each open, read, write, send-file and extract call. Check whether the resolved path is confirmed to sit under the intended directory after joining.
- **Exempt:** a name the server generated, such as an identifier it issued.
- **Correct:** resolve the joined path and confirm it is inside the base directory; store uploads under a generated name and keep the client's name as data.

### INP-4 A URL the caller chooses

- **State:** the server fetches a URL, or a host or port, taken from outside, or follows a redirect from one; the server redirects a browser to an outside-supplied location.
- **Detect:** each outbound request and each redirect response. Follow the address back to its origin.
- **Exempt:** an address looked up by key in the server's own configuration.
- **Correct:** allow-list the destinations; resolve the host and refuse private, loopback and link-local ranges, after every redirect; for a browser redirect, accept a path on the same origin only.

### INP-5 Text rendered as markup

- **State:** an outside value placed into a page, an email or a document through a raw-HTML setter, an unescaped template expression, a `javascript:` or `data:` URL in a link, or a markdown renderer with raw HTML enabled.
- **Detect:** each raw setter and each template expression that turns escaping off. Follow the value back.
- **Exempt:** markup passed through the sanitiser the repository already uses for this, with a closed list of tags.
- **Correct:** render as text; where markup is the feature, sanitise on output with an allow-list of tags and URL schemes.

### INP-6 A template or expression the caller writes

- **State:** an outside value used as the template itself, as a format string, or handed to an evaluator: `eval`, `exec`, a dynamic `Function`, a template rendered from a string, an expression language.
- **Detect:** each evaluator call and each render-from-string call.
- **Exempt:** none for `eval` and `exec`. For a template engine, a sandboxed environment with no access to objects beyond the supplied values.
- **Correct:** make the outside value a parameter of a fixed template; replace evaluation with a parser for the small grammar that is wanted.

### INP-7 Bytes turned into objects

- **State:** outside bytes passed to a deserialiser that can construct arbitrary types: native object serialisation, a YAML loader in its unsafe mode, an XML parser with external entities enabled.
- **Detect:** each load call and its mode.
- **Exempt:** data the same process wrote and that never left its own storage, with an integrity check on read.
- **Correct:** use a data-only format and loader, and validate the result against a declared schema.

### INP-8 A structure accepted whole

- **State:** a request body bound straight onto a persisted record or passed as keyword arguments, so a caller can set a field the form never offered, such as a role, an owner or a price.
- **Detect:** each handler that spreads or binds the body. Compare the fields it accepts with the fields the caller is meant to control.
- **Exempt:** a body parsed into a schema that names its fields and rejects the rest.
- **Correct:** declare the accepted fields and reject unknown ones; set owner, role and other server-decided fields from the authenticated identity.

### INP-9 No bound on what is accepted

- **State:** an outside value that sets a size, a count, a page length, a recursion depth, a regular expression or a timeout with no ceiling; an upload with no size limit; a pattern with nested quantifiers applied to outside text.
- **Detect:** each numeric parameter that reaches a loop, an allocation or a query limit; each upload handler; each regular expression applied to outside text.
- **Exempt:** a ceiling enforced by the framework or the gateway, when the finding can name where.
- **Correct:** clamp the value to a stated maximum, limit the upload size, and bound or rewrite the pattern.

### INP-10 Outside text in a log line or a header

- **State:** an outside value written to a log or a response header with its line breaks intact.
- **Detect:** each log call and header assignment that takes an outside value.
- **Exempt:** structured logging that encodes the value as a field.
- **Correct:** log it as a structured field, or strip control characters.
