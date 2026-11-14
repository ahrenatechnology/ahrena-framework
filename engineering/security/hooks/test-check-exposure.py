#!/usr/bin/env python3
"""Tests for check-exposure.py.

Each case builds a change in a scratch repository, runs the hook as a
subprocess with `--changed HEAD~1...HEAD` and asserts on the exit code and on
the `file:line` and condition of every finding it printed, and on nothing else.

The first case is the incident of #294: the anonymised handler in
fixtures/upstream-error-passthrough.py.txt, added as handlers/credentials.py.
It names #294/AC-2, the criterion it decides. The cases after it pin each
condition of rules/layer-exposure.md the hook decides, in the languages the
agency builds in, and the shapes that must stay quiet: a named field of an
error, a generic error with a correlation id, a key that only spells "error".

Usage:
    python3 engineering/security/hooks/test-check-exposure.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-exposure.py"
INCIDENT = Path(__file__).resolve().parent / "fixtures" / "upstream-error-passthrough.py.txt"
GATE = Path(__file__).resolve().parents[3] / "foundation" / "hooks" / "validate-artifacts.py"
FINDING = re.compile(r"^(\S+:\d+)\n\s+\[layer-exposure\] condition (\d+):", re.MULTILINE)


def incident_line() -> int:
    lines = INCIDENT.read_text(encoding="utf-8").splitlines()
    return next(number for number, line in enumerate(lines, 1) if '"statusCode": 500' in line)


CASES = [
    # #294: (name, files at base, files at head, expected findings as "path:line condition")
    (
        "#294/AC-2 the incident: a handler returns the caught provider error in its response",
        {},
        {"handlers/credentials.py": INCIDENT.read_text(encoding="utf-8")},
        [f"handlers/credentials.py:{incident_line()} 1"],
    ),
    (
        "#294/AC-2 the response line is reported even when the except above it is older",
        {"svc/settings.py": "def get(ssm, name):\n    try:\n        return ssm.get(name)\n    except Exception as exc:\n        raise\n"},
        {"svc/settings.py": "def get(ssm, name):\n    try:\n        return ssm.get(name)\n    except Exception as exc:\n        return {\"statusCode\": 502, \"body\": str(exc)}\n"},
        ["svc/settings.py:5 1"],
    ),
    (
        "#294/AC-2 a caught error interpolated into a log line is reported",
        {},
        {"svc/job.py": "def run(log, step):\n    try:\n        step()\n    except RuntimeError as error:\n        log.error(f\"step failed: {error}\")\n"},
        ["svc/job.py:5 1"],
    ),
    (
        "#294/AC-2 a stack trace in a response is reported",
        {},
        {"svc/api.py": "import traceback\n\ndef view():\n    return {\"trace\": traceback.format_exc()}\n"},
        ["svc/api.py:4 1"],
    ),
    (
        "#294/AC-2 TypeScript: the error's message in an Express response is reported",
        {},
        {"web/route.ts": "app.post('/x', async (req, res) => {\n  try {\n    await put(req.body);\n  } catch (err) {\n    res.status(500).json({ error: err.message });\n  }\n});\n"},
        ["web/route.ts:5 1"],
    ),
    (
        "#294/AC-2 Go: err.Error() written to the client is reported",
        {},
        {"api/handler.go": "package api\n\nfunc Put(w http.ResponseWriter, r *http.Request) {\n\tif err := store(r); err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t}\n}\n"},
        ["api/handler.go:5 1"],
    ),
    (
        "#294/AC-2 Rust: an error turned into the response body in the match arm that binds it is reported",
        {},
        {"src/api.rs": "fn put() -> HttpResponse {\n    match store() {\n        Ok(_) => HttpResponse::NoContent().finish(),\n        Err(e) => HttpResponse::InternalServerError().body(e.to_string()),\n    }\n}\n"},
        ["src/api.rs:4 1"],
    ),
    (
        "#294/AC-2 a dependency's whole response returned to the caller is reported",
        {},
        {"svc/proxy.py": "def view(http):\n    resp = http.get('https://partner.example/v1/accounts')\n    return jsonify(resp.json())\n"},
        ["svc/proxy.py:3 2"],
    ),
    (
        "#294/AC-2 an access policy written to standard output is reported",
        {},
        {"ops/audit.py": "import json\n\ndef show(iam, arn):\n    policy = iam.get_policy_version(PolicyArn=arn)\n    print(json.dumps(policy))\n"},
        ["ops/audit.py:5 3"],
    ),
    (
        "#294/AC-2 the whole environment written to a log is reported, in Python and in Node",
        {},
        {
            "svc/boot.py": "import os\n\ndef start(logger):\n    logger.info(os.environ)\n",
            "web/boot.js": "console.log(process.env);\nconsole.log(process.env.NODE_ENV);\n",
        },
        ["svc/boot.py:4 3", "web/boot.js:1 3"],
    ),
    (
        "#294/AC-2 a Terraform output that publishes a policy or a whole resource is reported, one attribute is not",
        {},
        {"infra/outputs.tf": 'output "policy" {\n  value = aws_iam_policy.service.policy\n}\n\noutput "role" {\n  value = aws_iam_role.service\n}\n\noutput "queue_url" {\n  value = aws_sqs_queue.jobs.url\n}\n'},
        ["infra/outputs.tf:2 3", "infra/outputs.tf:6 3"],
    ),
    (
        "#294/AC-2 the correction stays quiet: generic error and correlation id out, named fields to the log",
        {},
        {"handlers/credentials.py": "def handler(event, store, log, cid):\n    try:\n        store.put(event)\n    except ClientError as error:\n        log.error(\"put failed\", extra={\"code\": error.response[\"Error\"][\"Code\"], \"correlation_id\": cid})\n        return {\"statusCode\": 500, \"body\": json.dumps({\"error\": \"internal error\", \"correlation_id\": cid})}\n"},
        [],
    ),
    (
        "#294/AC-2 a key spelled error with a literal value is not a caught error",
        {},
        {"svc/api.py": "def view(lookup):\n    try:\n        return lookup()\n    except KeyError as error:\n        return {\"error\": \"not found\"}\n"},
        [],
    ),
    (
        "#294/AC-2 a line carrying an ADR pointer is a recorded decision and is not reported",
        {},
        {"tools/cli.py": "import sys\n\ndef main(path):\n    try:\n        open(path)\n    except OSError as exc:\n        print(f\"cannot read {path}: {exc}\", file=sys.stderr)  # ADR-3: the operator reads it\n"},
        [],
    ),
    (
        "#294/AC-2 a docstring that describes the shape is prose, not an exit",
        {},
        {"svc/doc.py": "def view():\n    \"\"\"Never do this:\n\n    return {\"body\": str(error)}\n    \"\"\"\n    return {\"ok\": True}\n"},
        [],
    ),
    (
        "#294/AC-2 a line the change did not add is not reported",
        {"svc/old.py": "def view(x):\n    try:\n        x()\n    except Exception as e:\n        return {\"body\": str(e)}\n"},
        {"svc/old.py": "def view(x):\n    try:\n        x()\n    except Exception as e:\n        return {\"body\": str(e)}\n\n\ndef other():\n    return 1\n"},
        [],
    ),
]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def write(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def scratch(repo: Path, base: dict[str, str], head: dict[str, str]) -> None:
    """A repository with one commit holding `base` and a second applying `head`."""
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "case@example.com")
    git(repo, "config", "user.name", "case")
    git(repo, "config", "commit.gpgsign", "false")
    for commit, files in (("base", {"README": "seed\n", **base}), ("head", head)):
        write(repo, files)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", commit)


def run(repo: Path) -> tuple[int, str]:
    done = subprocess.run(
        [sys.executable, str(HOOK), "--changed", "HEAD~1...HEAD", "."], cwd=repo, capture_output=True, text=True
    )
    return done.returncode, done.stdout + done.stderr


def problems_for(expected: list[str], code: int, output: str) -> list[str]:
    printed = sorted(f"{where.removeprefix('./')} {condition}" for where, condition in FINDING.findall(output))
    problems = []
    if code != (1 if expected else 0):
        problems.append(f"exit code {code}, expected {1 if expected else 0}")
    if printed != sorted(expected):
        problems.append(f"findings {printed}, expected {sorted(expected)}")
    return problems


def report(name: str, problems: list[str], output: str) -> int:
    if not problems:
        print(f"ok    {name}")
        return 0
    print(f"FAIL  {name}")
    for line in problems + output.splitlines():
        print(f"        {line}")
    return 1


def main() -> int:
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for number, (name, base, head, expected) in enumerate(CASES):
            repo = Path(tmp) / f"case-{number}"
            scratch(repo, base, head)
            code, output = run(repo)
            failed += report(name, problems_for(expected, code, output), output)
    gate = subprocess.run([sys.executable, str(GATE)], cwd=GATE.parents[2], capture_output=True, text=True)
    gate_problems = [] if gate.returncode == 0 else [f"exit code {gate.returncode}"]
    failed += report("#294/AC-6 the artifact gate passes with the rule, its doc and its hook in the tree", gate_problems, gate.stdout + gate.stderr)
    total = len(CASES) + 1
    print()
    if failed:
        print(f"{failed} of {total} cases failed.")
        return 1
    print(f"{total} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
