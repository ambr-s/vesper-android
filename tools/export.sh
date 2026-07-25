#!/usr/bin/env bash
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/work"

[[ -d "$WORK/.git" ]] || {
  echo "No materialised work/ checkout. Run ./tools/materialize.sh first." >&2
  exit 1
}

if [[ -n "$(git -C "$WORK" status --porcelain)" ]]; then
  echo "work/ has uncommitted changes; commit them before export." >&2
  exit 1
fi

BRANDING_COMMIT="$(git -C "$WORK" log --format=%H --grep='^Vesper branding transforms$' -n 1)"
OVERLAY_COMMIT="$(git -C "$WORK" log --format=%H --grep='^Vesper owned overlays$' -n 1)"
if [[ -z "$BRANDING_COMMIT" || -z "$OVERLAY_COMMIT" ]]; then
  echo "Expected branding and overlay materialisation commits." >&2
  exit 1
fi

git -C "$WORK" merge-base --is-ancestor "$BRANDING_COMMIT" "$OVERLAY_COMMIT" || {
  echo "Overlay commit does not follow the branding commit." >&2
  exit 1
}
git -C "$WORK" merge-base --is-ancestor "$OVERLAY_COMMIT" HEAD || {
  echo "Overlay commit is not part of the current work/ branch." >&2
  exit 1
}

mapfile -t FEATURE_COMMITS < <(git -C "$WORK" rev-list --reverse "$OVERLAY_COMMIT..HEAD")
if ((${#FEATURE_COMMITS[@]} == 0)); then
  echo "No feature commits to export." >&2
  exit 0
fi

OVERLAY_EXCLUDES=()
while IFS= read -r -d '' overlay_file; do
  relative_path="${overlay_file#"$ROOT/overlay/"}"
  source_file="$WORK/$relative_path"
  [[ -f "$source_file" ]] || {
    echo "Owned overlay is missing from work/: $relative_path" >&2
    exit 1
  }
  cp -- "$source_file" "$overlay_file"
  OVERLAY_EXCLUDES+=(":(exclude)$relative_path")
done < <(find "$ROOT/overlay" -type f -print0)

mkdir -p "$ROOT/patches"
find "$ROOT/patches" -maxdepth 1 -type f -name '*.patch' -delete

echo "Exporting overlay files and feature commits."
echo "Overlay files live in overlay/. Patches come from commits after the two"
echo "materialisation commits."
echo
git -C "$WORK" format-patch \
  --no-signature \
  --output-directory "$ROOT/patches" \
  "$OVERLAY_COMMIT..HEAD" \
  -- . "${OVERLAY_EXCLUDES[@]}"
