#!/usr/bin/env python3
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Integration check: clean replay matches work/ and re-export preserves bytes.

Run after committing source changes and exporting. Uses a disposable wrapper so
it never replaces the build worktree or interacts with its Gradle caches.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def run(*args, cwd=None, env=None):
    return subprocess.check_output(args, cwd=cwd, env=env, text=True).strip()


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ['patches', 'overlay']
            for p in (root / directory).rglob('*') if p.is_file()}


def main():
    root = Path(__file__).resolve().parents[1]
    work = root / 'work'
    if run('git', 'status', '--porcelain', cwd=work):
        raise RuntimeError('Commit source changes before verifying replay')
    branding = run('git', 'log', '--format=%H', '--grep=^Vesper branding transforms$', '-n', '1', cwd=work)
    tag = run('git', 'describe', '--tags', '--exact-match', branding + '^', cwd=work)
    tree = run('git', 'rev-parse', 'HEAD^{tree}', cwd=work)
    expected = snapshot(root)
    with tempfile.TemporaryDirectory(prefix='vesper-roundtrip-') as directory:
        wrapper = Path(directory)
        for name in ['tools', 'branding', 'overlay', 'patches']:
            shutil.copytree(root / name, wrapper / name)
        shutil.copy2(root / 'upstream.pin', wrapper / 'upstream.pin')
        env = dict(os.environ, SIGNAL_REPOSITORY=str(work))
        subprocess.run([str(wrapper / 'tools/materialize.sh'), '--tag', tag], env=env, check=True)
        replay = wrapper / 'work'
        assert run('git', 'rev-parse', 'HEAD^{tree}', cwd=replay) == tree
        assert not run('git', 'status', '--porcelain', cwd=replay)
        subprocess.run([str(wrapper / 'tools/export.sh')], check=True)
        assert snapshot(wrapper) == expected, 'Patch/overlay inventory or bytes changed on second export'
    print(f'PASS {tag}: exact tree {tree}; clean replay; byte-identical second export')


if __name__ == '__main__':
    main()
