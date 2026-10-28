#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
import unittest
import json
import os
from pathlib import Path
import subprocess
import tempfile
from stable_release import stable_tag

class StableReleaseTest(unittest.TestCase):
    def test_rejects_numeric_prerelease(self):
        with self.assertRaises(ValueError):
            stable_tag({'tag_name': 'v8.33.2', 'prerelease': True, 'draft': False})

    def test_accepts_stable(self):
        self.assertEqual(stable_tag({'tag_name': 'v8.32.3', 'prerelease': False, 'draft': False}), 'v8.32.3')

    def test_rejects_downgrade(self):
        with self.assertRaisesRegex(ValueError, 'Refusing automatic downgrade'):
            stable_tag({'tag_name': 'v8.32.3', 'prerelease': False, 'draft': False}, 'v8.33.2')

    def test_accepts_equal_or_newer(self):
        release = {'tag_name': 'v8.33.3', 'prerelease': False, 'draft': False}
        for pin in ['v8.33.3', 'v8.33.2', 'v8.9.9']:
            self.assertEqual(stable_tag(release, pin), 'v8.33.3')

    def test_fails_closed(self):
        for release in [{}, {'tag_name': 'v8.33.2'}, {'tag_name': 'v8.33.2', 'draft': True, 'prerelease': False}, {'tag_name': 'v8.33.2-beta', 'draft': False, 'prerelease': False}]:
            with self.subTest(release=release), self.assertRaises(ValueError):
                stable_tag(release)

    def test_shell_selects_metadata_not_highest_tag_and_fails_closed(self):
        root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'curl').write_text('#!/bin/sh\nprintf "%s" "$RELEASE_JSON"\nexit "${CURL_EXIT:-0}"\n')
            (folder / 'git').write_text('#!/bin/sh\nprintf "abc refs/tags/v8.33.2\\n"\n')
            for name in ['curl', 'git']:
                (folder / name).chmod(0o755)
            env = dict(os.environ, PATH=temp + os.pathsep + os.environ['PATH'], RELEASE_JSON=json.dumps({'tag_name': 'v8.32.3', 'prerelease': False, 'draft': False}))
            result = subprocess.run([str(root / 'latest-signal-tag.sh')], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'v8.32.3')
            result = subprocess.run([str(root / 'latest-signal-tag.sh'), 'v8.33.2'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refusing automatic downgrade', result.stderr)
            env.update(CURL_EXIT='22', RELEASE_JSON='')
            result = subprocess.run([str(root / 'latest-signal-tag.sh')], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')

if __name__ == '__main__':
    unittest.main()
