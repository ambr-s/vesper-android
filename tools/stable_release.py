#!/usr/bin/env python3
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate GitHub's stable release metadata; never infer stability from a tag."""
import json
import re
import sys


def stable_tag(release, pinned=None):
    if release.get('prerelease') is not False or release.get('draft') is not False:
        raise ValueError('Signal release is not explicitly stable and published')
    tag = release.get('tag_name', '')
    if not isinstance(tag, str) or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag):
        raise ValueError('Invalid stable Signal release tag')
    if pinned is not None:
        if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', pinned):
            raise ValueError('Invalid published Signal pin')
        if tuple(map(int, tag[1:].split('.'))) < tuple(map(int, pinned[1:].split('.'))):
            raise ValueError(f'Refusing automatic downgrade from published {pinned} to stable {tag}; retain the published pin and update channel until a safe migration is qualified')
    return tag


if __name__ == '__main__':
    try:
        print(stable_tag(json.load(sys.stdin), sys.argv[1] if len(sys.argv) > 1 else None))
    except (ValueError, TypeError, AttributeError) as error:
        sys.exit(str(error))
