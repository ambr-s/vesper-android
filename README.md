# Vesper for Android

Vesper is an independent client for the Signal service. This repository
contains the Vesper changes, not a copy of Signal's source. `./tools/materialize.sh`
applies them to the Signal release recorded in `upstream.pin`.

Vesper is not affiliated with or endorsed by Signal Messenger. Its Android package
name is `systems.amber.vesper`.

## Build

You need JDK 21 and the Android SDK declared by the pinned Signal release.

```bash
./tools/materialize.sh
cd work
./gradlew :Signal-Android:assembleWebsiteProdRelease
```

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
