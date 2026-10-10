# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Regressions for Signal's shared call/sticker preview action migration."""
from pathlib import Path
import tempfile
import unittest
from transform import transform_source_theme_colors


class LinkPreviewColorTest(unittest.TestCase):
    def test_unrelated_ternaries_are_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app/src/main/java/Other.java"
            path.parent.mkdir(parents=True)
            source = "package test;\n" + "\n".join((
                "int color = ContextCompat.getColor(context, enabled ? R.color.custom : R.color.other);",
                "int color = ContextCompat.getColor(context, enabled ? R.color.release_notes_bubble_text : R.color.signal_accent_primary);",
            ))
            path.write_text(source)
            self.assertEqual(transform_source_theme_colors(Path(tmp)), 0)
            self.assertEqual(path.read_text(), source)

    def test_outgoing_resources_and_incoming_theme_for_both_receivers(self):
        for receiver in ("joinCallLinkStub.get()", "button"):
            with self.subTest(receiver=receiver), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "app/src/main/java/Preview.java"
                path.parent.mkdir(parents=True)
                path.write_text("package test;\n\n" + "\n".join(
                    f"{receiver}.{setter}(ContextCompat.getColor(context, messageRecord.isOutgoing() ? org.signal.core.ui.R.color.{outgoing} : org.signal.core.ui.R.color.{incoming}));"
                    for setter, outgoing, incoming in (
                        ("setTextColor", "signal_light_colorOnPrimary", "signal_colorOnPrimaryContainer"),
                        ("setBackgroundColor", "signal_light_colorTransparent2", "signal_colorOnPrimary"),
                    )
                ))
                transform_source_theme_colors(Path(tmp))
                source = path.read_text()
                self.assertIn("messageRecord.isOutgoing() ? ContextCompat.getColor(context, org.signal.core.ui.R.color.signal_light_colorOnPrimary) : ThemeUtil.getThemedColor(context, com.google.android.material.R.attr.colorOnPrimaryContainer)", source)
                self.assertIn("messageRecord.isOutgoing() ? ContextCompat.getColor(context, org.signal.core.ui.R.color.signal_light_colorTransparent2) : ThemeUtil.getThemedColor(context, com.google.android.material.R.attr.colorOnPrimary)", source)
                self.assertEqual(transform_source_theme_colors(Path(tmp)), 0)


if __name__ == "__main__":
    unittest.main()
