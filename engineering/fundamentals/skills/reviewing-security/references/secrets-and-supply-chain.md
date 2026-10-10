# Secrets and supply chain

Opened by step 1 of `SKILL.md`. The `secrets` route opens SEC-1 to SEC-4 on every change. The `supply-chain` route opens SUP-1 to SUP-6 when a manifest, an image definition, a pipeline or registry configuration changed.

Each condition gives the state, how it is detected, what exempts it and the correction.

## Secrets

The party who gains is whoever can read the repository, its history, a build log or an image layer. That is always more people than can read the secret store.

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

## Supply chain

The party who gains is whoever can publish a package, an image or an action that this change will download and run.

### SUP-1 A dependency that is not pinned

- **State:** a new dependency, base image or pipeline action referenced by a floating name: no version, a range with no lockfile entry, `latest`, a branch, or a mutable tag for a third-party action.
- **Detect:** read each added line of the manifest, the image definition and the workflow. Check that the lockfile changed with the manifest.
- **Exempt:** a library's own manifest, which declares ranges on purpose, when the repository commits a lockfile for its development and test installs.
- **Correct:** pin the version and commit the lockfile; pin an image by digest; pin a third-party action by commit hash.

### SUP-2 A dependency nobody chose

- **State:** a new package whose name is one edit away from a well-known one, that has no source repository, that was published in the last 30 days, or that duplicates what a dependency already in the tree does.
- **Detect:** read the package's registry page and its repository. Search the tree for an existing dependency with the same job.
- **Exempt:** a package the organisation publishes itself.
- **Correct:** use the existing dependency, or the well-known package the name resembles. Where the new one is intended, the finding is a **question** asking who vetted it.

### SUP-3 Code that runs at install

- **State:** an install or post-install script added to a manifest, a `curl ... | sh` in an image definition or a pipeline, or a package index or registry URL changed to one outside the organisation's.
- **Detect:** read `scripts` in the manifest, every `RUN` line that downloads, and every registry setting.
- **Exempt:** an install script that only builds code already in the tree.
- **Correct:** download a pinned version, verify its checksum, then run it; restore the registry setting.

### SUP-4 A pipeline that hands a stranger its secrets

- **State:** a workflow triggered by a pull request from a fork that checks out the fork's head and has secrets or a write token in scope; a workflow that interpolates a title, a branch name or a comment body into a shell line.
- **Detect:** read the trigger, the checkout reference and the permissions block together. Read every `run` line for an expression that expands text an outside contributor writes.
- **Exempt:** a workflow that only reads, with no secret in scope.
- **Correct:** run a fork's code with a read-only token and no secrets; pass contributor-written text through an environment variable and quote it; declare the narrowest permissions block that works.

### SUP-5 An image that runs as root or carries its build

- **State:** an image definition with no non-root user, or a final stage that keeps compilers, package caches or the source tree's `.git` directory.
- **Detect:** read the last stage for a `USER` line and for what it copies in.
- **Exempt:** a development image that is never deployed.
- **Correct:** add a user and switch to it; copy only the built output into the final stage.

### SUP-6 A known-vulnerable version

- **State:** a dependency added or kept at a version with a published advisory that the code's use of it reaches.
- **Detect:** the repository's audit check, when it has one and it ran. Without one this is **unchecked**, naming the manifest, and the review does not guess from memory.
- **Exempt:** an advisory for a function the tree never calls, when the finding says which and how that was established.
- **Correct:** move to the first fixed version the advisory names.
