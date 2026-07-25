# Vesper Android repository guide

Vesper is maintained as a patchset against Signal Android. Never add the
materialised `work/` tree to this repository.

## Source of truth

- `upstream.pin` records the last Signal release that built and published
  successfully.
- `branding/` holds pattern-based branding inputs.
- `overlay/` holds complete files that Vesper owns or replaces.
- `patches/` holds patches generated from source commits.
- `work/` is an ignored Signal checkout used for development and conflict
  resolution.

## Development

1. Run `./tools/materialize.sh`.
2. Work in `work/`.
3. Commit the source changes in `work/`.
4. Run the relevant Gradle checks there.
5. Return to this repository and run `./tools/export.sh`.

Never edit `patches/` by hand. `./tools/export.sh` copies overlay files from
`work/` and rebuilds the patch series from its feature commits.

To test a new Signal release, move or export any current work first, then run:

```bash
./tools/bump.sh vX.Y.Z
```

After the build passes, accept the new pin with:

```bash
./tools/bump.sh --accept vX.Y.Z
```

## Licence and provenance

Keep existing copyright, licence and attribution notices. New Vesper files should
use `SPDX-License-Identifier: AGPL-3.0-only`. If code comes from another project,
name the source in the file or commit and update `NOTICE` when needed.

Contributions must follow `CONTRIBUTING.md`.

## Releases and secrets

A push to `main` starts a signed build and publishes it to the update channel.
Before pushing, check the complete diff and make sure these GitHub Actions secrets
exist:

- `SECRET_KEYSTORE`
- `SECRET_KEYSTORE_ALIAS`
- `SECRET_KEYSTORE_PASSWORD`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

Never commit a keystore, signing password, Cloudflare token, generated signing
properties or local Android configuration.

Keep the updater host `vspab.asy.st`. Released clients compile that address into
the app and cannot discover a replacement on their own.
