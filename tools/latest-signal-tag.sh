#!/usr/bin/env bash
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

set -euo pipefail

UPSTREAM_REPOSITORY="${SIGNAL_REPOSITORY:-https://github.com/signalapp/Signal-Android.git}"

LATEST_TAG="$(
  git ls-remote --tags --refs "$UPSTREAM_REPOSITORY" 'v*' |
    sed 's#^.*refs/tags/##' |
    grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' |
    sort -V |
    tail -n 1
)"

[[ -n "$LATEST_TAG" ]] || {
  echo "No stable Signal release tags found at $UPSTREAM_REPOSITORY." >&2
  exit 1
}

printf '%s\n' "$LATEST_TAG"
