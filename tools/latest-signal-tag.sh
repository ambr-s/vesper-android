#!/usr/bin/env bash
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

# Numeric tags also identify Signal betas. GitHub's published release metadata
# is authoritative; never fall back to the highest tag on API failure.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
curl --fail --silent --show-error --location --retry 3 \
  --connect-timeout 15 --max-time 60 \
  -H 'Accept: application/vnd.github+json' \
  https://api.github.com/repos/signalapp/Signal-Android/releases/latest |
  python3 "$ROOT/tools/stable_release.py" "$@"
