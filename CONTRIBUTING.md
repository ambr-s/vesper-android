# Contributing

Vesper is a patchset, so source work happens in the materialised Signal checkout:

```bash
./tools/materialize.sh
cd work
# edit, test and commit
cd ..
./tools/export.sh
```

Do not edit files in `patches/` by hand.

By contributing, you agree to license your work under
`AGPL-3.0-only`. You keep your copyright. You also confirm that you wrote the
change or have the right to submit it under that licence.

Commits must include a Developer Certificate of Origin sign-off:

```text
Signed-off-by: Your Name <you@example.com>
```

Use `git commit -s` to add it. The sign-off follows
[Developer Certificate of Origin 1.1](https://developercertificate.org/) and is
not a copyright assignment.

If you adapt code from Signal, Molly or another project, keep its notices and name
the source in the commit. Do not submit private keys, tokens, passwords, signing
files or generated local configuration.
