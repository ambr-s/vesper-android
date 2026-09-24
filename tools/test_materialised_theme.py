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
    def test_remote_config_keeps_vesper_override_after_upstream_resolution(self) -> None:
        source = (SOURCE / "util/RemoteConfig.kt").read_text()
        delegate = source.split('operator fun getValue(thisRef: Any?, property: KProperty<*>): T {', 1)[1].split('// endregion', 1)[0]
        self.assertIn('VesperConfig.valueWithOverride(key, rawValue)', delegate)
        self.assertIn('this.transformer(', delegate)
        self.assertIn('value is Number', delegate)
        self.assertIn('value.toString()', delegate)
        # The new upstream internal-override resolver must not be bypassed.
        if 'private fun effectiveRawValue(' in source:
            self.assertIn('return transformer(effectiveRawValue(key))', delegate)
            self.assertIn('internal fun resolve(): T = transformer(effectiveRawValue(key))', delegate)
            self.assertIn('internal fun resolveDefault(): T = transformer(null)', delegate)
        else:
            self.assertIn('return transformer(REMOTE_VALUES[key])', delegate)

    def test_kotlin_settings_preserve_dynamic_theme_contract(self) -> None:
        source = (SOURCE / "keyvalue/SettingsValues.kt").read_text()
        self.assertIn('const val DYNAMIC_COLORS_ENABLED = "settings.dynamicColors"', source)
        self.assertIn('fun setTheme(theme: Theme, useDynamicColors: Boolean)', source)
        self.assertIn('putBoolean(DYNAMIC_COLORS_ENABLED, useDynamicColors)', source)
        self.assertIn('setTheme(value, isDynamicColorsEnabled)', source)
        self.assertIn('configurationSettingChanged.postValue(THEME)', source)

    def test_extended_colors_retain_upstream_neutral_fill(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "work/core/ui/src/main/java/org/signal/core/ui/compose/theme/SignalTheme.kt").read_text()
        dark = source.split('private val darkExtendedColors = ExtendedColors(', 1)[1].split('\n)', 1)[0]
        self.assertIn('neutralFill = Color(0x33FFFFFF)', dark)
        self.assertIn('colorOnCustomVariant = Color(0xB3FFFFFF)', dark)

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

    def test_main_activity_imports_dynamic_color_resolver(self) -> None:
        source = (SOURCE / "MainActivity.kt").read_text()
        self.assertIn('import org.signal.core.ui.compose.theme.colorAttribute\n', source)
        self.assertNotIn('import org.signal.core.ui.util.ThemeUtil\n', source)

    def test_navigation_inset_uses_the_navigation_container_surface(self) -> None:
        source = (SOURCE / "MainActivity.kt").read_text()
        self.assertRegex(
            source,
            r"Column\(\s*modifier\s*=\s*Modifier\s*(?:\.clip\([^\n]*\)\s*)?\.background\(color\s*=\s*colorAttribute\(R\.attr\.navbar_container_color\)\)\s*\)\s*\{\s*MainNavigationBar\(",
            "The navbar and its navigationBarsPadding spacer must share the Vesper navbar surface",
        )


if __name__ == "__main__":
    unittest.main()
