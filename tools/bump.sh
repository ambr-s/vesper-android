#!/usr/bin/env bash
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -eq 2 && "$1" == "--accept" ]]; then
  TAG="$2"
  [[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    echo "Invalid Signal tag: $TAG" >&2
    exit 2
  }
  [[ -d "$ROOT/work/.git" ]] || {
    echo "No materialised work/ checkout to accept." >&2
    exit 1
  }
  [[ -z "$(git -C "$ROOT/work" status --porcelain)" ]] || {
    echo "work/ has uncommitted changes." >&2
    exit 1
  }
  git -C "$ROOT/work" rev-parse --verify --quiet "$TAG^{commit}" >/dev/null || {
    echo "work/ does not contain Signal tag $TAG." >&2
    exit 1
  }
  git -C "$ROOT/work" merge-base --is-ancestor "$TAG" HEAD || {
    echo "$TAG is not the base of the materialised work/ branch." >&2
    exit 1
  }
  printf 'signal=%s\n' "$TAG" > "$ROOT/upstream.pin"
  echo "Advanced upstream.pin to $TAG."
  exit 0
fi

if [[ $# -ne 1 || ! "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Usage: $0 vX.Y.Z" >&2
  echo "       $0 --accept vX.Y.Z" >&2
  exit 2
fi

TAG="$1"

if [[ -e "$ROOT/work" ]]; then
  echo "Preserving existing work/; move it aside after exporting or resolving it." >&2
  echo "To test the candidate in a clean tree, run:" >&2
  echo "  ./tools/materialize.sh --tag $TAG" >&2
  exit 1
fi

"$ROOT/tools/materialize.sh" --tag "$TAG"

echo
echo "Candidate $TAG materialised successfully."
echo "Run the required build checks in work/, then advance the pin with:"
echo "  ./tools/bump.sh --accept $TAG"
