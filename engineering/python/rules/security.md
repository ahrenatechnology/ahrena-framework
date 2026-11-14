---
id: security
type: rule
clade: engineering
subclade: python
title: The Python calls that are a security decision
statement: eval, exec, object deserialisers, a shell, an unfiltered tar extract and TLS verification turned off each run only with a reason beside them.
enforcement: hook
enforced-by: hooks/check-python.py
references:
  - docs/libraries.md
  - docs/web-services.md
---

# The Python calls that are a security decision

Five conditions, all decided by `hooks/check-python.py`. Each names a call in Python's standard library or its most common packages that is, by itself, a security decision: it hands a value the authority to run code, to name files, or to impersonate a server. The security plugin's disciplines read these sinks in any language by following a value from where it enters to where it lands. This rule is the half of that work a parser can do in Python without following anything: it finds the call, and it requires the author to have said, beside it, why the input is trusted.

**What this adds to the security plugin, and what it does not.** `reviewing-untrusted-input` decides INP-2 (a command built from text), INP-3 (a path the caller chooses), INP-6 (an evaluator) and INP-7 (bytes turned into objects) by reading where a value came from, which needs a reader. Those conditions are language-agnostic and stay where they are. What a reader cannot do is be present on every commit. This rule makes each of those Python sinks impossible to add silently: the call either carries a reason a reviewer can check, or the hook stops it. The reason is not verified, the same trade condition 3 of [`typing.md`](typing.md) makes for `Any`, and the provenance question remains INP's.

**Why a reason comment and not a ban.** Every one of these calls has a legitimate use. `pickle` on a cache the same process wrote, `exec` in a code generator, `shell=True` in a developer script, `verify=False` behind a flag the user set on purpose. A ban would be wrong about all of them and would be switched off; a reason is one line, written once, where the next reader looks. A comment that instructs a tool — `# noqa: S301`, `# nosec` — is not a reason: it silences a scanner without telling a person anything.

This is the rule [`docs/toolchain.md`](../docs/toolchain.md) refused to put inside the typing rule when it triaged Ruff's `S` family: a security posture is a subject of its own. It does not transcribe `S`. Of bandit's checks it keeps the five whose state is the call itself, and the boundary section says where the rest went.

## What the specification says

The Library Reference states each hazard in the module's own documentation, and each condition follows it:

- **`eval` and `exec` run arbitrary code**: Library Reference, *Built-in Functions*, `eval()` and `exec()`.
- **`pickle` is not secure, and unpickling can execute arbitrary code**; only data you trust should be unpickled: Library Reference, `pickle`, the warning at the top of the module. `marshal` and `shelve` carry the same warning.
- **A shell invoked with untrusted input is vulnerable to injection**: Library Reference, `subprocess`, *Security Considerations*.
- **Tar extraction writes members where their names say unless a filter is given**: Library Reference, `tarfile`, *Extraction filters*, and PEP 706, which added `filter=` and made `data` the default from 3.14.
- **Certificate and hostname verification is on by default in the standard library**, and turning it off is an explicit act: PEP 476, and Library Reference, `ssl`, *Security considerations*.
- **`assert` statements are removed when optimisation is requested**: Language Reference §7.3, *The assert statement*, which is why a check written as one is not a check.

## Conditions

Each of these is decided by `hooks/check-python.py`, and each is satisfied by a comment that is not a tool directive, on the call's line or the line above, saying why the input is trusted.

1. **`eval` and `exec` run nothing but a string literal.** The state is a call to the built-in `eval` or `exec` whose first argument is not a literal. Whoever controls the value writes the program, with the program's whole authority. INP-6 gives `eval` and `exec` no exemption for an outside value; this condition gives one for an inside value, provided the author says it is one.

2. **No deserialiser that builds arbitrary objects runs.** The state is a call to `pickle.load`, `pickle.loads`, `pickle.Unpickler`, `marshal.load`, `marshal.loads`, `shelve.open`, `dill.load`, `dill.loads`, `jsonpickle.decode`, `yaml.unsafe_load`, or `yaml.load` and `yaml.load_all` without a safe loader (`SafeLoader`, `CSafeLoader`, `BaseLoader`). Each builds whatever type the bytes name, and building it runs that type's code; loading bytes someone else wrote runs code someone else wrote. The fix is a data-only format — JSON, `yaml.safe_load`, a Pydantic model over either — which [`docs/libraries.md`](../docs/libraries.md) names per problem.

3. **No shell runs a command that is not a literal.** The state is `os.system`, `os.popen`, `subprocess.getoutput`, `subprocess.getstatusoutput` or `asyncio.create_subprocess_shell`, or a `subprocess` call with `shell=True`, whose command is not a string literal. A shell reads `;`, `|`, `$()` and whitespace in whatever was spliced into the string. A literal command carries nothing spliced and is not reported. The fix is an argument list with `shell` left off, which is INP-2's correction too.

