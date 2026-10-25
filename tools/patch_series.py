#!/usr/bin/env python3
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Keep the published pre-extraction patch series while qualifying Signal 8.33."""
import re
import sys
from pathlib import Path


def patch_directory(root: Path, tag: str) -> Path:
    match = re.fullmatch(r'v([0-9]+)\.([0-9]+)\.([0-9]+)', tag)
    if match is None:
        raise ValueError(f'Invalid Signal release tag: {tag!r}')
    version = tuple(map(int, match.groups()))
    return root / ('patches/signal-8.33' if version >= (8, 33, 0) else 'patches')


if __name__ == '__main__':
    print(patch_directory(Path(sys.argv[1]), sys.argv[2]))
