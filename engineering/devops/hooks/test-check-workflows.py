#!/usr/bin/env python3
"""Tests for check-workflows.py.

Every condition the hook decides is pinned twice: by a workflow that must fail
and by the carve-out it must not flag. Each case builds a throwaway tree with
one or two files under `.github/`, runs the hook against it as a subprocess,
and asserts on the exit code and on the `<rule> condition <n>` fragment the
finding carries.

The carve-outs are where the work is. A secret piped into a command's standard
input is how a secret is handed over without printing it; a token captured
into a variable is not printed; a job that calls a reusable workflow cannot
carry `timeout-minutes`; a `pull_request_target` workflow that checks out the
base is the safe use of that trigger; a GitHub-owned action on a tag is
outside the third-party condition; a line carrying a decision-record pointer
records why a long-lived credential remains.

Criteria covered: #311/AC-2 (every condition the hook decides has a failing
case and a passing carve-out), #311/AC-6 (a workflow that writes a secret, a
token or an infrastructure plan's debug log to its log is a finding, in the
EXPOSURE cases) and #311/AC-8 (the corpus with this plugin passes the artifact
gate, whose graph check keeps the plugins acyclic).

Usage:
    python3 engineering/devops/hooks/test-check-workflows.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-workflows.py"
REPOSITORY = Path(__file__).resolve().parents[3]
GATE = REPOSITORY / "foundation" / "hooks" / "validate-artifacts.py"

SHA = "11bd71901bbe5b1630ceea73d27597364c9af683"

CLEAN = f"""
name: ci
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@{SHA}  # v6.0.0
      - run: make test
