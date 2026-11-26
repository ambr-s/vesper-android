# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from pathlib import Path
from patch_series import patch_directory

class PatchSeriesTest(unittest.TestCase):
    def test_known_good_uses_original_series(self):
        self.assertEqual(patch_directory(Path('/repo'), 'v8.32.2'), Path('/repo/patches'))

    def test_extracted_settings_uses_rebased_series(self):
        for tag in ['v8.33.0', 'v8.33.1', 'v8.33.2']:
            self.assertEqual(patch_directory(Path('/repo'), tag), Path('/repo/patches/signal-8.33'))

    def test_rebased_series_retains_original_mail_provenance(self):
        from export_patches import patch_mail, patch_subject
        root = Path(__file__).resolve().parents[1]
        originals = sorted((root / 'patches').glob('*.patch'))
        rebased = sorted((root / 'patches/signal-8.33').glob('*.patch'))
        self.assertEqual(len(originals), 29)
        self.assertGreaterEqual(len(rebased), len(originals))
        for old, new in zip(originals, rebased):
            with self.subTest(patch=old.name):
                a, d, _, body = patch_mail(old.read_bytes())
                na, nd, _, nbody = patch_mail(new.read_bytes())
                self.assertEqual((a, d, body), (na, nd, nbody))
                self.assertEqual(patch_subject(old.read_bytes()), patch_subject(new.read_bytes()))

    def test_834_series_retains_833_mail_provenance(self):
        from export_patches import patch_mail, patch_subject
        root = Path(__file__).resolve().parents[1]
        originals = sorted((root / 'patches/signal-8.33').glob('*.patch'))
        rebased = sorted((root / 'patches/signal-8.34').glob('*.patch'))
        self.assertEqual(len(originals), 32)
        self.assertGreaterEqual(len(rebased), len(originals))
        for old, new in zip(originals, rebased):
            with self.subTest(patch=old.name):
                a, d, _, body = patch_mail(old.read_bytes())
                na, nd, _, nbody = patch_mail(new.read_bytes())
                self.assertEqual((a, d, body), (na, nd, nbody))
                self.assertEqual(patch_subject(old.read_bytes()), patch_subject(new.read_bytes()))

    def test_navigation_extraction_uses_834_series(self):
        for tag in ['v8.34.0', 'v8.34.2']:
            self.assertEqual(patch_directory(Path('/repo'), tag), Path('/repo/patches/signal-8.34'))

    def test_storage_and_remote_config_extraction_uses_835_series(self):
        for tag in ['v8.35.0', 'v8.35.2']:
            self.assertEqual(patch_directory(Path('/repo'), tag), Path('/repo/patches/signal-8.35'))

    def test_835_series_retains_834_mail_provenance(self):
        from export_patches import patch_mail, patch_subject
        root = Path(__file__).resolve().parents[1]
        originals = sorted((root / 'patches/signal-8.34').glob('*.patch'))
        rebased = sorted((root / 'patches/signal-8.35').glob('*.patch'))
        self.assertEqual(len(originals), 34)
        self.assertGreaterEqual(len(rebased), len(originals))
        for old, new in zip(originals, rebased):
            with self.subTest(patch=old.name):
                a, d, _, body = patch_mail(old.read_bytes())
                na, nd, _, nbody = patch_mail(new.read_bytes())
                self.assertEqual((a, d, body), (na, nd, nbody))
                self.assertEqual(patch_subject(old.read_bytes()), patch_subject(new.read_bytes()))

    def test_help_entry_extraction_preserves_series_provenance(self):
        from export_patches import patch_mail, patch_subject
        root = Path(__file__).resolve().parents[1]
        candidate = patch_directory(root, 'v8.36.3')
        self.assertEqual(candidate, root / 'patches/signal-8.36')
        previous = sorted(patch_directory(root, 'v8.35.2').glob('*.patch'))
        self.assertEqual([p.name for p in previous], sorted(p.name for p in candidate.glob('*.patch')))
        for original in previous:
            with self.subTest(patch=original.name):
                old, new = original.read_bytes(), (candidate / original.name).read_bytes()
                self.assertEqual(patch_subject(old), patch_subject(new))
                self.assertEqual(patch_mail(old)[:2], patch_mail(new)[:2])
                self.assertEqual(patch_mail(old)[3], patch_mail(new)[3])

    def test_837_preserves_published_feature_series_provenance(self):
        from export_patches import patch_mail, patch_subject
        root = Path(__file__).resolve().parents[1]
        previous = patch_directory(root, 'v8.36.3')
        candidate = patch_directory(root, 'v8.37.3')
        self.assertEqual(candidate, root / 'patches/signal-8.37')
        originals = sorted(previous.glob('*.patch'))
        self.assertEqual([p.name for p in originals], sorted(p.name for p in candidate.glob('*.patch')))
        for original in originals:
            with self.subTest(patch=original.name):
                old, new = original.read_bytes(), (candidate / original.name).read_bytes()
                self.assertEqual(patch_subject(old), patch_subject(new))
                self.assertEqual(patch_mail(old)[:2], patch_mail(new)[:2])
                self.assertEqual(patch_mail(old)[3], patch_mail(new)[3])

    def test_invalid_versions_fail_closed(self):
        for tag in ['8.33.1', 'v8.33.1-rc', '../patches', 'v8.33', 'v8.33.1\n']:
            with self.assertRaises(ValueError):
                patch_directory(Path('/repo'), tag)

if __name__ == '__main__':
    unittest.main()
