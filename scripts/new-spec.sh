#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "usage: $0 kebab-case-feature-name" >&2
  exit 2
fi

feature_name="$1"
latest="$(find specs -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sed -n 's/^\([0-9][0-9][0-9]\)-.*/\1/p' | sort -n | tail -1)"
next_number="$(printf '%03d' "$((10#${latest:-000} + 1))")"
destination="specs/${next_number}-${feature_name}"

if [[ -e "$destination" ]]; then
  echo "spec already exists: $destination" >&2
  exit 1
fi

cp -R specs/_template "$destination"
today="$(date +%F)"
find "$destination" -type f -exec sed -i \
  -e "s/NNN: Feature title/${next_number}: ${feature_name}/g" \
  -e "s/Feature title/${feature_name}/g" \
  -e "s/YYYY-MM-DD/${today}/g" {} +

echo "$destination"