"""


def wf(body: str) -> dict[str, str]:
    return {".github/workflows/ci.yml": body}


def job(steps: str, *, head: str = "on: push\npermissions:\n  contents: read\n", extra: str = "") -> str:
    """A workflow with one job whose steps are `steps`, indented under `steps:`."""
    indented = "\n".join("      " + line if line else line for line in steps.strip("\n").splitlines())
    return f"{head}jobs:\n  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n{extra}    steps:\n{indented}\n"


PERMISSIONS = [
    ("a clean workflow passes", wf(CLEAN), ["no failures"], True),
    ("a workflow with no permissions anywhere fails",
     wf(CLEAN.replace("permissions:\n  contents: read\n", "")), ["token-permissions condition 1"], False),
    ("permissions on every job instead of the workflow passes",
     wf("on: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    permissions:\n      contents: read\n"
        "    steps:\n      - run: make\n  b:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    permissions: {}\n"
        "    steps:\n      - run: make\n"),
     ["no failures"], True),
    ("one job without permissions when the workflow has none fails",
     wf("on: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    permissions:\n      contents: read\n"
        "    steps:\n      - run: make\n  b:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: make\n"),
     ["token-permissions condition 1", "jobs.b"], False),
    ("write-all at the workflow fails", wf(CLEAN.replace("permissions:\n  contents: read\n", "permissions: write-all\n")),
     ["token-permissions condition 2"], False),
    ("read-all at a job fails",
     wf(job("- run: make", extra="    permissions: read-all\n")), ["token-permissions condition 2"], False),
]

PINNING = [
    ("a third-party action on a tag fails", wf(job("- uses: astral-sh/setup-uv@v6")), ["action-pinning condition 1"], False),
    ("a third-party action on a short SHA fails", wf(job("- uses: astral-sh/setup-uv@11bd719")),
     ["action-pinning condition 1"], False),
    ("a third-party action on a full SHA passes", wf(job(f"- uses: astral-sh/setup-uv@{SHA}")), ["no failures"], True),
    ("a GitHub-owned action on a tag passes", wf(job("- uses: actions/setup-node@v4\n- uses: github/codeql-action/init@v3")),
     ["no failures"], True),
    ("a local action passes", wf(job("- uses: ./.github/actions/build")), ["no failures"], True),
    ("a third-party reusable workflow on a branch fails",
     wf("on: push\npermissions:\n  contents: read\njobs:\n  call:\n    uses: acme-tools/workflows/.github/workflows/build.yml@main\n"),
     ["action-pinning condition 1"], False),
    ("a third-party action on a tag passes when the workflow lockfile exists",
     {**wf(job("- uses: astral-sh/setup-uv@v6")), ".github/workflows/actions.lock": "{}\n"}, ["no failures"], True),
    ("the lockfile does not cover a reusable workflow on a branch",
     {**wf("on: push\npermissions:\n  contents: read\njobs:\n  call:\n    uses: acme-tools/workflows/.github/workflows/build.yml@v2\n"),
      ".github/workflows/actions.lock": "{}\n"},
     ["action-pinning condition 1"], False),
    ("a docker image without a digest fails", wf(job("- uses: docker://alpine:3.20")), ["action-pinning condition 2"], False),
    ("a docker image by digest passes",
     wf(job("- uses: docker://alpine@sha256:" + "a" * 64)), ["no failures"], True),
    ("a composite action's own step on a tag fails",
     {".github/actions/build/action.yml": "name: build\nruns:\n  using: composite\n  steps:\n"
      "    - uses: astral-sh/setup-uv@v6\n    - run: make\n      shell: bash\n"},
     ["action-pinning condition 1", ".github/actions/build/action.yml"], False),
]

CREDENTIALS = [
    ("an AWS access key handed to the login action fails",
     wf(job("- uses: aws-actions/configure-aws-credentials@" + SHA + "\n  with:\n"
            "    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}\n"
            "    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}\n    aws-region: eu-west-1")),
     ["cloud-credentials condition 1"], False),
    ("an AWS role assumed by OIDC passes",
     wf(job("- uses: aws-actions/configure-aws-credentials@" + SHA + "\n  with:\n"
            "    role-to-assume: ${{ vars.DEPLOY_ROLE }}\n    aws-region: eu-west-1",
            head="on: push\npermissions:\n  contents: read\n  id-token: write\n")),
     ["no failures"], True),
    ("a Google service-account key handed to the auth action fails",
     wf(job("- uses: google-github-actions/auth@" + SHA + "\n  with:\n    credentials_json: ${{ secrets.GCP_SA_KEY }}")),
     ["cloud-credentials condition 1"], False),
    ("Google Workload Identity Federation passes",
     wf(job("- uses: google-github-actions/auth@" + SHA + "\n  with:\n"
            "    workload_identity_provider: ${{ vars.WIF_PROVIDER }}\n    service_account: ${{ vars.DEPLOY_SA }}")),
     ["no failures"], True),
    ("an Azure creds JSON handed to the login action fails",
     wf(job("- uses: azure/login@" + SHA + "\n  with:\n    creds: ${{ secrets.AZURE_CREDENTIALS }}")),
     ["cloud-credentials condition 1"], False),
    ("Azure login by federated credential passes",
     wf(job("- uses: azure/login@" + SHA + "\n  with:\n    client-id: ${{ vars.AZURE_CLIENT_ID }}\n"
            "    tenant-id: ${{ vars.AZURE_TENANT_ID }}\n    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}")),
     ["no failures"], True),
    ("a Terraform client secret in the job env fails",
     wf(job("- run: terraform plan", extra="    env:\n      ARM_CLIENT_SECRET: ${{ secrets.ARM_CLIENT_SECRET }}\n")),
     ["cloud-credentials condition 2"], False),
    ("an AWS key in the workflow env fails",
     wf("on: push\npermissions:\n  contents: read\nenv:\n  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_KEY }}\n"
        "jobs:\n  a:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: aws s3 ls\n"),
     ["cloud-credentials condition 2"], False),
    ("a key file activated on the command line fails",
     wf(job("- run: gcloud auth activate-service-account --key-file=key.json")), ["cloud-credentials condition 3"], False),
    ("az login with a client secret fails",
     wf(job("- run: az login --service-principal -u $ID -p $SECRET --tenant $TENANT")), ["cloud-credentials condition 3"], False),
    ("a remaining key with a decision-record pointer passes",
     wf(job("- uses: azure/login@" + SHA + "\n  with:\n    creds: ${{ secrets.AZURE_CREDENTIALS }}  # ADR-7")),
     ["no failures"], True),
]

INJECTION = [
    ("a pull request title in a run step fails",
     wf(job('- run: echo "Title: ${{ github.event.pull_request.title }}"')), ["script-injection condition 1"], False),
    ("the head branch in a multi-line run fails",
     wf(job("- run: |\n    git fetch origin\n    git switch ${{ github.head_ref }}")), ["script-injection condition 1"], False),
    ("an issue body in github-script fails",
     wf(job("- uses: actions/github-script@v7\n  with:\n    script: |\n      const b = `${{ github.event.issue.body }}`")),
     ["script-injection condition 1"], False),
    ("a commit message in a composite action's run fails",
     {".github/actions/note/action.yml": "name: note\nruns:\n  using: composite\n  steps:\n"
      "    - run: echo \"${{ github.event.head_commit.message }}\"\n      shell: bash\n"},
     ["script-injection condition 1"], False),
    ("the title through an environment variable passes",
     wf(job('- env:\n    TITLE: ${{ github.event.pull_request.title }}\n  run: echo "Title: $TITLE"')),
     ["no failures"], True),
    ("a head SHA and the repository name pass",
     wf(job("- run: git checkout ${{ github.event.pull_request.head.sha }} && echo ${{ github.event.repository.name }}")),
     ["no failures"], True),
]

TRIGGERS = [
    ("pull_request_target checking out the head SHA fails",
     wf(job("- uses: actions/checkout@v5\n  with:\n    ref: ${{ github.event.pull_request.head.sha }}\n- run: make test",
            head="on: pull_request_target\npermissions:\n  contents: read\n")),
     ["privileged-triggers condition 1"], False),
    ("workflow_run checking out the triggering branch fails",
     wf(job("- uses: actions/checkout@v5\n  with:\n    ref: ${{ github.event.workflow_run.head_branch }}",
            head="on:\n  workflow_run:\n    workflows: [ci]\n    types: [completed]\npermissions:\n  contents: read\n")),
     ["privileged-triggers condition 1"], False),
    ("pull_request_target running gh pr checkout fails",
     wf(job("- run: gh pr checkout ${{ github.event.number }}",
            head="on: pull_request_target\npermissions:\n  contents: read\n")),
     ["privileged-triggers condition 1"], False),
    ("pull_request_target checking out the base passes",
     wf(job("- uses: actions/checkout@v5\n- run: ./label.sh",
            head="on: pull_request_target\npermissions:\n  pull-requests: write\n")),
     ["no failures"], True),
    ("pull_request checking out the head SHA passes",
     wf(job("- uses: actions/checkout@v5\n  with:\n    ref: ${{ github.event.pull_request.head.sha }}",
            head="on: pull_request\npermissions:\n  contents: read\n")),
     ["no failures"], True),
]

EXPOSURE = [
    ("#311/AC-6 a secret echoed through its environment variable fails",
     wf(job('- env:\n    API_TOKEN: ${{ secrets.API_TOKEN }}\n  run: echo "token is $API_TOKEN"')),
     ["log-exposure condition 1"], False),
    ("#311/AC-6 a secret expression printed directly fails",
     wf(job("- run: echo ${{ secrets.DEPLOY_KEY }}")), ["log-exposure condition 1"], False),
    ("#311/AC-6 the whole secrets context printed fails",
     wf(job("- run: echo '${{ toJSON(secrets) }}'")), ["log-exposure condition 1"], False),
    ("a secret piped into a command's stdin passes",
     wf(job('- env:\n    REGISTRY_TOKEN: ${{ secrets.REGISTRY_TOKEN }}\n'
            '  run: echo "$REGISTRY_TOKEN" | docker login ghcr.io -u bot --password-stdin')),
     ["no failures"], True),
    ("a secret written to a file passes",
     wf(job('- env:\n    NPM_TOKEN: ${{ secrets.NPM_TOKEN }}\n  run: echo "//registry.npmjs.org/:_authToken=$NPM_TOKEN" > .npmrc')),
     ["no failures"], True),
    ("#311/AC-6 the environment dumped fails", wf(job("- run: env | sort")), ["log-exposure condition 2"], False),
    ("#311/AC-6 printenv alone fails", wf(job("- run: |\n    set -e\n    printenv")), ["log-exposure condition 2"], False),
    ("printenv of one plain variable passes", wf(job("- run: printenv GITHUB_SHA")), ["no failures"], True),
    ("#311/AC-6 the github context printed fails",
     wf(job("- env:\n    CTX: ${{ toJSON(github) }}\n  run: echo \"$CTX\"")), ["log-exposure condition 2"], False),
    ("#311/AC-6 shell tracing in a job holding a secret fails",
     wf(job("- env:\n    TOKEN: ${{ secrets.TOKEN }}\n  run: |\n    set -euxo pipefail\n    ./deploy.sh")),
     ["log-exposure condition 3"], False),
    ("shell tracing in a job with no secret passes", wf(job("- run: |\n    set -x\n    make")), ["no failures"], True),
    ("#311/AC-6 an access token printed by the CLI fails",
     wf(job("- run: gcloud auth print-access-token")), ["log-exposure condition 4"], False),
    ("#311/AC-6 the caller identity printed fails",
     wf(job("- run: aws sts get-caller-identity")), ["log-exposure condition 4"], False),
    ("#311/AC-6 a minted token echoed through a command substitution fails",
     wf(job('- run: echo "deploying with $(gcloud auth print-access-token)"')), ["log-exposure condition 4"], False),
    ("a token captured into a variable passes",
     wf(job('- run: |\n    TOKEN="$(az account get-access-token --query accessToken -o tsv)"\n    echo "::add-mask::$TOKEN"')),
     ["no failures"], True),
    ("a registry password piped to docker login passes",
     wf(job("- run: aws ecr get-login-password | docker login --username AWS --password-stdin $REGISTRY")),
     ["no failures"], True),
    ("#311/AC-6 Terraform debug logging switched on fails",
     wf(job("- run: terraform plan", extra="    env:\n      TF_LOG: DEBUG\n")), ["log-exposure condition 5"], False),
    ("TF_LOG off passes", wf(job("- run: terraform plan", extra="    env:\n      TF_LOG: \"off\"\n")), ["no failures"], True),
]

DEPLOYMENTS = [
    ("a deploy job without a concurrency group fails",
     wf(job("- run: ./deploy.sh", extra="    environment: production\n")), ["protected-deployments condition 1"], False),
    ("a deploy job with a queued concurrency group passes",
     wf(job("- run: ./deploy.sh",
            extra="    environment:\n      name: production\n      url: https://example.invalid\n"
                  "    concurrency:\n      group: deploy-production\n      cancel-in-progress: false\n")),
     ["no failures"], True),
    ("workflow-level concurrency covers the deploy job",
     wf(job("- run: ./deploy.sh", head="on: push\npermissions:\n  contents: read\nconcurrency: deploy-${{ github.ref }}\n",
            extra="    environment: staging\n")),
     ["no failures"], True),
    ("a deploy that cancels an in-flight deploy fails",
     wf(job("- run: ./deploy.sh",
            extra="    environment: production\n    concurrency:\n      group: prod\n      cancel-in-progress: true\n")),
     ["protected-deployments condition 2"], False),
]

TIMEOUTS = [
    ("a job without timeout-minutes fails",
     wf("on: push\npermissions:\n  contents: read\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n"),
     ["job-timeouts condition 1"], False),
    ("a timeout given as an expression passes",
     wf("on: push\npermissions:\n  contents: read\njobs:\n  a:\n    runs-on: ubuntu-latest\n"
        "    timeout-minutes: ${{ fromJSON(vars.TIMEOUT) }}\n    steps:\n      - run: make\n"),
     ["no failures"], True),
    ("a job that calls a reusable workflow needs no timeout",
     wf("on: push\npermissions:\n  contents: read\njobs:\n  call:\n    uses: ./.github/workflows/build.yml\n"),
     ["no failures"], True),
]

PARSING = [
    ("a file that is not YAML the hook can read is reported, not passed",
     wf("on: push\njobs:\n  a: [unterminated\n"), ["could not read"], False),
    ("flow sequences, quoted keys and block scalars parse",
     wf("'on':\n  push:\n    branches: [ main, 'release/*' ]\npermissions: { contents: read }\njobs:\n  a:\n"
        "    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - name: >-\n          long name\n"
        "        run: |\n          # a comment inside the script\n          make\n"),
     ["no failures"], True),
]

CASES = PERMISSIONS + PINNING + CREDENTIALS + INJECTION + TRIGGERS + EXPOSURE + DEPLOYMENTS + TIMEOUTS + PARSING


def run(files: dict[str, str]) -> tuple[int, str]:
    root = Path(tempfile.mkdtemp(prefix="check-workflows-"))
    try:
        for rel, text in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        result = subprocess.run([sys.executable, str(HOOK), str(root)], capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr
    finally:
        shutil.rmtree(root, ignore_errors=True)


def gate_case() -> tuple[str, list[str], bool, tuple[int, str]]:
    """#311/AC-8: the artifact gate passes on the repository that carries this plugin."""
    result = subprocess.run([sys.executable, str(GATE)], cwd=REPOSITORY, capture_output=True, text=True)
    return ("#311/AC-8 the artifact gate passes with this plugin in the catalogue", ["no failures"], True,
            (result.returncode, result.stdout + result.stderr))


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    problems = []
    if ok and code != 0:
        problems.append(f"exit {code}, expected 0")
    if not ok and code != 1:
        problems.append(f"exit {code}, expected 1")
    problems += [f"missing {text!r}" for text in expect if text != "no failures" and text not in output]
    return problems


def main() -> int:
    failed = 0
    results = [(name, expect, ok, run(files)) for name, files, expect, ok in CASES] + [gate_case()]
    for name, expect, ok, (code, output) in results:
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            print(f"FAIL  {name}: {'; '.join(problems)}")
            print("      " + output.strip().replace("\n", "\n      "))
        else:
            print(f"ok    {name}")
    print()
    print(f"{failed} of {len(results)} cases failed." if failed else f"{len(results)} cases passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
