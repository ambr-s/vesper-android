# Vesper for Android

Vesper is an independent client for the Signal service. This repository
contains the Vesper changes, not a copy of Signal's source. `./tools/materialize.sh`
applies them to the Signal release recorded in `upstream.pin`.

Vesper is not affiliated with or endorsed by Signal Messenger. Its Android package
name is `systems.amber.vesper`.

Vesper loads per-account configuration and captcha handoff pages from
`https://vsp.asy.st`; it does not depend on `signalcaptchas.org`. The manifest
accepts Signal's `sgnl://signal.me/...` contact fallback. Verified ownership of
the `https://signal.me` domain remains controlled by Signal's hosted Android App
Links association.

## Build

You need JDK 21 and the Android SDK declared by the pinned Signal release.

```bash
python3 tools/test_export_patches.py -v
./tools/materialize.sh
python3 tools/test_materialised_theme.py -v
cd work
./gradlew :Signal-Android:assembleWebsiteProdRelease
```

Trusted same-repository pull requests run these gates and upload an unsigned
universal APK without signing credentials or publishing updates. The existing
main-branch workflow signs and publishes builds after merge.

The materialised-theme checks protect source-level hooks that can be lost during
an upstream rebase: applying the media-send theme before activity creation and
using the navbar surface for its gesture-navigation inset. They supplement the
release build, not on-device lifecycle or visual testing.

Make source changes in `work/`, commit them there, run the relevant checks, then
return to this directory and run `./tools/export.sh`. Do not edit generated patches
by hand. [AGENTS.md](AGENTS.md) has the full maintenance workflow.

## Licence and credits

Vesper is free software under the
[GNU Affero General Public License v3.0 only](LICENSE). Contributions are covered
by the same licence; [CONTRIBUTING.md](CONTRIBUTING.md) explains the sign-off.

Vesper is built from [Signal Android](https://github.com/signalapp/Signal-Android).
Some of Vesper's dynamic-colour support, debug logging and resource tools are
adapted from [Molly](https://github.com/mollyim/mollyim-android). Signal and Molly
contributors retain their copyright. See [NOTICE](NOTICE) for the details.
