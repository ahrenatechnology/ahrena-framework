#!/usr/bin/env python3
"""Tests for check-terraform.py.

Every condition the hook decides is pinned twice: by a fixture that must fail
and by the carve-out it must not flag. Each case builds a throwaway tree, runs
the hook against it as a subprocess, and asserts on the exit code and on the
`<rule> condition <n>` fragment the finding carries.

The carve-outs are where the work is. A secret-named variable with no default
is the correct way to take a secret, a whole-object output of a child module
is how modules compose, a reusable module's `>=` constraint is what HashiCorp
asks for, and a test file in `tests/` is as close to its module as one in the
module's own folder.

One case initialises a git repository, because "in the repository" means
tracked or about to be: a state file that `.gitignore` excludes is on disk and
not in the repository, and reporting it would fail every working copy that has
ever run `terraform apply` locally.

Criteria covered: #295/AC-2 (every condition the hook decides has a failing
case and a passing carve-out), #295/AC-3 (an output carrying a policy, a
credential or a connection string without `sensitive` is a finding, in the
OUTPUT_CASES) and #295/AC-6 (the corpus with this plugin passes the artifact
gate, whose graph check keeps the plugins acyclic).

Usage:
    python3 engineering/terraform/hooks/test-check-terraform.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-terraform.py"
REPOSITORY = Path(__file__).resolve().parents[3]
GATE = REPOSITORY / "foundation" / "hooks" / "validate-artifacts.py"

VERSIONS = '''
terraform {
  required_version = ">= 1.10"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  backend "s3" {}
}
'''

MAIN = '''
resource "random_pet" "name" {
  length = 2
}

output "pet_name" {
  value = random_pet.name.id
}
'''

LOCK = '''
provider "registry.terraform.io/hashicorp/random" {
  version     = "3.6.3"
  constraints = "~> 3.6"
}
'''

CLEAN_ROOT = {"versions.tf": VERSIONS, "main.tf": MAIN, ".terraform.lock.hcl": LOCK}

CHILD_VERSIONS = '''
terraform {
  required_version = ">= 1.10"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}
'''

CHILD_MAIN = '''
variable "length" {
  type = number
}

resource "random_pet" "this" {
  length = var.length
}

output "name" {
  value = random_pet.this.id
}
'''

CHILD_TEST = '''
run "names_a_pet" {
  command = plan
  variables {
    length = 2
  }
}
'''

CALLS_CHILD = '''
module "pet" {
  source = "./modules/pet"
  length = 2
}
'''


def child(name: str = "pet", test: str = "tests/pet.tftest.hcl") -> dict[str, str]:
    """A clean child module under `modules/<name>`, with its test where `test` says."""
    base = f"modules/{name}"
    files = {f"{base}/versions.tf": CHILD_VERSIONS, f"{base}/main.tf": CHILD_MAIN}
    if test:
        files[f"{base}/{test}"] = CHILD_TEST
    return files


def tree(*parts: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for part in parts:
        merged.update(part)
    return merged


def root_with(extra: str) -> dict[str, str]:
    """The clean root configuration with `extra` appended to its main.tf."""
    return tree(CLEAN_ROOT, {"main.tf": MAIN + extra})


# ---------------------------------------------------------------------------

STATE_CASES = [
    ("clean root and child", tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD}), ["no failures"], True),
    ("state file in the tree", tree(CLEAN_ROOT, {"terraform.tfstate": "{}"}), ["state condition 1"], False),
    ("backup state file", tree(CLEAN_ROOT, {"terraform.tfstate.backup": "{}"}), ["state condition 1"], False),
    ("saved plan file", tree(CLEAN_ROOT, {"release.tfplan": "x"}), ["state condition 1"], False),
    (
        "the .terraform directory",
        tree(CLEAN_ROOT, {".terraform/terraform.tfstate": "{}"}),
        ["state condition 1", ".terraform/"],
        False,
    ),
    (
        "root module without a backend",
        tree(CLEAN_ROOT, {"versions.tf": VERSIONS.replace('  backend "s3" {}\n', "")}),
        ["state condition 2"],
        False,
    ),
    (
        "root module on the local backend",
        tree(CLEAN_ROOT, {"versions.tf": VERSIONS.replace('backend "s3" {}', 'backend "local" {}')}),
        ["state condition 2"],
        False,
    ),
    (
        "a cloud block is a remote backend",
        tree(CLEAN_ROOT, {"versions.tf": VERSIONS.replace('backend "s3" {}', 'cloud {\n    organization = "o"\n  }')}),
        ["no failures"],
        True,
    ),
    (
        "an example is a root module that owes no backend",
        tree(CLEAN_ROOT, {"examples/basic/main.tf": MAIN}),
        ["no failures"],
        True,
    ),
    (
        "locking switched off in a pipeline",
        tree(CLEAN_ROOT, {".github/workflows/apply.yml": "run: terraform apply -lock=false plan.out\n"}),
        ["state condition 3"],
        False,
    ),
    (
        "locking switched off in a script",
        tree(CLEAN_ROOT, {"scripts/apply.sh": "tofu apply -lock=false\n"}),
        ["state condition 3"],
        False,
    ),
]

SECRET_VARIABLE = '''
variable "db_password" {
  type      = string
  sensitive = true
  default   = "hunter2-but-longer"
}
'''

UNMARKED_SECRET_VARIABLE = '''
variable "api_token" {
  type = string
}
'''

TAKEN_SECRET_VARIABLE = '''
variable "db_password" {
  type      = string
  sensitive = true
}

variable "admin_token" {
  type      = string
  ephemeral = true
  default   = null
}

variable "db_password_secret_arn" {
  type    = string
  default = "arn:example:secret:db"
}
'''

LITERAL_CREDENTIAL = '''
provider "random" {
  access_key = "AKIAEXAMPLEEXAMPLE"
}
'''

LITERAL_WRITE_ONLY = '''
resource "random_password" "db" {
  length      = 32
  password_wo = "plain-in-the-source"
}
'''

REFERENCED_CREDENTIAL = '''
resource "random_password" "db" {
  length              = 32
  password_wo         = var.db_password
  password_wo_version = 1
  secret_name         = "orders-db"
}
'''

SECRET_CASES = [
    ("a secret variable with a default", root_with(SECRET_VARIABLE), ["secrets condition 1"], False),
    (
        "a default is reported on its own line",
        root_with(SECRET_VARIABLE),
        ["main.tf:13\n    [secrets] secrets condition 1"],
        False,
    ),
    ("a secret variable not marked sensitive", root_with(UNMARKED_SECRET_VARIABLE), ["secrets condition 2"], False),
    ("a secret variable taken the right way", root_with(TAKEN_SECRET_VARIABLE), ["no failures"], True),
    ("a literal credential in a provider block", root_with(LITERAL_CREDENTIAL), ["secrets condition 3"], False),
    ("a literal written to a write-only argument", root_with(LITERAL_WRITE_ONLY), ["secrets condition 3"], False),
    (
        "a credential argument fed by a reference",
        root_with(REFERENCED_CREDENTIAL + TAKEN_SECRET_VARIABLE),
        ["no failures"],
        True,
    ),
    (
        "a versioned tfvars file holding a secret",
        tree(CLEAN_ROOT, {"prod.tfvars": 'region      = "eu"\ndb_password = "s3cr3t-value"\n'}),
        ["secrets condition 4"],
        False,
    ),
    (
        "a versioned tfvars file with no secret",
        tree(CLEAN_ROOT, {"prod.tfvars": 'region = "eu"\ninstance_count = 3\n'}),
        ["no failures"],
        True,
    ),
]

POLICY_OUTPUT = '''
data "random_policy_document" "reader" {
}

output "reader_policy" {
  value = data.random_policy_document.reader.json
}
'''

CONNECTION_OUTPUT = '''
output "database" {
  value = "postgres://app:${random_pet.name.id}@db.internal:5432/orders"
  description = "for the app"
}

output "connection_string" {
  value = random_pet.name.id
}
'''

CREDENTIAL_OUTPUT = '''
resource "random_password" "db" {
  length = 32
}

output "db" {
  value = random_password.db.result
}

output "admin" {
  value = random_password.db.password
}
'''

SENSITIVE_VARIABLE_OUTPUT = '''
variable "seed" {
  type      = string
  sensitive = true
}

output "seed_echo" {
  value = var.seed
}
'''

MARKED_OUTPUTS = '''
output "reader_policy" {
  value     = random_pet.name.id
  sensitive = true
}

output "policy_arn" {
  value = random_pet.name.id
}
'''

WHOLE_RESOURCE_OUTPUT = '''
output "pet" {
  value = random_pet.name
}
'''

WHOLE_MODULE_OUTPUT = '''
output "everything" {
  value = module.pet
}
'''

OUTPUT_CASES = [
    ("an output carrying a policy", root_with(POLICY_OUTPUT), ["outputs condition 1", "reader_policy"], False),
    ("an output carrying a connection string", root_with(CONNECTION_OUTPUT), ["outputs condition 1", "database"], False),
    ("an output named for a connection string", root_with(CONNECTION_OUTPUT), ["connection_string"], False),
    ("an output carrying a credential", root_with(CREDENTIAL_OUTPUT), ["outputs condition 1", '"admin"'], False),
    ("a generated secret's result", root_with(CREDENTIAL_OUTPUT), ['"db"'], False),
    ("an output echoing a sensitive variable", root_with(SENSITIVE_VARIABLE_OUTPUT), ["outputs condition 1"], False),
    ("sensitive outputs and an identifier", root_with(MARKED_OUTPUTS), ["no failures"], True),
    ("a root output of a whole resource", root_with(WHOLE_RESOURCE_OUTPUT), ["outputs condition 2"], False),
    (
        "a root output of a whole module",
        tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD + WHOLE_MODULE_OUTPUT}),
        ["outputs condition 2"],
        False,
    ),
    (
        "a child module may hand a whole object to its caller",
        tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD}, {"modules/pet/obj.tf": WHOLE_RESOURCE_OUTPUT.replace("name", "this")}),
        ["no failures"],
        True,
    ),
    (
        "a pipeline printing every output",
        tree(CLEAN_ROOT, {".github/workflows/plan.yml": "run: terraform output -json\n"}),
        ["outputs condition 3"],
        False,
    ),
    (
        "a pipeline printing a plan as JSON",
        tree(CLEAN_ROOT, {"ci/plan.sh": "terraform show -json plan.out\n"}),
        ["outputs condition 3"],
        False,
    ),
    (
        "a global option before the subcommand does not hide the print",
        tree(CLEAN_ROOT, {".github/workflows/plan.yml": "run: terraform -chdir=live/prod show -json plan.tfplan\n"}),
        ["outputs condition 3"],
        False,
    ),
    (
        "a pipeline capturing an output into a file or a variable",
        tree(
            CLEAN_ROOT,
            {"ci/plan.sh": "terraform show -json plan.out > plan.json\nNAME=$(terraform output -raw pet_name)\n"},
        ),
        ["no failures"],
        True,
    ),
]

UNPINNED_PROVIDER = VERSIONS.replace('      version = "~> 3.6"\n', "")
NO_REQUIRED_VERSION = VERSIONS.replace('  required_version = ">= 1.10"\n', "")
UNDECLARED_PROVIDER = '''
resource "tls_private_key" "k" {
  algorithm = "ED25519"
}
'''

REGISTRY_UNPINNED = '''
module "net" {
  source = "example/network/random"
}
'''

REGISTRY_RANGE = '''
module "net" {
  source  = "example/network/random"
  version = "~> 2.1"
}
'''

GIT_UNPINNED = '''
module "net" {
  source = "git::https://example.com/network.git"
}
'''

GIT_BRANCH = '''
module "net" {
  source = "git::https://example.com/network.git?ref=main"
}
'''

PINNED_MODULES = '''
module "net" {
  source  = "example/network/random"
  version = "2.1.4"
}

module "dns" {
  source = "git::https://example.com/dns.git?ref=v1.4.0"
}
'''

PINNING_CASES = [
    ("a provider with no version", tree(CLEAN_ROOT, {"versions.tf": UNPINNED_PROVIDER}), ["pinning condition 2"], False),
    ("no required_version", tree(CLEAN_ROOT, {"versions.tf": NO_REQUIRED_VERSION}), ["pinning condition 1"], False),
    ("a provider used but not declared", root_with(UNDECLARED_PROVIDER), ["pinning condition 2", "tls"], False),
    (
        "a root provider with no upper bound",
        tree(CLEAN_ROOT, {"versions.tf": VERSIONS.replace("~> 3.6", ">= 3.6")}),
        ["pinning condition 3"],
        False,
    ),
    (
        "a reusable module with an upper bound",
        tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD, "modules/pet/versions.tf": CHILD_VERSIONS.replace(">= 3.0", "~> 3.6")}),
        ["pinning condition 3", "modules/pet"],
        False,
    ),
    ("a registry module with no version", root_with(REGISTRY_UNPINNED), ["pinning condition 4"], False),
    ("a registry module on a range", root_with(REGISTRY_RANGE), ["pinning condition 4"], False),
    ("a git module with no ref", root_with(GIT_UNPINNED), ["pinning condition 4"], False),
    ("a git module on a branch", root_with(GIT_BRANCH), ["pinning condition 4"], False),
    ("a module pin is reported on its source line", root_with(GIT_BRANCH), ["main.tf:11\n    [pinning] pinning condition 4"], False),
    ("modules pinned exactly", root_with(PINNED_MODULES), ["no failures"], True),
    (
        "a github.com source is git, not a registry address",
        root_with('\nmodule "net" {\n  source = "github.com/acme/network/aws"\n}\n'),
        ["pinning condition 4", "has no `?ref=`"],
        False,
    ),
    ("a root module with no lock file", {"versions.tf": VERSIONS, "main.tf": MAIN}, ["pinning condition 5"], False),
    (
        "a lock file that does not list a declared provider",
        tree(CLEAN_ROOT, {"versions.tf": VERSIONS.replace("    random = {", '    tls = {\n      source  = "hashicorp/tls"\n      version = "~> 4.0"\n    }\n    random = {')}),
        ["pinning condition 5", "hashicorp/tls"],
        False,
    ),
    (
        "a stub lock file",
        tree(CLEAN_ROOT, {".terraform.lock.hcl": "# lock\n"}),
        ["pinning condition 5", "hashicorp/random"],
        False,
    ),
]

CYCLE_A = '''
module "b" {
  source = "../b"
}
'''

CYCLE_B = '''
module "a" {
  source = "../a"
}
'''

CALLS_ROOT = '''
module "everything" {
  source = "../.."
}
'''

PROVIDER_IN_CHILD = '''
provider "random" {
}
'''

BACKEND_IN_CHILD = '''
terraform {
  backend "s3" {}
}
'''


def cycle() -> dict[str, str]:
    parts = tree(child("a"), child("b"))
    parts["modules/a/calls.tf"] = CYCLE_A
    parts["modules/b/calls.tf"] = CYCLE_B
    return parts


BOUNDARY_CASES = [
    ("two modules calling each other", tree(CLEAN_ROOT, cycle()), ["module-boundaries condition 1"], False),
    (
        "a module calling the root configuration",
        tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD, "modules/pet/up.tf": CALLS_ROOT}),
        ["module-boundaries condition 2"],
        False,
    ),
    (
        "a provider block in a reusable module",
        tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD, "modules/pet/providers.tf": PROVIDER_IN_CHILD}),
        ["module-boundaries condition 3"],
        False,
    ),
    (
        "a backend in a reusable module",
        tree(CLEAN_ROOT, child(), {"pet.tf": CALLS_CHILD, "modules/pet/backend.tf": BACKEND_IN_CHILD}),
        ["module-boundaries condition 3"],
        False,
    ),
]

TEST_CASES = [
    ("a module with no test", tree(CLEAN_ROOT, child(test="")), ["test-placement condition 1", "modules/pet"], False),
    ("a test in the module's own folder", tree(CLEAN_ROOT, child(test="pet.tftest.hcl")), ["no failures"], True),
    ("an OpenTofu test file", tree(CLEAN_ROOT, child(test="tests/pet.tofutest.hcl")), ["no failures"], True),
    (
        "a test in another module's folder does not count",
        tree(CLEAN_ROOT, child("a"), child("b", test="")),
        ["test-placement condition 1", "modules/b"],
        False,
    ),
]

PARSER_CASES = [
    (
        "comments, heredocs and nested strings do not confuse the reader",
        root_with(
            '\n# output "x" { value = random_pet.name }\n/* variable "token" { default = "x" } */\n'
            'locals {\n  text = <<-EOT\n    password = "not-an-attribute"\n  EOT\n'
            '  joined = "${join("}", ["a", "b"])}"\n}\n'
        ),
        ["no failures"],
        True,
    ),
    (
        "a file that cannot be read is reported, not passed as empty",
        tree(CLEAN_ROOT, {"prod.tfvars": "db_password = \"caf\xe9\"\n"}),
        ["skipped, cannot be read as UTF-8: prod.tfvars"],
        False,
    ),
    (
        "vendored and generated trees are skipped",
        tree(CLEAN_ROOT, {"node_modules/x/main.tf": WHOLE_RESOURCE_OUTPUT}),
        ["no failures"],
        True,
    ),
]

CASES = STATE_CASES + SECRET_CASES + OUTPUT_CASES + PINNING_CASES + BOUNDARY_CASES + TEST_CASES + PARSER_CASES


def write(root: Path, files: dict[str, str]) -> None:
    """Write each file as UTF-8, except a `.tfvars` holding Latin-1, written as Latin-1 bytes."""
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        encoding = "latin-1" if rel.endswith(".tfvars") and "\xe9" in content else "utf-8"
        target.write_text(content, encoding=encoding)


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp), files)
        result = subprocess.run([sys.executable, str(HOOK), "."], cwd=tmp, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


def run_in_git(files: dict[str, str], ignored: str) -> tuple[int, str]:
    """Run the hook inside a fresh git repository whose .gitignore holds `ignored`."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root, tree(files, {".gitignore": ignored}))
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        result = subprocess.run([sys.executable, str(HOOK), "."], cwd=root, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, code: int, output: str) -> list[str]:
    """What went wrong with this case, or nothing."""
    wanted = "pass" if ok else "fail"
    found = [] if ok == (code == 0) else [f"expected the hook to {wanted}, it did the other"]
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    return found


