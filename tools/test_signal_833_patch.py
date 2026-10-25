#!/usr/bin/env python3
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Supplementary contracts for the 8.33 extracted appearance screen."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work'

@unittest.skipUnless((WORK / 'feature/app-settings/src/main/java/org/signal/appsettings/appearance').exists(), 'requires materialised Signal 8.33+')
class AppearanceMigrationTest(unittest.TestCase):
    def test_controls_use_extracted_state_and_events(self):
        base = WORK / 'feature/app-settings/src/main/java/org/signal/appsettings/appearance'
        screen = (base / 'AppearanceSettingsScreen.kt').read_text()
        state = (base / 'AppearanceSettingsState.kt').read_text()
        events = (base / 'AppearanceSettingsEvent.kt').read_text()
        for field, event in [('dynamicColors', 'DynamicColorsChanged'), ('vesperTheme', 'VesperThemeChanged')]:
            self.assertIn('val ' + field + ': Boolean', state)
            self.assertIn('state.' + field, screen)
            self.assertIn(event, screen)
            self.assertIn(event, events)
        self.assertIn('state.vesperTheme && state.isDynamicColorsAvailable', screen)

    def test_updater_retains_call_gate_with_upstream_event_bus(self):
        source = (WORK / 'app/src/main/java/org/thoughtcrime/securesms/apkupdate/ApkUpdateInstaller.kt').read_text()
        self.assertIn('import org.signal.core.util.eventbus.EventBus', source)
        self.assertIn('EventBus.default.getStickyEvent', source)
        self.assertNotIn('org.greenrobot', source)

    def test_preserved_delete_uses_core_recipient_id(self):
        source = (WORK / 'app/src/main/java/org/thoughtcrime/securesms/messages/PreservedRemoteDelete.kt').read_text()
        self.assertIn('import org.signal.core.models.recipients.RecipientId\n', source)

    def test_moved_span_utility_keeps_dynamic_link_color(self):
        source = (WORK / 'core/ui/src/main/java/org/signal/core/ui/util/SpanUtil.java').read_text()
        self.assertIn('clickListener, false, R.attr.signal_accent_primary)', source)
        self.assertIn('ds.setColor(ThemeUtil.getThemedColor(context, linkColor))', source)
        self.assertFalse((WORK / 'app/src/main/java/org/thoughtcrime/securesms/util/SpanUtil.java').exists())

if __name__ == '__main__':
    unittest.main()
