# Secrets

The conditions `reviewing-secrets` applies, swept over every added line. Each gives the state, how it is detected, what exempts it, and the correction. The party who gains is whoever can read the repository, its history, a build log or an image layer — always more people than can read the secret store.

### SEC-1 A credential written as a literal

- **State:** an added line holds a value that authenticates: an API key, a token, a password, a private key block, a connection string with a password in it, a signing secret.
- **Detect:** sweep every added line of every file type, including tests, fixtures, examples, notebooks, documentation and workflow files. Look for provider key prefixes, `BEGIN ... PRIVATE KEY`, a URL with `user:password@`, and an assignment to a name such as `password`, `secret`, `token` or `api_key` whose right side is a quoted string of 16 or more characters.
- **Exempt:** a value that is visibly not live and is documented as such: `example`, `changeme`, a provider's published test key, a key generated inside the test that uses it.
- **Correct:** read the value from the environment or the secret store through the module the repository already uses for that; replace the literal with the variable's name. Report the credential for rotation, because removing the line leaves it in history.

### SEC-2 A secret that travels where it is kept

- **State:** a secret written to a log, a trace attribute, an error message, a metric label, a response body, a URL query string or a command line.
- **Detect:** follow each variable that holds a secret from where it is read to every use. A whole configuration object or request header map passed to a logger carries its secrets with it.
- **Exempt:** a fingerprint of the secret, such as its last four characters or a hash, logged to tell keys apart.
- **Correct:** log the identifier of the secret and not its value; pass it in a header or a body and not a URL; pass it to a child process through the environment and not its arguments.

### SEC-3 A secret baked into an artefact

- **State:** a build argument, an image layer, a bundled front-end file or a committed `.env` file that contains a secret.
- **Detect:** in an image definition, an `ARG` or `ENV` holding a secret, or a `COPY` of a file that does. In a front-end build, a secret read into a variable the bundler inlines for the browser. In the tree, an added `.env` file that is not an example.
- **Exempt:** a public identifier that is meant to reach the browser, such as a publishable key the provider documents as public.
- **Correct:** mount the secret at build time without writing it to a layer, or inject it at run time; keep server secrets out of variables the bundler exposes; commit an example file with empty values and ignore the real one.

### SEC-4 A default that works

- **State:** a fallback value for a secret that lets the system start when the secret is absent: `os.environ.get("SIGNING_KEY", "dev")`, a default administrator password, a signature check skipped when no key is configured.
- **Detect:** read every default argument and every `or` on a line that reads a secret, and every branch taken when a key is missing.
- **Exempt:** a default used only by a test fixture.
- **Correct:** fail at start when the secret is missing. A system that refuses to start is noticed; one that starts with a known key is not.
