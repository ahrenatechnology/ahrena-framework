#!/usr/bin/env bash
# #295: run init, validate and, where a module has tests, terraform test in every
# directory below the root that holds .tf files. Stops at the first failure.
# Usage: validate-each.sh [root]
set -euo pipefail
root="${1:-.}"
find "$root" -name '*.tf' -not -path '*/.terraform/*' -print0 \
  | xargs -0 -n1 dirname | sort -u | while IFS= read -r dir; do
    echo "== $dir"
    terraform -chdir="$dir" init -backend=false -input=false >/dev/null
    terraform -chdir="$dir" validate
    if compgen -G "$dir/tests/*.tftest.hcl" >/dev/null || compgen -G "$dir/*.tftest.hcl" >/dev/null; then
      terraform -chdir="$dir" test
    fi
  done
