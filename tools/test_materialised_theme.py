# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Source-contract checks for downstream hooks after upstream materialisation.

These supplement compilation; they do not replace Android UI/lifecycle tests.
Run after tools/materialize.sh, not in the pre-materialisation tooling gate.
"""

from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "work/app/src/main/java/org/thoughtcrime/securesms"


class MaterialisedThemeContractTest(unittest.TestCase):
    def test_media_theme_is_applied_before_activity_creation(self) -> None:
        source = (SOURCE / "mediasend/v3/MediaSendV3Activity.kt").read_text()
        self.assertRegex(
            source,
            r"override fun onPreCreate\(\)\s*\{\s*theme\.onCreate\(this\)\s*\}",
            "MediaSend must apply its dynamic theme in PassphraseRequiredActivity's pre-create hook",
        )
        self.assertEqual(source.count("theme.onCreate(this)"), 1)
        self.assertEqual(source.count("override fun onResume()"), 1)
        self.assertRegex(source, r"override fun onResume\(\)\s*\{\s*super\.onResume\(\)\s*theme\.onResume\(this\)")

    def test_navigation_inset_uses_the_navigation_container_surface(self) -> None:
        source = (SOURCE / "MainActivity.kt").read_text()
        self.assertRegex(
            source,
            r"Column\(\s*modifier\s*=\s*Modifier\s*(?:\.clip\([^\n]*\)\s*)?\.background\(color\s*=\s*colorAttribute\(R\.attr\.navbar_container_color\)\)\s*\)\s*\{\s*MainNavigationBar\(",
            "The navbar and its navigationBarsPadding spacer must share the Vesper navbar surface",
        )


if __name__ == "__main__":
    unittest.main()
