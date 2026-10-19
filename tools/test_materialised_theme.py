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
    def test_settings_host_theme_precedes_inflation(self) -> None:
        paths = [SOURCE / "components/settings/DSLSettingsActivity.kt", SOURCE / "components/NavGraphHostActivity.kt"]
        sources = [path.read_text() for path in paths if path.exists()]
        self.assertEqual(len(sources), 1)
        source = sources[0]
        self.assertEqual(source.count("dynamicTheme.onCreate(this)"), 1)
        self.assertLess(source.index("dynamicTheme.onCreate(this)"), source.index("setContentView("))
        self.assertIn("super.onPreCreate()", source)
        self.assertIn("check(themeAppliedBeforeInflation)", source)
        self.assertIn("val navGraphId = resolveNavGraphId()", source)

    def test_sticker_picker_retains_theme_and_upstream_security(self) -> None:
        legacy = SOURCE / "scribbles/ImageEditorStickerSelectActivity.java"
        modern = SOURCE / "stickers/search/StickerSearchActivity.kt"
        self.assertNotEqual(legacy.exists(), modern.exists())
        source = (legacy if legacy.exists() else modern).read_text()
        self.assertEqual(source.count("dynamicTheme.onCreate(this)"), 1)
        self.assertEqual(source.count("dynamicTheme.onResume(this)"), 1)
        if modern.exists():
            self.assertIn("StickerSearchActivity : PassphraseRequiredActivity()", source)
            self.assertIn("DynamicMediaPreviewTheme()", source)
            self.assertIn("SignalTheme(isDarkMode = true)", source)
            self.assertIn("ImageEditorStickerSearch(onResult = ::finishWithResult)", source)
            self.assertLess(source.index("dynamicTheme.onCreate(this)"), source.index("setContent {"))
        else:
            self.assertIn("new DynamicNoActionBarTheme()", source)
            self.assertLess(source.index("dynamicTheme.onCreate(this)"), source.index("super.onCreate(savedInstanceState)"))

    def test_conversation_retains_material_and_upstream_compose_colors(self) -> None:
        source = (SOURCE / "conversation/v2/ConversationFragment.kt").read_text()
        self.assertEqual(source.count('import com.google.android.material.R as MaterialR\n'), 1)
        self.assertIn('MaterialR.attr.colorOnSurfaceVariant', source)
        self.assertIn('MaterialR.attr.colorOnSurface', source)
        self.assertIn('MaterialR.attr.colorSurface', source)
        # Signal v8.29.2 introduces this alias for sticker confirmation. Do not
        # drop it just to restore the old patch's import-block context.
        if 'stickerConfirmation.sendColor' in source:
            self.assertEqual(source.count('import androidx.compose.ui.graphics.Color as ComposeColor\n'), 1)
            self.assertIn('stickerConfirmation.sendColor = ComposeColor(chatColors.asSingleColor())', source)

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
        # An unused upstream import may remain for cross-version patch context;
        # dynamic surfaces must call the Compose resolver, not the View helper.
        self.assertNotIn('ThemeUtil.getThemedColor(', source)

    def test_link_preview_actions_keep_incoming_dynamic_colors(self) -> None:
        source = (SOURCE / "conversation/ConversationItem.java").read_text()
        self.assertIn('messageRecord.isOutgoing() ? ContextCompat.getColor(context, org.signal.core.ui.R.color.signal_light_colorOnPrimary) : ThemeUtil.getThemedColor(context, com.google.android.material.R.attr.colorOnPrimaryContainer)', source)
        self.assertIn('messageRecord.isOutgoing() ? ContextCompat.getColor(context, org.signal.core.ui.R.color.signal_light_colorTransparent2) : ThemeUtil.getThemedColor(context, com.google.android.material.R.attr.colorOnPrimary)', source)
        if 'presentLinkPreviewAction(' in source:
            self.assertIn('presentLinkPreviewAction(R.string.ConversationItem__view_pack', source)
            self.assertIn('eventListener.onViewStickerPackLink(', source)
            self.assertIn('presentLinkPreviewAction(R.string.ConversationItem__join_call', source)
        self.assertIn('eventListener.onJoinCallLink(callLinkRootKey)', source)

    def test_privacy_does_not_expose_mobilecoin_payment_lock(self) -> None:
        source = (SOURCE / "components/settings/app/privacy/PrivacySettingsFragment.kt").read_text()
        self.assertNotIn('sectionHeaderPref(R.string.preferences_app_protection__payments)', source)
        self.assertNotIn('title = DSLSettingsText.from(R.string.preferences__payment_lock)', source)
        self.assertNotIn('biometricAuth.authenticate(', source)
        # Keep upstream setup, cancellation and callbacks together even though
        # Vesper does not expose the payments preference that invokes them.
        self.assertIn('biometricAuth.cancelAuthentication()', source)
        self.assertIn('inner class BiometricAuthenticationListener', source)

    def test_navigation_inset_uses_the_navigation_container_surface(self) -> None:
        source = (SOURCE / "MainActivity.kt").read_text()
        self.assertRegex(
            source,
            r"Column\(\s*modifier\s*=\s*Modifier\s*(?:\.clip\([^\n]*\)\s*)?\.background\(color\s*=\s*colorAttribute\(R\.attr\.navbar_container_color\)\)\s*\)\s*\{\s*MainNavigationBar\(",
            "The navbar and its navigationBarsPadding spacer must share the Vesper navbar surface",
        )


if __name__ == "__main__":
    unittest.main()
