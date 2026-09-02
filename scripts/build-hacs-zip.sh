#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
component_dir="$repo_root/custom_components/ynblue"
output_arg="${1:-dist/ynblue.zip}"

case "$output_arg" in
  /*) output_file="$output_arg" ;;
  *) output_file="$repo_root/$output_arg" ;;
esac

if [[ ! -f "$component_dir/manifest.json" || ! -f "$component_dir/__init__.py" ]]; then
  echo "YnBlue component files are missing from $component_dir" >&2
  exit 1
fi

output_dir="$(dirname -- "$output_file")"
mkdir -p -- "$output_dir"

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/ynblue-hacs.XXXXXX")"
temp_archive="$temp_dir/ynblue.zip"

cleanup() {
  rm -rf -- "$temp_dir"
}
trap cleanup EXIT

(
  cd -- "$component_dir"
  zip -q -r "$temp_archive" . \
    -x '.DS_Store' '*/.DS_Store' '__pycache__/*' '*/__pycache__/*' '*.pyc' '*.pyo'
)

archive_entries="$(unzip -Z1 "$temp_archive")"

if ! grep -Fxq 'manifest.json' <<<"$archive_entries"; then
  echo "Generated archive does not contain manifest.json at its root" >&2
  exit 1
fi

if ! grep -Fxq '__init__.py' <<<"$archive_entries"; then
  echo "Generated archive does not contain __init__.py at its root" >&2
  exit 1
fi

if grep -Eq '(^/|(^|/)\.\.(/|$)|^custom_components/)' <<<"$archive_entries"; then
  echo "Generated archive contains an unsafe path or an unexpected wrapper directory" >&2
  exit 1
fi

mv -f -- "$temp_archive" "$output_file"
printf 'Created %s\n' "$output_file"
