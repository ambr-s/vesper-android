# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Cross-version lifecycle hooks; the real source is also checked after replay."""
from pathlib import Path
import tempfile
import unittest
from activity_theme import transform_activity_themes


class ActivityThemeTest(unittest.TestCase):
    def test_settings_theme_precedes_inflation_for_both_names(self):
        for name, layout in (("components/settings/DSLSettingsActivity.kt", "dsl_settings_activity"),
                             ("components/NavGraphHostActivity.kt", "nav_graph_host_activity")):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / "app/src/main/java/org/thoughtcrime/securesms" / name
                path.parent.mkdir(parents=True)
                path.write_text('''package example
class Activity {
  override fun onCreate(savedInstanceState: Bundle?, ready: Boolean) {
    enableSettingsEdgeToEdge()

    setContentView(R.layout.LAYOUT)
    val navGraphId = resolveNavGraphId()
    dynamicTheme.onCreate(this)

    onBackPressedDispatcher.addCallback(this, OnBackPressed())
  }
}
'''.replace("LAYOUT", layout))
                self.assertEqual(transform_activity_themes(root), 1)
                source = path.read_text()
                self.assertEqual(source.count("dynamicTheme.onCreate(this)"), 1)
                self.assertLess(source.index("dynamicTheme.onCreate(this)"), source.index("setContentView"))
                self.assertIn("super.onPreCreate()", source)
                self.assertIn("val navGraphId = resolveNavGraphId()", source)
                self.assertIn("check(themeAppliedBeforeInflation)", source)
                self.assertEqual(transform_activity_themes(root), 0)
                self.assertEqual(source, path.read_text())

    def test_sticker_picker_hooks_preserve_each_upstream_lifecycle(self):
        for name, source, creation in (
            ("scribbles/ImageEditorStickerSelectActivity.java", '''package example;
import org.thoughtcrime.securesms.util.ViewUtil;
public final class ImageEditorStickerSelectActivity extends AppCompatActivity {
  public static final String EXTRA_FEATURE_STICKER = "imageEditor.featureSticker";
  protected void onCreate(@Nullable Bundle savedInstanceState) {
    EdgeToEdge.enable(this);
    super.onCreate(savedInstanceState);
  }
}
''', "    EdgeToEdge.enable(this);"),
            ("stickers/search/StickerSearchActivity.kt", '''package example
import org.thoughtcrime.securesms.PassphraseRequiredActivity
class StickerSearchActivity : PassphraseRequiredActivity() {
  override fun onCreate(savedInstanceState: Bundle?, ready: Boolean) {
    super.onCreate(savedInstanceState, ready)
    SignalTheme(isDarkMode = true) { ImageEditorStickerSearch(onResult = ::finishWithResult) }
  }
}
''', "  override fun onCreate(savedInstanceState: Bundle?, ready: Boolean) {"),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / "app/src/main/java/org/thoughtcrime/securesms" / name
                path.parent.mkdir(parents=True)
                path.write_text(source)
                self.assertEqual(transform_activity_themes(root), 1)
                result = path.read_text()
                self.assertEqual(result.count("dynamicTheme.onCreate(this)"), 1)
                self.assertEqual(result.count("dynamicTheme.onResume(this)"), 1)
                self.assertLess(result.index("dynamicTheme.onCreate(this)"), result.index(creation))
                if name.endswith(".kt"):
                    self.assertIn("DynamicMediaPreviewTheme()", result)
                    self.assertIn("SignalTheme(isDarkMode = true)", result)
                    self.assertIn("super.onPreCreate()", result)
                else:
                    self.assertIn("new DynamicNoActionBarTheme()", result)
                self.assertEqual(transform_activity_themes(root), 0)
                self.assertEqual(result, path.read_text())

    def test_unknown_settings_lifecycle_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "app/src/main/java/org/thoughtcrime/securesms/components/NavGraphHostActivity.kt"
            path.parent.mkdir(parents=True)
            path.write_text("upstream lifecycle changed")
            with self.assertRaises(RuntimeError):
                transform_activity_themes(root)
            self.assertEqual(path.read_text(), "upstream lifecycle changed")


if __name__ == "__main__":
    unittest.main()
