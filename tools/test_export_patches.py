# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("export_patches.py")


def run(*args: str, cwd: Path) -> str:
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_patches", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StablePatchExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.repository = self.root / "work"
        self.output = self.root / "patches"
        self.repository.mkdir()
        run("git", "init", "-q", cwd=self.repository)
        run("git", "config", "user.name", "Vesper Test", cwd=self.repository)
        run("git", "config", "user.email", "vesper-test@example.invalid", cwd=self.repository)

        (self.repository / "feature.txt").write_text(
            "zero\none\ntwo\nthree\nalpha\nbeta\ngamma\nseven\neight\nnine\n"
        )
        run("git", "add", "feature.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "upstream base", cwd=self.repository)
        self.base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()

        (self.repository / "feature.txt").write_text(
            "zero\none\ntwo\nthree\nalpha\nVESPER\ngamma\nseven\neight\nnine\n"
        )
        run("git", "commit", "-qam", "feat: add Vesper behaviour", cwd=self.repository)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_preserves_existing_patch_when_it_reproduces_rebased_commit(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch = next(self.output.glob("*.patch"))
        original_bytes = patch.read_bytes()
        feature_author_date = run(
            "git", "show", "-s", "--format=%aI", "HEAD", cwd=self.repository
        ).strip()

        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "feature.txt").write_text(
            "new upstream line\nzero\none\ntwo\nthree\nalpha\nbeta\ngamma\nseven\neight\nnine\n"
        )
        run("git", "commit", "-qam", "upstream moves the hunk", cwd=self.repository)
        rebased_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()
        (self.repository / "feature.txt").write_text(
            "new upstream line\nzero\none\ntwo\nthree\nalpha\nVESPER\ngamma\nseven\neight\nnine\n"
        )
        run(
            "git",
            "commit",
            "-qam",
            "feat: add Vesper behaviour",
            f"--date={feature_author_date}",
            cwd=self.repository,
        )

        exporter.export_patch_series(self.repository, self.output, rebased_base, [])

        self.assertEqual(original_bytes, next(self.output.glob("*.patch")).read_bytes())

    def test_regenerates_patch_when_feature_effect_changes(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch = next(self.output.glob("*.patch"))
        original_bytes = patch.read_bytes()

        (self.repository / "feature.txt").write_text(
            "zero\none\ntwo\nthree\nalpha\nVESPER UPDATED\ngamma\nseven\neight\nnine\n"
        )
        run("git", "commit", "-qam", "fix: update Vesper behaviour", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patches = sorted(self.output.glob("*.patch"))
        self.assertEqual(2, len(patches))
        retained_bytes = patches[0].read_bytes()
        self.assertNotEqual(original_bytes, retained_bytes)
        self.assertIn(b"Subject: [PATCH 1/2] feat: add Vesper behaviour", retained_bytes)
        self.assertIn(b"+VESPER", retained_bytes)
        self.assertNotIn(b"VESPER UPDATED", retained_bytes)
        self.assertIn(b"VESPER UPDATED", patches[1].read_bytes())

    def test_binary_patch_is_exported_and_reused_when_still_exact(self) -> None:
        exporter = load_exporter()
        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "asset.bin").write_bytes(b"\x00vesper\xff")
        run("git", "add", "asset.bin", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add binary asset", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        original_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertIn(b"GIT binary patch", original_bytes)
        feature_author_date = run(
            "git", "show", "-s", "--format=%aI", "HEAD", cwd=self.repository
        ).strip()

        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "upstream.txt").write_text("new upstream file\n")
        run("git", "add", "upstream.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "upstream adds a file", cwd=self.repository)
        rebased_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()
        (self.repository / "asset.bin").write_bytes(b"\x00vesper\xff")
        run("git", "add", "asset.bin", cwd=self.repository)
        run(
            "git",
            "commit",
            "-q",
            "-m",
            "feat: add binary asset",
            f"--date={feature_author_date}",
            cwd=self.repository,
        )

        exporter.export_patch_series(self.repository, self.output, rebased_base, [])

        self.assertEqual(original_bytes, next(self.output.glob("*.patch")).read_bytes())

    def test_clears_stale_patches_for_empty_series(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        self.assertTrue(list(self.output.glob("*.patch")))

        run("git", "checkout", "-q", self.base, cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, self.base, [])

        self.assertEqual([], list(self.output.glob("*.patch")))

    def test_rejects_old_patch_that_applies_but_produces_wrong_tree(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        original_bytes = next(self.output.glob("*.patch")).read_bytes()

        (self.repository / "feature.txt").write_text(
            "zero\none\ntwo\nthree\nalpha\nVESPER UPDATED\ngamma\nseven\neight\nnine\n"
        )
        run("git", "commit", "-qam", "feat: add Vesper behaviour", "--amend", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, self.base, [])

        updated_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotEqual(original_bytes, updated_bytes)
        self.assertIn(b"VESPER UPDATED", updated_bytes)

    def test_ignores_commits_that_only_change_excluded_overlay_files(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        self.assertTrue(list(self.output.glob("*.patch")))

        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "owned.txt").write_text("updated overlay\n")
        run("git", "add", "owned.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: update owned overlay", cwd=self.repository)

        exporter.export_patch_series(
            self.repository, self.output, self.base, ["owned.txt"]
        )

        self.assertEqual([], list(self.output.glob("*.patch")))

    def test_regenerates_when_provenance_changes_without_tree_change(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        original_bytes = next(self.output.glob("*.patch")).read_bytes()

        run(
            "git",
            "commit",
            "--amend",
            "-q",
            "-m",
            "feat: add Vesper behaviour",
            "-m",
            "Updated provenance and attribution.",
            cwd=self.repository,
        )
        exporter.export_patch_series(self.repository, self.output, self.base, [])

        updated_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotEqual(original_bytes, updated_bytes)
        self.assertIn(b"Updated provenance and attribution.", updated_bytes)

    def test_disables_configured_cover_letters(self) -> None:
        exporter = load_exporter()
        (self.repository / "second.txt").write_text("second feature\n")
        run("git", "add", "second.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add second feature", cwd=self.repository)
        run("git", "config", "format.coverLetter", "auto", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patches = sorted(self.output.glob("*.patch"))
        self.assertEqual(2, len(patches))
        self.assertFalse(any("cover-letter" in patch.name for patch in patches))

    def test_disables_configured_mime_attachments(self) -> None:
        exporter = load_exporter()
        run("git", "config", "format.attach", "true", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotIn(b"Content-Type: multipart/mixed", patch)
        self.assertIn(b"diff --git a/feature.txt b/feature.txt", patch)

    def test_disables_configured_automatic_base_selection(self) -> None:
        exporter = load_exporter()
        run("git", "config", "format.useAutoBase", "true", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotIn(b"base-commit:", patch)
        self.assertIn(b"diff --git a/feature.txt b/feature.txt", patch)

    def test_forces_default_diff_prefixes(self) -> None:
        exporter = load_exporter()
        run("git", "config", "format.noprefix", "true", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertIn(b"diff --git a/feature.txt b/feature.txt", patch)
        self.assertIn(b"--- a/feature.txt", patch)
        self.assertIn(b"+++ b/feature.txt", patch)

    def test_forces_patch_filename_suffix(self) -> None:
        exporter = load_exporter()
        run("git", "config", "format.suffix", ".mbox", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patches = sorted(self.output.glob("*.patch"))
        self.assertEqual(1, len(patches))
        self.assertEqual([], list(self.output.glob("*.mbox")))

    def test_disables_configured_from_rewriting(self) -> None:
        exporter = load_exporter()
        run("git", "config", "user.name", "Different Exporter", cwd=self.repository)
        run("git", "config", "user.email", "exporter@example.invalid", cwd=self.repository)
        run("git", "config", "format.from", "true", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertIn(b"From: Vesper Test <vesper-test@example.invalid>", patch)
        self.assertNotIn(b"From: Different Exporter <exporter@example.invalid>", patch)

    def test_disables_configured_signoff_injection(self) -> None:
        exporter = load_exporter()
        run("git", "config", "format.signOff", "true", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotIn(b"Signed-off-by: Vesper Test <vesper-test@example.invalid>", patch)

    def test_disables_configured_extra_mail_headers(self) -> None:
        exporter = load_exporter()
        run("git", "config", "format.headers", "Subject: Injected", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertEqual(1, patch.count(b"\nSubject:"))
        self.assertNotIn(b"Subject: Injected", patch)

    def test_replaces_all_retained_mail_headers(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch_path = next(self.output.glob("*.patch"))
        patch = patch_path.read_bytes()
        patch_path.write_bytes(
            patch.replace(
                b"From: Vesper Test <vesper-test@example.invalid>\n",
                b"From: Vesper Test <vesper-test@example.invalid>\n"
                b"From: Evil <evil@example.invalid>\n",
                1,
            )
        )

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        retained = next(self.output.glob("*.patch")).read_bytes()
        self.assertEqual(1, retained.count(b"\nFrom:"))
        self.assertNotIn(b"Evil <evil@example.invalid>", retained)

    def test_disables_configured_threading(self) -> None:
        exporter = load_exporter()
        (self.repository / "second.txt").write_text("second feature\n")
        run("git", "add", "second.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add second feature", cwd=self.repository)
        run("git", "config", "format.thread", "deep", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        for patch_path in self.output.glob("*.patch"):
            patch = patch_path.read_bytes()
            self.assertNotIn(b"Message-ID:", patch)
            self.assertNotIn(b"In-Reply-To:", patch)
            self.assertNotIn(b"References:", patch)

    def test_forces_canonical_numbered_patch_subjects(self) -> None:
        exporter = load_exporter()
        (self.repository / "second.txt").write_text("second feature\n")
        run("git", "add", "second.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add second feature", cwd=self.repository)
        run("git", "config", "format.numbered", "false", cwd=self.repository)
        run("git", "config", "format.subjectPrefix", "VESPER", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patches = sorted(self.output.glob("*.patch"))
        self.assertIn(b"Subject: [PATCH 1/2] feat: add Vesper behaviour", patches[0].read_bytes())
        self.assertIn(b"Subject: [PATCH 2/2] feat: add second feature", patches[1].read_bytes())

    def test_duplicate_subjects_are_mapped_in_commit_order(self) -> None:
        exporter = load_exporter()
        (self.repository / "second.txt").write_text("second feature\n")
        run("git", "add", "second.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add Vesper behaviour", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patches = sorted(self.output.glob("*.patch"))
        self.assertEqual(2, len(patches))
        self.assertIn(b"feature.txt", patches[0].read_bytes())
        self.assertIn(b"second.txt", patches[1].read_bytes())

    def test_regenerates_an_unapplicable_retained_candidate(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch = next(self.output.glob("*.patch"))
        canonical = patch.read_bytes()
        broken = canonical.replace(b"--- a/feature.txt", b"--- a/missing.txt")
        patch.write_bytes(broken)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        self.assertEqual(canonical, next(self.output.glob("*.patch")).read_bytes())

    def test_regenerates_when_retained_candidate_is_malformed(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch = next(self.output.glob("*.patch"))
        canonical = patch.read_bytes()
        patch.write_bytes(b"truncated stale patch\n")

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        self.assertEqual(canonical, next(self.output.glob("*.patch")).read_bytes())

    def test_regenerates_provenance_matching_candidate_without_diff(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch = next(self.output.glob("*.patch"))
        canonical = patch.read_bytes()
        diff_start = canonical.find(b"\ndiff --git ")
        self.assertGreater(diff_start, 0)
        patch.write_bytes(canonical[: diff_start + 1])

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        self.assertEqual(canonical, next(self.output.glob("*.patch")).read_bytes())

    def test_exports_mixed_commit_using_non_excluded_tree(self) -> None:
        exporter = load_exporter()
        (self.repository / "owned.txt").write_text("owned overlay\n")
        run("git", "add", "owned.txt", cwd=self.repository)
        run("git", "commit", "--amend", "-q", "--no-edit", cwd=self.repository)

        exporter.export_patch_series(
            self.repository, self.output, self.base, ["owned.txt"]
        )

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertIn(b"feature.txt", patch)
        self.assertNotIn(b"owned.txt", patch)

    def test_exports_force_added_ignored_file(self) -> None:
        exporter = load_exporter()
        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / ".gitignore").write_text("*.ignored\n")
        run("git", "add", ".gitignore", cwd=self.repository)
        run("git", "commit", "-q", "-m", "upstream ignores fixture", cwd=self.repository)
        ignored_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()
        (self.repository / "feature.ignored").write_text("tracked feature\n")
        run("git", "add", "-f", "feature.ignored", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add ignored file", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, ignored_base, [])

        self.assertIn(
            b"feature.ignored", next(self.output.glob("*.patch")).read_bytes()
        )

    def test_regenerates_retained_candidate_with_lowercase_subject_header(self) -> None:
        exporter = load_exporter()
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        patch = next(self.output.glob("*.patch"))
        canonical = patch.read_bytes()
        patch.write_bytes(canonical.replace(b"\nSubject:", b"\nsubject:", 1))

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        self.assertEqual(canonical, next(self.output.glob("*.patch")).read_bytes())

    def test_rejects_retained_patch_when_only_a_later_file_suffix_matches(self) -> None:
        exporter = load_exporter()
        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "a.txt").write_text("base a\n")
        (self.repository / "b.txt").write_text("base b\n")
        run("git", "add", "a.txt", "b.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "upstream adds files", cwd=self.repository)
        multi_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()
        (self.repository / "a.txt").write_text("VESPER A\n")
        (self.repository / "b.txt").write_text("VESPER B\n")
        run("git", "commit", "-qam", "feat: update both files", cwd=self.repository)
        feature_author_date = run(
            "git", "show", "-s", "--format=%aI", "HEAD", cwd=self.repository
        ).strip()
        exporter.export_patch_series(self.repository, self.output, multi_base, [])
        original = next(self.output.glob("*.patch")).read_bytes()

        run("git", "checkout", "-q", multi_base, cwd=self.repository)
        (self.repository / "a.txt").write_text("VESPER A\n")
        run("git", "commit", "-qam", "upstream absorbs first change", cwd=self.repository)
        rebased_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()
        (self.repository / "b.txt").write_text("VESPER B\n")
        run(
            "git",
            "commit",
            "-qam",
            "feat: update both files",
            f"--date={feature_author_date}",
            cwd=self.repository,
        )

        exporter.export_patch_series(self.repository, self.output, rebased_base, [])

        updated = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotEqual(original, updated)
        self.assertNotIn(b"diff --git a/a.txt", updated)
        self.assertIn(b"diff --git a/b.txt", updated)

    def test_exports_binary_delta_patches(self) -> None:
        exporter = load_exporter()
        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "asset.bin").write_bytes(b"\x00before\xff")
        run("git", "add", "asset.bin", cwd=self.repository)
        run("git", "commit", "-q", "-m", "upstream binary asset", cwd=self.repository)
        binary_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()
        (self.repository / "asset.bin").write_bytes(b"\x00after\xff")
        run("git", "commit", "-qam", "feat: update binary asset", cwd=self.repository)

        exporter.export_patch_series(self.repository, self.output, binary_base, [])

        self.assertIn(b"GIT binary patch", next(self.output.glob("*.patch")).read_bytes())

    def test_unfolds_complete_subject_before_matching(self) -> None:
        exporter = load_exporter()
        prefix = "feat: " + ("very long Vesper subject " * 5)
        run("git", "commit", "--amend", "-q", "-m", prefix + "ONE", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        original_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertIn(b" ONE", original_bytes)

        run("git", "commit", "--amend", "-q", "-m", prefix + "TWO", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, self.base, [])

        updated_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotEqual(original_bytes, updated_bytes)
        self.assertIn(b" TWO", updated_bytes)
        self.assertNotIn(b" ONE", updated_bytes)

    def test_rejects_signoff_hidden_after_patch_separator(self) -> None:
        exporter = load_exporter()
        author = "Vesper Test <vesper-test@example.invalid>"
        run(
            "git",
            "commit",
            "--amend",
            "-q",
            "-m",
            "feat: add Vesper behaviour",
            "-m",
            "---",
            "-m",
            f"Signed-off-by: {author}",
            cwd=self.repository,
        )

        with self.assertRaisesRegex(RuntimeError, "surviving author sign-off"):
            exporter.export_patch_series(
                self.repository,
                self.output,
                self.base,
                [],
                require_author_signoff=True,
            )

    def test_accepts_signoff_for_author_name_requiring_rfc_quotes(self) -> None:
        exporter = load_exporter()
        run("git", "config", "user.name", "Doe, Jane", cwd=self.repository)
        run(
            "git",
            "commit",
            "--amend",
            "-q",
            "--signoff",
            "--no-edit",
            "--reset-author",
            cwd=self.repository,
        )

        exporter.export_patch_series(
            self.repository,
            self.output,
            self.base,
            [],
            require_author_signoff=True,
        )

        self.assertEqual(1, len(list(self.output.glob("*.patch"))))

    def test_commit_message_may_quote_diff_header(self) -> None:
        exporter = load_exporter()
        run(
            "git",
            "commit",
            "--amend",
            "-q",
            "-m",
            "feat: add Vesper behaviour",
            "-m",
            "Context before quoted patch.\n\ndiff --git a/example b/example\nQuoted patch text.",
            cwd=self.repository,
        )

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        patch = next(self.output.glob("*.patch")).read_bytes()
        self.assertIn(b"Context before quoted patch.", patch)
        self.assertIn(b"diff --git a/example b/example", patch)
        self.assertIn(b"Quoted patch text.", patch)

    def test_diff_line_equal_to_separator_cannot_hide_an_earlier_file_change(self) -> None:
        exporter = load_exporter()
        run("git", "checkout", "-q", self.base, cwd=self.repository)
        (self.repository / "a.txt").write_text("--\nBASE\n")
        (self.repository / "b.txt").write_text("base\n")
        run("git", "add", "a.txt", "b.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "upstream adds two files", cwd=self.repository)
        collision_base = run("git", "rev-parse", "HEAD", cwd=self.repository).strip()

        (self.repository / "a.txt").write_text("OLD\nBASE\n")
        (self.repository / "b.txt").write_text("VESPER\n")
        run("git", "commit", "-qam", "feat: update two files", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, collision_base, [])
        original_bytes = next(self.output.glob("*.patch")).read_bytes()

        (self.repository / "a.txt").write_text("NEW\nBASE\n")
        run("git", "commit", "--amend", "-qam", "feat: update two files", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, collision_base, [])

        updated_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotEqual(original_bytes, updated_bytes)
        self.assertIn(b"+NEW", updated_bytes)
        self.assertNotIn(b"+OLD", updated_bytes)

    def test_regenerates_when_full_message_changes_after_internal_separator(self) -> None:
        exporter = load_exporter()
        run(
            "git",
            "commit",
            "--amend",
            "-q",
            "-m",
            "feat: add Vesper behaviour",
            "-m",
            "Context before separator.\n\n---\n\nAdditional context ONE.",
            cwd=self.repository,
        )
        exporter.export_patch_series(self.repository, self.output, self.base, [])
        original_bytes = next(self.output.glob("*.patch")).read_bytes()

        run(
            "git",
            "commit",
            "--amend",
            "-q",
            "-m",
            "feat: add Vesper behaviour",
            "-m",
            "Context before separator.\n\n---\n\nAdditional context TWO.",
            cwd=self.repository,
        )
        exporter.export_patch_series(self.repository, self.output, self.base, [])

        updated_bytes = next(self.output.glob("*.patch")).read_bytes()
        self.assertNotEqual(original_bytes, updated_bytes)
        self.assertIn(b"Additional context TWO.", updated_bytes)
        self.assertNotIn(b"Additional context ONE.", updated_bytes)

    def test_retained_patch_uses_canonical_envelope_and_ordinal(self) -> None:
        exporter = load_exporter()
        (self.repository / "second.txt").write_text("second feature\n")
        run("git", "add", "second.txt", cwd=self.repository)
        run("git", "commit", "-q", "-m", "feat: add second feature", cwd=self.repository)
        exporter.export_patch_series(self.repository, self.output, self.base, [])

        first = sorted(self.output.glob("*.patch"))[0]
        tampered = first.read_bytes().replace(
            b"From 0000000000000000000000000000000000000000 ",
            b"From 1111111111111111111111111111111111111111 ",
            1,
        ).replace(b"Subject: [PATCH 1/2]", b"Subject: [PATCH 09/99]", 1)
        first.write_bytes(tampered)

        exporter.export_patch_series(self.repository, self.output, self.base, [])

        canonical = sorted(self.output.glob("*.patch"))[0].read_bytes()
        self.assertTrue(
            canonical.startswith(
                b"From 0000000000000000000000000000000000000000 "
            )
        )
        self.assertIn(b"Subject: [PATCH 1/2]", canonical)
        self.assertNotIn(b"[PATCH 09/99]", canonical)


if __name__ == "__main__":
    unittest.main()
