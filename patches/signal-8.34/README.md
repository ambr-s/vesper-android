# Signal 8.34 series

This series preserves the published 8.33 series while qualifying Signal v8.34.2.
`upstream.pin` remains publication-defined. Materialisation and export select this
series from the actual upstream tag, not from the published pin.

The rebase retains original authors, dates, messages and DCO trailers. Changes to
feature payloads are limited to the upstream settings extraction:

- Appearance events retain the new parent navigation emitter. Dynamic colour and
  Vesper theme preferences remain independent.
- The remote deletion preference moves into the privacy screen, state, events
  and repository. Enabling still requires confirmation; disabling is immediate.
  The original stored key, default, marker and backup filtering are unchanged.
- Labs remains public in the extracted settings home. Internal preferences still
  require the existing account policy and refresh when returning to settings.
  Update settings remain visible for builds which manage their own updates.
- The MobileCoin payment lock row and its scroll target remain hidden. Upstream
  authentication cancellation and state handling are retained.
- The removed Java username editor is not restored. Its Compose replacement
  already uses MaterialTheme colours, which receive Vesper's dynamic scheme.
- The avatar menu retains the new upstream popup tooltip implementation.
- The removed stickerReplies preference is not restored. All surviving public
  Labs preferences retain their existing defaults and access policy.

PR validation builds both the published pin and v8.34.2 without signing or
publication, checks exact-tree replay and byte-stable export, and runs settings,
configuration, lifecycle, appearance and candidate privacy/navigation tests.
Retire obsolete parallel series separately after successful publication and
confirmation that no supported validation target still depends on them.
