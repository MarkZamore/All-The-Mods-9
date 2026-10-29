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
All 431 author JARs and every author file outside the 107 explicitly pinned
quest-display resources remain byte-identical to those sources. The display
localization and five added data/document files are described below. No Modified
content, custom helper or Safety mod is included.
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
python tools/prepare_pack.py --pack . --cache artifacts/upstream --restore-locked-files
python tools/verify_upstream.py --pack .
python -m unittest discover -s tools -p "test_*.py"
python tools/generate_manifest.py --pack . --out dist --revision YOUR_COMMIT
python tools/generate_manifest.py --pack . --out dist --verify-all
```

The release workflow globally verifies existing author files before writing or
downloading, restores the reviewed display spans to their exact author bytes,
runs the unchanged author importer, verifies all 1,794 originals, then reapplies
and verifies the fixed localization. It does not rewrite the author lock or query
mutable per-file metadata in locked mode. Missing tracked overrides must be
restored from Git; they are never guessed from the partial display spans.
A full archive import uses `python tools/prepare_pack.py --pack . --cache
artifacts/upstream --workers 6` with the same reviewed normalization boundary.

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

## Russian quests and pack-owned diagnostics

The [Scriptora translation and MIT notice](library/ru-quests-provenance.md) are
adapted to the released ATM9 1.1.1 quests. `ru_ru.json` contains 7,538 entries.
Exactly 106 SNBT documents replace 327 human-display strings with language keys;
325 English fallback keys are appended to the existing English language file.
The original English display is preserved apart from one documented pre-existing
brace typo. Quest IDs, tasks, rewards, dependencies, coordinates, pictures and
button actions stay unchanged, so this does not reset quest progress. Author
names, brands, technical symbols and hidden credit/legal notices are retained.

`tools/atm9_ru_quests/manifest.json` pins the original/localized hashes and
reversible byte spans for all 107 replacements. The native structural proof is
committed beside it. `.gitattributes` disables text normalization, preserving the
exact author CRLF bytes outside the approved spans. Unknown source hashes,
unreviewed patch-tool/manifest identities and unrelated extra content fail
verification instead of being overwritten or accepted as another profile.

The five new runtime files are the Russian language file, `config/log4j2.xml`,
`launcher/jvm-args.txt` and two inert `kubejs/atm9_ru_quests_*` notice documents.
The logging configuration keeps INFO/WARN/ERROR diagnostics and limits archive
retention while avoiding the full DEBUG file. The launcher reads its single
pack-owned JVM argument; no logging hook is injected into an author mod.
The exact support hashes are in `tools/portable-profile.json`. The full MIT
license and provenance also travel inside the native KubeJS payload, so copying
the installed pack preserves the notices.

Steam transport and identity integration remain launcher-managed infrastructure,
outside the 431 author JARs. The shared [native LAN UI profile](https://github.com/MarkZamore/e4steam/releases/tag/native-lan-ui-v1)
declares its Forge e4steam 0.3.4 derivative separately, SHA256
`68ba6bdce76868e2cb43359a13416dfa1b011c628c13b6c4266b653c765b5c40`.
It removes the extra settings entry/redirects while preserving the native Steam
invitation code and all other original entries. Historical runtime observations
below refer to their recorded transport/launcher versions, not a new test of
this infrastructure profile.

Safety has no pack-side change: these display strings, logging data and inert
notices add no world ability, mod or protection framework. Native parsing and
deep comparison preserve gameplay data; the translation is not presented as a
new full-client or visual-language acceptance run. Actual runtime and connection
results are recorded separately in `TESTING-STATUS.md`.
