# All The Mods 9

Original All the Mods 9 **1.1.1**, Minecraft **1.20.1**, Forge **47.4.0**,
prepared for the LANMinecraft launcher. The card and launched game window are
named **All The Mods 9**, without a separate network edition suffix.

## Author source and byte identity

The authoritative client export is [ATMTeam's CurseForge file 7097953](https://www.curseforge.com/minecraft/modpacks/all-the-mods-9/files/7097953),
released 12 October 2025. The [official project repository](https://github.com/AllTheMods/ATM-9)
is the author's source repository; its moving main branch is not substituted
for the released export.

The 51,433,990-byte client archive has SHA256
`5d7f7b4a3775a3902274311b5d3949367e7da3baaba97a0bf55312d966302a6d`.
The source was downloaded again from the official CDN during this rebuild
and matched that complete hash. `tools/upstream-manifest.json` preserves its
435 exact project/file IDs. `tools/upstream-lock.json` pins every installed
download, all 1,360 author overrides and the Mojang client by size and SHA256.
Author configs, scripts, quests, resources and versions remain byte-identical
to those sources. No Modified content, custom helper or Safety mod is included.
Original Spark, Observable, Crash Utilities and Crash Assistant are retained.

The withdrawn Lionfish API file 5922047 remains available inside the author's
[server export 7097957](https://www.curseforge.com/minecraft/modpacks/all-the-mods-9/files/7097957).
Only that exact client-manifest JAR is reused from the server export; no extra
server files are installed. Its original bytes are included in Git so rebuilding
does not require downloading the entire server export.

## Duplicate entries in the author export

The raw client export names two versions of each of two Forge IDs. Installing
both would leave duplicate IDs. These are explicit installation normalizations,
not silent library updates:

| ID | Inactive export entry | Selected author entry | Evidence |
| --- | --- | --- | --- |
| `computercraft` | CC:Tweaked 1.113.1, file 5714507 | 1.116.1 | Newer JAR is embedded in the author's `overrides/mods/` itself. |
| `oculus` | Oculus 1.8.0, file 6020952 | Mekalus 1.8.0.1 | Both occur in the author manifest; the release notes explicitly list Mekalus 1.8.0.1 and its author identifies it as an Oculus fork. |

Both original and selected JARs declare the same corresponding Forge mod ID.
Their exact versions and hashes remain in `historicalFiles` and the active
lock, respectively. No assumption about CurseForge app duplicate handling is
reported as an observed test. No registry IDs are renamed by this normalization.

## Reproduce and publish

Python 3.12 or later, standard library only:

```sh
python tools/import_upstream.py --pack . --cache artifacts/upstream --restore-locked-files
python tools/verify_upstream.py --pack .
python -m unittest discover -s tools -p "test_*.py"
python tools/generate_manifest.py --pack . --out dist --revision YOUR_COMMIT
python tools/generate_manifest.py --pack . --out dist --verify-all
```

The release workflow restores the committed lock without rewriting it or querying
mutable per-file metadata. An independent archive audit can additionally run
`python tools/import_upstream.py --pack . --cache artifacts/upstream --workers 6`.

Downloaded JARs, shaders and the Mojang client are omitted from Git and restored
from exact source IDs and committed hashes. The author-embedded CC:Tweaked JAR
and withdrawn Lionfish API are included. Existing files with different bytes
cause import verification to fail instead of being overwritten.

The publish workflow uploads every payload and the library bundle before
`pack-manifest.json`. Reuse requires GitHub's full SHA256 digest and size; all
remote payload digests are checked again before publishing the manifest. `tools/legacy-files.json` contains exact previously
published managed file hashes for safe migration after the repository reset.
The manifest is authoritative; historical entries are never active files.
`launcher/pack-owned.txt` identifies author-owned configuration and content.
Personal worlds, player data, screenshots and personal options are not shipped.
The migration does not claim old worlds retain removed registry entries.

Steam transport and identity integration are installed by the launcher for the
Forge/Minecraft platform. The verified managed transport is the author's Forge
e4steam **0.3.4**, SHA256
`33421acbea4d904ac3cefa62ac1d4bd5f62f9e9169b81a4d16a052d2330bc6fc`.
It stays outside the author pack. The shared launcher adapter supplies the
one-click LAN flow without a custom ATM9 gameplay mod. No base JAR, config,
script or resource is changed beyond the documented export-duplicate resolution.
Safety has no pack-side change here:
this restores the original BASE author composition and does not add NEW content
or copy Modified's protection framework. Actual runtime and connection results
are recorded separately in `TESTING-STATUS.md`.
