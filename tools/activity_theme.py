# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Theme hooks for activities renamed or replaced across supported Signal tags."""
from pathlib import Path


def _replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"Unexpected activity lifecycle context: {old!r}")
    return source.replace(old, new, 1)


def transform_activity_themes(checkout: Path) -> int:
    root = checkout / "app/src/main/java/org/thoughtcrime/securesms"
    changed = 0
    # Signal 8.32 renamed this host; keep both layouts and navigation policies.
    for name in ("components/settings/DSLSettingsActivity.kt", "components/NavGraphHostActivity.kt"):
        path = root / name
        if not path.exists():
            continue
        source = path.read_text()
        if "private var themeAppliedBeforeInflation = false" in source:
            continue
        source = _replace_once(source, "    dynamicTheme.onCreate(this)\n", "")
        source = _replace_once(source, "  override fun onCreate(savedInstanceState: Bundle?, ready: Boolean) {", '''  private var themeAppliedBeforeInflation = false

  override fun onPreCreate() {
    super.onPreCreate()
    dynamicTheme.onCreate(this)
    themeAppliedBeforeInflation = true
  }

  override fun onCreate(savedInstanceState: Bundle?, ready: Boolean) {''')
        source = _replace_once(source, "    enableSettingsEdgeToEdge()\n", '''    enableSettingsEdgeToEdge()
    check(themeAppliedBeforeInflation) {
      "The dynamic settings theme must be applied before inflating views."
    }
''')
        # Preserve the exact previously patched layout (one blank line).
        source = source.replace("\n\n\n    onBackPressedDispatcher", "\n\n    onBackPressedDispatcher")
        path.write_text(source)
        changed += 1
    # The old picker was replaced by a passphrase-gated Compose activity.
    # Never resurrect the removed activity or change the new result contract.
    legacy = root / "scribbles/ImageEditorStickerSelectActivity.java"
    modern = root / "stickers/search/StickerSearchActivity.kt"
    for path in (legacy, modern):
        if not path.exists():
            continue
        source = path.read_text()
        if "dynamicTheme.onCreate(this)" in source:
            continue
        if path == legacy:
            source = _replace_once(source, "import org.thoughtcrime.securesms.util.ViewUtil;", "import org.thoughtcrime.securesms.util.DynamicNoActionBarTheme;\nimport org.thoughtcrime.securesms.util.DynamicTheme;\nimport org.thoughtcrime.securesms.util.ViewUtil;")
            anchor = '  public static final String EXTRA_FEATURE_STICKER = "imageEditor.featureSticker";'
            source = _replace_once(source, anchor, anchor + '''
  private final DynamicTheme dynamicTheme = new DynamicNoActionBarTheme();

  @Override
  protected void onResume() {
    super.onResume();
    dynamicTheme.onResume(this);
  }''')
            source = _replace_once(source, "    EdgeToEdge.enable(this);", "    dynamicTheme.onCreate(this);\n    EdgeToEdge.enable(this);")
        else:
            source = _replace_once(source, "import org.thoughtcrime.securesms.PassphraseRequiredActivity", "import org.thoughtcrime.securesms.util.DynamicMediaPreviewTheme\nimport org.thoughtcrime.securesms.PassphraseRequiredActivity")
            anchor = "class StickerSearchActivity : PassphraseRequiredActivity() {"
            source = _replace_once(source, anchor, anchor + '''

  private val dynamicTheme = DynamicMediaPreviewTheme()

  override fun onPreCreate() {
    super.onPreCreate()
    dynamicTheme.onCreate(this)
  }

  override fun onResume() {
    super.onResume()
    dynamicTheme.onResume(this)
  }''')
        path.write_text(source)
        changed += 1
    return changed
