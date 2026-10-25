# Signal 8.33 patch series

Signal 8.33 extracted Appearance, Help and Labs UI into `feature/app-settings`,
moved `SpanUtil` to `core/ui` and `RecipientId` to `core/models`, and changed
nearby imports and call event subscriptions. These are semantic source changes,
not missing preimage blobs.

`patches/*.patch` remains the unchanged known-good pre-8.33 series. The
materialiser and exporter select `patches/signal-8.33/*.patch` for 8.33 and later.
This temporary parallel series avoids rewriting the published 8.32.2 source or
recreating upstream's removed app-only settings screens. Keep both validation
legs until 8.33 is published and the old series can be retired. `upstream.pin`
continues to mean last successfully published release; this repair does not
advance it or publish a release.

The new series is generated from source commits with `tools/export.sh`, never
edited by hand. Original authors, author dates, messages and DCO trailers are
preserved. Appearance retains upstream state/events/repository architecture;
Help retains upstream navigation and uses host composable slots for logging
confirmation, the version-tap internal-user setting and Vesper attribution.
Only the appearance strings used by the extracted UI are added to its module.
The app-owned helper continues to own deletion of logs and configuration.

Validation:

- `python3 -m unittest discover -s tools -p 'test_*.py'`
- `bash -n tools/materialize.sh tools/export.sh`
- Fresh materialisation, exact source-tree comparison and byte-identical second
  export (both series use the same provenance/tree-checking exporter).
- PR matrix: published pin plus explicit `v8.33.1`, settings/lifecycle/config/log
  tests on both, extracted appearance ViewModel tests on the candidate, then
  complete unsigned release APK assembly on both. No publishing credentials.