4. **No tar archive is extracted without a filter.** The state is a call to `extractall` or `extract` in a file that imports `tarfile`, without a `filter` argument, on anything not bound in the same file to a `zipfile.ZipFile`. A tar member may be named `../../etc/cron.d/job`, be an absolute path, or be a link out of the target, and before Python 3.14 `tarfile` writes it where it says (CVE-2007-4559). `filter="data"`, accepted from 3.12 and backported to the maintained 3.8 to 3.11 releases, refuses all three. Python 3.14 makes `data` the default; passing it explicitly costs nothing and keeps the code safe on every interpreter it runs on. A zip archive is not read: `zipfile` strips absolute paths and parent references itself.

5. **No call turns TLS verification off.** The state is a call with `verify=False` — the spelling `requests` and `httpx` share — or a call to `ssl._create_unverified_context`. Anyone on the network path can then answer in the server's name and read everything sent. The fix is to point the client at the right certificate bundle; the flag a user sets to trust a host on purpose, as pip's `--trusted-host` does, is the case the reason exists for.

    Measured with the hook as it ships, on 2026-11-14. The CPython 3.14 standard library without its test suite — 721 files, 334,790 lines — gives 60, 16, 10, 0 and 0 findings for conditions 1 to 5; its findings are the interpreter's own machinery: `dataclasses` and `collections` generating code with `exec`, `pickle` and `shelve` implementing themselves, `os.popen` and `platform` calling the shell they wrap. pip 26.2.1 with its vendored libraries — 398 files, 133,846 lines — gives 4, 1, 1, 1 and 2: plugin loading in `pygments`, a configuration editor launched through a shell, an archive helper in `distlib`, and the insecure adapter pip installs when a user passes `--trusted-host`. Read by hand — every finding in pip, and the standard library's by module — each is a site where a reason belongs, which is what the condition asks for. That says the conditions are not wrong about legitimate code; it does not say how often they catch a mistake, because neither corpus is the kind of code the rule exists to hold, a service handling outside input.

## Where this stops

**Provenance is not decided here.** Whether the value reaching one of these calls came from outside is INP-2, INP-3, INP-6 and INP-7 in `reviewing-untrusted-input`, read by a reviewer. A reason comment that is false passes this rule and fails that reading.

**A hardcoded secret is not decided here.** The predecessor's law opened with it. It is SEC-1 of `reviewing-secrets`, which runs on every change, and the pipeline's secret scanner, which a pattern list in this hook would only duplicate worse.

**Input validation at the boundary is not decided here.** The predecessor required every external input to be validated with Pydantic at the edge. That is INP-8 and INP-9 in the security plugin, and the pattern a service follows is in [`docs/web-services.md`](../docs/web-services.md). Whether a function is an edge is not something a parser knows.

**Dependency audit is not decided here.** The predecessor required dependencies audited before adoption and periodically after. That is SUP-2 and SUP-6 of `reviewing-supply-chain`, and `docs/libraries.md` names the auditing tool; a rule about Python source cannot see a lockfile's advisories.

**Query parameterisation is not decided here.** `text(f"SELECT ... {status}")` is INP-1. A parser can see an f-string reaching `text()` or `execute()`, and could not tell an interpolated table name chosen from an allow-list from an interpolated value; the condition would be wrong about the exemption INP-1 itself grants. `docs/persistence.md` shows the bound form.

**`assert` for validation is not decided here.** `python -O` strips every `assert`, so an authorisation check written as one vanishes in an optimised build. Bandit reports every `assert` outside tests, which is wrong about the far more common use — an internal invariant, or narrowing a type for the checker — and a parser cannot tell a guard from an invariant. A reviewer reads it.

**An XML parser, `random` for a token, a weak hash for a password, `tempfile.mktemp`.** Each is a real defect in the right place and a correct call in most places it appears. The first three are DAT-4 and INP-7 readings; the fourth is rare enough that a closed list carrying it would cost more to read than it catches.

**Condition 3 does not see a shell reached through a wrapper.** `sh.run(cmd)` from a third-party library, or a project's own helper that sets `shell=True` inside, is read where the helper is defined, once, and not at each call.

**Condition 4 identifies a zip archive only by a binding in the same file.** An archive object passed in as a parameter, in a file that also imports `tarfile`, is reported whatever it is. The fix when it is a zip is the reason comment, and that is the rarer case.

**This rule declares a hook, and every condition has a script.** The statement reaches no request; the security plugin's disciplines are what a reviewer reads when a finding is disputed.
