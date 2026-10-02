# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Exercise real exported hunks against upstream 8.30 context changes, offline."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = "app/src/main/java/org/thoughtcrime/securesms/"


class Signal830PatchTest(unittest.TestCase):
    def apply_hunks(self, target, predicate, upstream):
        patch = (ROOT / "patches/0001-feat-add-Material-You-dynamic-theming.patch").read_text()
        section = patch.split(f"diff --git a/{target} b/{target}\n", 1)[1].split("\ndiff --git ", 1)[0]
        chunks = re.split(r"(?m)(?=^@@ -)", section)
        hunks = [chunk for chunk in chunks[1:] if predicate(chunk)]
        self.assertTrue(hunks)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / target
            path.parent.mkdir(parents=True)
            path.write_text(upstream)
            result = subprocess.run(["git", "apply", "-"], cwd=tmp, text=True, capture_output=True,
                                    input=f"diff --git a/{target} b/{target}\n{chunks[0]}" + "".join(hunks).rstrip("\n") + "\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            return path.read_text()

    def test_call_theme_imports_without_removed_preferences_import(self):
        upstream = "\n".join("import org.thoughtcrime.securesms." + name for name in [
            "safety.SafetyNumberBottomSheet", "service.webrtc.CallLinkDisconnectReason",
            "service.webrtc.SignalCallManager", "sms.MessageSender", "util.FullscreenHelper",
            "util.RemoteConfig", "util.VibrateUtil"]) + "\n"
        source = self.apply_hunks(BASE + "components/webrtc/v2/WebRtcCallActivity.kt",
                                  lambda h: "+import org.thoughtcrime.securesms.util.DynamicTheme" in h, upstream)
        for name in ["DynamicTheme", "DynamicNoActionBarTheme"]:
            line = f"import org.thoughtcrime.securesms.util.{name}\n"
            self.assertEqual(source.count(line), 1)
            source = source.replace(line, "")
        self.assertEqual(source, upstream)

    def test_settings_preserve_new_upstream_defaults(self):
        upstream = '''    }

  var theme: Theme
    get() = Theme.deserialize(getString(THEME, if (DynamicTheme.systemThemeAvailable()) "system" else "light"))
    set(value) {
      putString(THEME, value.serialize())
      configurationSettingChanged.postValue(THEME)
    }

  var messageFontSize: Int by integerValue(MESSAGE_FONT_SIZE, 16)
'''
        source = self.apply_hunks(BASE + "keyvalue/SettingsValues.kt",
                                  lambda h: "+      setTheme(value" in h or "+  fun setTheme(" in h, upstream)
        self.assertIn('getString(THEME, if (DynamicTheme.systemThemeAvailable()) "system" else "light")', source)
        self.assertIn('var messageFontSize: Int by integerValue(MESSAGE_FONT_SIZE, 16)', source)
        self.assertIn('setTheme(value, isDynamicColorsEnabled)', source)
        self.assertIn('putBoolean(DYNAMIC_COLORS_ENABLED, useDynamicColors)', source)
        self.assertIn('configurationSettingChanged.postValue(THEME)', source)
        self.assertIn('getBoolean(IGNORE_REMOTE_DELETE, false)', source)


if __name__ == "__main__":
    unittest.main()