def report_failure(name: str, problems: list[str], output: str) -> None:
    print(f"FAIL  {name}")
    for problem in problems:
        print(f"        {problem}")
    print("      --- hook output ---")
    for line in output.splitlines():
        print(f"      {line}")


def git_cases() -> list[tuple[str, list[str], bool, tuple[int, str]]]:
    """The cases that need a repository; empty where git is not installed."""
    if shutil.which("git") is None:
        print("skip  git cases: git is not installed")
        return []
    with_state = tree(CLEAN_ROOT, {"terraform.tfstate": "{}", ".terraform/providers/x": "x"})
    return [
        ("an ignored state file is not in the repository", ["no failures"], True,
         run_in_git(with_state, "*.tfstate\n.terraform/\n")),
        ("an unignored state file is about to be", ["state condition 1"], False,
         run_in_git(with_state, ".terraform/\n")),
    ]


def gate_case() -> tuple[str, list[str], bool, tuple[int, str]]:
    """#295/AC-6: the artifact gate passes on the repository that carries this plugin."""
    result = subprocess.run([sys.executable, str(GATE)], cwd=REPOSITORY, capture_output=True, text=True)
    return ("#295/AC-6 the artifact gate passes with this plugin in the catalogue", ["no failures"], True,
            (result.returncode, result.stdout + result.stderr))


def summarise(failed: int, total: int) -> int:
    print()
    if failed:
        print(f"{failed} of {total} cases failed.")
        return 1
    print(f"{total} cases passed.")
    return 0


def main() -> int:
    failed = 0
    results = [(name, expect, ok, run(files)) for name, files, expect, ok in CASES] + git_cases() + [gate_case()]
    for name, expect, ok, (code, output) in results:
        problems = problems_for(expect, ok, code, output)
        if problems:
            failed += 1
            report_failure(name, problems, output)
        else:
            print(f"ok    {name}")
    return summarise(failed, len(results))


if __name__ == "__main__":
    sys.exit(main())
