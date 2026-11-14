#!/usr/bin/env bash
# #295: init -backend=false and validate in every directory with .tf files under [root]; stops at the first failure.
set -euo pipefail
root="${1:-.}"
find "$root" -name '*.tf' -not -path '*/.terraform/*' -print0 \
  | xargs -0 -n1 dirname | sort -u | while IFS= read -r dir; do
    echo "== $dir"
    terraform -chdir="$dir" init -backend=false -input=false >/dev/null
    terraform -chdir="$dir" validate
  done
