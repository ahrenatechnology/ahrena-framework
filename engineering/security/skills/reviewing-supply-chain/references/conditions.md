# Supply chain

The conditions `reviewing-supply-chain` applies. Each gives the state, how it is detected, what exempts it, and the correction. The party who gains is whoever can publish a package, an image or an action that this change will download and run.

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
