# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Check the real Material You import hunk against both upstream alias layouts.

This small fixture needs no network or Android SDK. Full materialisation and
Gradle compilation remain authoritative for the complete patch series.
"""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET = "app/src/main/java/org/thoughtcrime/securesms/conversation/v2/ConversationFragment.kt"


class ConversationPatchTest(unittest.TestCase):
    def test_material_import_preserves_upstream_compose_alias(self):
        patch = (ROOT / "patches/0001-feat-add-Material-You-dynamic-theming.patch").read_text()
        section = patch.split(f"diff --git a/{TARGET} b/{TARGET}\n", 1)[1].split("\ndiff --git ", 1)[0]
        # Reconstruct the real import hunk; package context is stable even when
        # upstream inserts or reorders aliases at the end of the imports.
        chunks = re.split(r"(?m)(?=^@@ -)", section)
        imports = [chunk for chunk in chunks[1:] if "+import com.google.android.material.R as MaterialR" in chunk]
        self.assertEqual(len(imports), 1)
        import_patch = f"diff --git a/{TARGET} b/{TARGET}\n{chunks[0]}{imports[0]}"
        for version, compose_alias, trailing_alias in [
            ("v8.30.2", "import androidx.compose.ui.graphics.Color as ComposeColor\n", ""),
            ("v8.31.1", "import androidx.compose.ui.graphics.Color as ComposeColor\nimport org.signal.appsettings.R as AppSettingsR\n", "import org.signal.core.util.R as CoreUtilsR\n"),
        ]:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / TARGET
                path.parent.mkdir(parents=True)
                upstream = (
                    " */\n\npackage org.thoughtcrime.securesms.conversation.v2\n\n"
                    "import android.Manifest\nimport android.animation.ValueAnimator\n"
                    "import java.util.Optional\n"
                    "import java.util.concurrent.ExecutionException\n"
                    "import kotlin.time.Duration.Companion.days\n"
                    "import kotlin.time.Duration.Companion.milliseconds\n"
                    + compose_alias
                    + "import org.signal.core.ui.R as CoreUiR\n"
                    + trailing_alias
                    + "\n/**\n * Conversation.\n */\n"
                )
                path.write_text(upstream)
                result = subprocess.run(["git", "apply", "-"], input=import_patch, text=True, cwd=tmp, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                source = path.read_text()
                self.assertEqual(source.count("import com.google.android.material.R as MaterialR\n"), 1)
                self.assertEqual(source.replace("\nimport com.google.android.material.R as MaterialR\n", ""), upstream)


if __name__ == "__main__":
    unittest.main()
