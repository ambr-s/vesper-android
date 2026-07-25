#!/usr/bin/env bash
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_WORK="$ROOT/work"
WORK="$TARGET_WORK"
UPSTREAM_REPOSITORY="${SIGNAL_REPOSITORY:-https://github.com/signalapp/Signal-Android.git}"
FORCE=false
CANDIDATE_TAG=""
STAGING_ROOT=""
RECOVERY_DIR=""

usage() {
  echo "Usage: $0 [--force] [--tag vX.Y.Z]" >&2
}

while (($#)); do
  case "$1" in
    --force)
      FORCE=true
      shift
      ;;
    --tag)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      CANDIDATE_TAG="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

PIN_LINE="$(<"$ROOT/upstream.pin")"
[[ "$PIN_LINE" =~ ^signal=(v[0-9]+\.[0-9]+\.[0-9]+)$ ]] || {
  echo "Invalid upstream.pin: expected signal=vX.Y.Z" >&2
  exit 1
}
PINNED_TAG="${BASH_REMATCH[1]}"
TAG="${CANDIDATE_TAG:-$PINNED_TAG}"
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "Invalid Signal tag: $TAG" >&2
  exit 1
}

if [[ -e "$TARGET_WORK" ]]; then
  if [[ "$FORCE" != true ]]; then
    echo "$TARGET_WORK already exists; preserve it or rerun with --force" >&2
    exit 1
  fi
  [[ "$(realpath -m -- "$TARGET_WORK")" == "$ROOT/work" ]] || {
    echo "Refusing to replace unexpected work path: $TARGET_WORK" >&2
    exit 1
  }

  if [[ -d "$TARGET_WORK/.git" ]]; then
    command -v rsync >/dev/null || {
      echo "rsync is required to preserve the existing checkout cache." >&2
      exit 1
    }

    STAGING_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/vesper-materialize.XXXXXXXX")"
    WORK="$STAGING_ROOT/work"
  else
    RECOVERY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/vesper-materialize-recovery.XXXXXXXX")"
    mv -- "$TARGET_WORK" "$RECOVERY_DIR/work"
    echo "Moved the previous non-Git work path to $RECOVERY_DIR/work"
  fi
fi

echo "Cloning Signal Android $TAG..."
CLONE_ARGS=(--single-branch --branch "$TAG")
if [[ "$UPSTREAM_REPOSITORY" == *"://"* || "$UPSTREAM_REPOSITORY" == git@* ]]; then
  CLONE_ARGS+=(--filter=blob:none)
fi
git clone "${CLONE_ARGS[@]}" "$UPSTREAM_REPOSITORY" "$WORK"

git -C "$WORK" config --local user.name "Vesper Materializer"
git -C "$WORK" config --local user.email "vesper-materializer@users.noreply.github.com"
git -C "$WORK" config --local commit.gpgsign false
git -C "$WORK" switch -c "vesper/${TAG#v}"
MATERIALIZE_DATE="$(git -C "$WORK" show -s --format=%aI HEAD)"

python3 "$ROOT/tools/transform.py" "$WORK"
git -C "$WORK" add -A
GIT_AUTHOR_DATE="$MATERIALIZE_DATE" GIT_COMMITTER_DATE="$MATERIALIZE_DATE" \
  git -C "$WORK" -c commit.gpgsign=false commit -m "Vesper branding transforms"

if [[ -n "$(find "$ROOT/overlay" -type f -print -quit)" ]]; then
  cp -a "$ROOT/overlay/." "$WORK/"
  git -C "$WORK" add -A
  if ! git -C "$WORK" diff --cached --quiet; then
    GIT_AUTHOR_DATE="$MATERIALIZE_DATE" GIT_COMMITTER_DATE="$MATERIALIZE_DATE" \
      git -C "$WORK" -c commit.gpgsign=false commit -m "Vesper owned overlays"
  fi
fi

shopt -s nullglob
PATCHES=("$ROOT"/patches/*.patch)
if ((${#PATCHES[@]})); then
  git -C "$WORK" -c commit.gpgsign=false am --3way --committer-date-is-author-date "${PATCHES[@]}"
fi

if [[ -n "$STAGING_ROOT" ]]; then
  EXISTING_HEAD="$(git -C "$TARGET_WORK" rev-parse HEAD)"
  GENERATED_HEAD="$(git -C "$WORK" rev-parse HEAD)"
  RECOVERY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/vesper-materialize-recovery.XXXXXXXX")"
  mkdir "$RECOVERY_DIR/previous-files"

  rsync \
    --archive \
    --checksum \
    --delete \
    --no-times \
    --omit-dir-times \
    --backup \
    --backup-dir="$RECOVERY_DIR/previous-files" \
    --exclude='/.git/' \
    --exclude='.gradle/' \
    --exclude='.kotlin/' \
    --exclude='.idea/' \
    --exclude='.cxx/' \
    --exclude='.externalNativeBuild/' \
    --exclude='build/' \
    --exclude='local.properties' \
    "$WORK/" "$TARGET_WORK/"

  if [[ "$GENERATED_HEAD" != "$EXISTING_HEAD" ]]; then
    mv -- "$TARGET_WORK/.git" "$RECOVERY_DIR/git"
    if ! mv -- "$WORK/.git" "$TARGET_WORK/.git"; then
      mv -- "$RECOVERY_DIR/git" "$TARGET_WORK/.git"
      echo "Failed to install generated Git metadata; restored the previous metadata." >&2
      exit 1
    fi
  fi

  STAGING_REAL="$(realpath -m -- "$STAGING_ROOT")"
  TEMP_REAL="$(realpath -m -- "${TMPDIR:-/tmp}")"
  [[ -d "$STAGING_REAL" && "$STAGING_REAL" == "$TEMP_REAL"/vesper-materialize.* ]] || {
    echo "Refusing to clean unexpected staging path: $STAGING_ROOT" >&2
    exit 1
  }
  rm -rf -- "$STAGING_REAL"

  WORK="$TARGET_WORK"
  echo "Updated work/ in place. Unchanged source times and local build caches were kept."
  if [[ -z "$(find "$RECOVERY_DIR/previous-files" -mindepth 1 -print -quit)" && ! -e "$RECOVERY_DIR/git" ]]; then
    rmdir "$RECOVERY_DIR/previous-files" "$RECOVERY_DIR"
  else
    echo "Previous Git metadata and replaced files can be recovered from $RECOVERY_DIR"
  fi
fi

git -C "$WORK" status --short
echo "Materialised Vesper from Signal $TAG at $WORK"
