# All The Mods 9

Original All the Mods 9 **1.1.1**, Minecraft **1.20.1**, Forge **47.4.0**,
prepared for the LANMinecraft launcher. The card and launched game window are
named **All The Mods 9**, without a separate network edition suffix.

The source-only [quest translation owner workflow](tools/atm9_quest_updates/OWNER_WORKFLOW.md)
prepares reviewed future locale updates from a fresh, separately pinned author
release. Native author Russian takes priority, then an aligned community source,
then reviewed fallback text; stale or unsupported translations leave native
English available. Its opt-in schema2 reader accepts new release identities and
resource counts as reviewed data, without changing the current 1.1.1 profile or
runtime payload. Refreshing the external translator is an explicit owner action;
normal CI uses pinned inputs and never fetches its latest release.

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
localization, eight added data/document files and the one explicitly requested
render-compatibility mod are described below. No previous Modified content, custom
helper JAR or Safety mod is included.
Original Spark, Observable, Crash Utilities and Crash Assistant are retained.

The withdrawn Lionfish API file 5922047 remains available inside the author's
[server export 7097957](https://www.curseforge.com/minecraft/modpacks/all-the-mods-9/files/7097957).
Only that exact client-manifest JAR is reused from the server export; no extra
server files are installed. Its original bytes are included in Git so rebuilding
does not require downloading the entire server export.

## Requested native client compatibility

### Same-ID carpet recipe correction

`kubejs/data/alchemistry/recipes/dissolver/carpets.json` supplies the same
`alchemistry:dissolver/carpets` recipe with one corrected JSON field:
`input.ingredient.tag` is `minecraft:wool_carpets`. The author recipe still uses
the removed `minecraft:carpets` tag, as reported in
[Alchemistry issue 365](https://github.com/SmashingMods/Alchemistry/issues/365).
The 639-byte author JSON becomes 644 bytes by that single literal substitution;
type, group, input count, all outputs, probabilities and rolls retain their bytes.
Minecraft's wool-carpet tag and normal provider additions supply the input items.

This is a resource override of author recipe behavior even though the Alchemistry
JAR remains unchanged. All 432 JARs retain the published source hashes, including
ModernFix 5.24.4. The unpublished ModernFix 5.25.0 candidate is not used. Quest
localization, controls, logging, RAM/JVM settings and all other 1,805 runtime files
remain unchanged. Actual multiplayer acceptance of this data correction is
pending a new user/peer attempt; historical native receipts are not relabelled.

The source-only `tools/carpets_recipe_policy.py` helper checks the exact author
recipe, the one-field edit and `tools/carpets-recipe-policy.json`. Explicit source
authoring may run `prepare`; the normal producer and manifest publisher only
verify. Source restoration keeps the data file and rechecks it after restoring
the exact author payload. All manifest CLI modes require the policy. A changed
or already corrected author recipe fails before publication, requiring owner
review and retirement or rebasing of this known override. A new author-owned
override at the same resource path also requires review.

When refreshing author sources, retain the helper, receipt, the profile's
`recipeDataFixPolicy` pin and the recipe support row until that review. Keep the
policy separate from quest-only schema2 `baseReplacements`. If the author fixes
the recipe, remove this owned override after verifying the author result; retain
its exact legacy ownership row so old installations without sync state also
retire it. The existing `kubejs/**` ownership keeps normal personal-conflict backups.
No launcher launch-time rule, new helper mod or rewritten author JAR is used.

All **431 original author JARs remain byte-identical**. The user additionally
requested the official **Draconic Evolution Render Patcher 1.3.0** for Forge
1.20.1, making **432 shipped JARs**. Its CurseForge project/file IDs are
`1383702/8408406`; size 75598 bytes and SHA256
`a59d110b3a0f8ade8c6c4bd9e7c6d6cf265f84391bce89de87ef92de5498d4ef`.
The [official mod page](https://www.curseforge.com/minecraft/mc-mods/draconic-evolution-render-patcher)
is linked from the library. It is an author's compatibility addon, not a rewritten
Draconic Evolution JAR. Its native client mixins change Draconic/shader render
routing; the old base JAR hashes therefore do not imply unchanged runtime render
behavior. It adds no new terrain, inventory, ability or world-changing path.

The exact pinned compatibility JAR is an explicit portable-profile support row;
it is separate from the unchanged upstream author lock and is included in source
so author restoration retains it. [Static compatibility evidence](tools/qa/derenderpatcher-1.3.0-static.json)
covers 21 native target classes, the declared injection sites and 69 external
member references. It is separate from an in-game shader or Draconic visual test.
The author beta-notice option remains enabled. The [native title report](tools/qa/original-native-title-421.md)
records three successful title observations, actual453packIDs including this mod,
432sourceJARs plus the shared Steam component, and normal exit0. No world, LAN,
Steam-peer or Draconic visual run is claimed. The library inventory uses this real
ModList observation, rather than adding a guessed ID to older evidence.

`kubejs/client_scripts/lanmc_memory_warning_policy.js` sets only the loaded native
Memory Settings `disableWarnings=true` before its initial game-menu check. This
prevents its upper-memory panel for a launcher-selected heap above the author's
14336 MiB (14 GiB) recommendation. The original author JSON remains byte-identical and
literally false: neither the script nor the launcher rewrites it or unrelated
personal options. Earlier native low-heap Swing warnings and constructor logs are
outside this client-stage policy. No heap, render or simulation limit is added.

[The native client-policy tool](tools/client-policy/README.md) validates its actual
public config API. Its hash-pinned template stage runs **before** strict source
support preflight/author restoration; the native API stage runs **after** all
author JARs are restored. Missing owned scripts are restored; conflicting source
files are refused. Later author JARs with unchanged public APIs are accepted;
API changes require review. Keep these source tools/templates and the explicit
portable-profile support rows when importing a later author version.

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
python tools/client-policy/prepare.py --pack . --templates-only --apply
python tools/prepare_pack.py --pack . --cache artifacts/upstream --restore-locked-files
python tools/client-policy/prepare.py --pack . --apply
python tools/verify_upstream.py --pack .
python tools/keybinds/check_preset.py
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
and withdrawn Lionfish API are included, together with the explicit requested
Render Patcher compatibility JAR. Existing files with different bytes
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

The original seven added data/document files are the Russian language file, `config/log4j2.xml`,
`launcher/jvm-args.txt`, two inert `kubejs/atm9_ru_quests_*` notice documents,
and the optional keyboard preset with its guide under `launcher/`.
The active pack-owned `config/log4j2.xml` retains only four native Connection
DEBUG exception diagnostics in the existing rolling `latest.log`: `Failed to
sent packet` (Minecraft's spelling), `Double fault`, `Skipping packet due to
errors` and `Timeout`. Packet traces and unrelated Connection DEBUG are filtered
out; INFO/WARN/ERROR and the existing archive/console limits remain unchanged.
There is no separate `debug.log`, packet hook, game-JAR rewrite or launcher-time
configuration rewrite. The exact current XML is 4617 bytes, SHA256
`9e7b9918b6ede54f7393ed3d307e51a2edb032b98c12f069f5df976bcf940b89`.

[Native caller and filter evidence](tools/qa/connection-throwables/README.md)
covers the six current profiles and exact native JARs, with actual Log4j 2.19.0,
2.22.1 and 2.26.0 filter checks. These are native bytecode/library checks, not new
game runs or evidence that a disconnect was fixed.

The existing pack-owned JVM selector is retained byte-for-byte. An existing
instance receives the owned logging file through normal pack synchronization;
its previous edited copy is preserved in `PackConflicts`, using the launcher's
existing ownership mechanism. No running game or instance is edited here.

For future author updates, retain `tools/network_logging_policy.py` and
`tools/network-logging-policy.json` with the pack-owned logging/JVM/ownership
data. After merging author files, run the source-authoring operation:

```text
python -B tools/network_logging_policy.py prepare --pack .
python -B tools/network_logging_policy.py verify --pack .
```

The source refresh preservation list is explicit:

- `config/log4j2.xml`
- `launcher/jvm-args.txt`
- `launcher/pack-owned.txt`
- `tools/network_logging_policy.py` and `tools/network-logging-policy.json`

Carry these tracked source overlays forward when merging a new author release,
then run the source prepare and verify commands after the author overrides have
been merged. This repository does not claim an automatic author-version updater.
The existing fixed-version import/restore or manual author-source refresh stays
separate from publication; the publisher verifies the retained policy and never
silently recreates a missing overlay.

Preparation preserves authored XML outside the bounded Connection block and
existing JVM arguments; conflicting custom logger/filter layouts fail for review
instead of being replaced with a default. Review any changed configuration pins.
The generator calls the read-only policy verifier in generation, sample-check
and full-check CLI modes, so an author import that drops or changes this policy
cannot silently publish. Publication never runs the mutating prepare operation.
Recheck the native caller proof on a new Minecraft/loader version; untested legacy
NetworkManager versions are not covered.

Original ATM9 already owns `config/**`; this update adds no broader ownership.
The support profile pins the exact logging XML. Every JAR, quest resource,
control preset, memory policy and other runtime file retains its prior bytes.
The unfiltered diagnostic and temporary normal-INFO proofs under
`tools/qa/connection-logging/` remain historical. The recorded
[Original Steam session on launcher 422](tools/qa/original-steam-422.json) is
separate evidence of that earlier session, not a test of this logging revision.

The exact support hashes are in `tools/portable-profile.json`. The full MIT
license and provenance also travel inside the native KubeJS payload, so copying
the installed pack preserves the notices.

## Optional keyboard preset

For original ATM9, apply the optional controls preset after the first launch
reaches the title menu and the game closes normally. Author DefaultSettings
replaces options during its first initialization; a pre-first-launch preset may
be overwritten. Full client close/restart retention was not tested.

The launcher can explicitly apply the key-only [keyboard preset](launcher/controls-guide.md).
It preserves the selected game language, graphics and other personal options;
no complete `options.txt` is shipped. It contains 488 expected names, with 159
bound and 329 unbound. The 83 independent vanilla/world inputs use distinct
physical keys. Captured native GUI and input companions retain their original
bindings; this is not a claim that every red pair in Controls disappears.

The namespace is projected from the observed Modified registry by exact BASE
ownership, with all 431 JAR hashes matched to this Original pack. A standalone
Original registry, in-game application and persistence after restart have not
been measured. The native Forge parser and the launcher's parser/Apply/Evaluate
checks passed; detailed provenance and the full-JAR validator are in `tools/keybinds/`.
The original DefaultSettings presets remain unchanged. No JAR, world ability or
permission path changes, so this preset needs no additional Safety profile.

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

The requested private `ru_ru` seed did not establish the actual title language:
Default Settings first boot overwrote it. Persisted post-exit private options show
`lang:en_us` and `pauseOnLostFocus:true`. This is post-exit evidence, not a direct
native language getter or a Russian UI pass. Mod IDs, the read-only Memory flag,
488 measured Options names and normal exit remain valid independently of locale.
No player language, runtime preset, quest or game file is changed by this evidence
correction.

## Singleplayer JourneyMap waypoint generations

The pack-owned startup script records a random world UUID in
`saves/<folder>/lanmc-waypoints-world.json` and associates only the JourneyMap
waypoint directory with that generation. Reusing a world folder preserves its
previous points under `local/lanmc-waypoint-archives/v1/<slot>/<UUID>/waypoints`.
Reopening the same UUID keeps its points; restoring a known UUID restores its
archived points. Existing worlds adopt their points on the first startup.
Map images, game data, JourneyMap settings and remote-server points are unchanged.

The [source/native fixture receipt](tools/qa/journeymap-waypoint-generation-source.json)
separates pinned native API checks and actual Rhino/filesystem fixtures from
Minecraft runtime acceptance. No new full-game launch, real Forge event execution
or real world switch is claimed. Native JourneyMap still queues deathpoint writes
after a minimum three-second sleep plus executor waiting, without rechecking the
world generation. A callback from a previous world can still write a point after
a transition; this policy has no late-deathpoint filter or global writer barrier.
Use one client per game directory; external concurrent edits and power-loss
durability are outside the tested scope. Path/bootstrap failures preserve existing
waypoints and report a warning.

Future author imports must retain `tools/journeymap-policy`, the source helper
`tools/waypoint_source_policy.py`, its receipt `tools/journeymap-waypoints-policy.json`,
the startup script/template, and their client-policy/support pins. Run
`python tools/client-policy/prepare.py --pack . --templates-only --apply` before
cold JAR restoration; after restoration run normal client-policy verification and
`python tools/waypoint_source_policy.py --pack .`. Generation verifies these pins
without rebasing them. Unknown JourneyMap/KubeJS/Rhino or platform bytes stop
publication pending explicit API review; personal waypoint state is never shipped.


## Исправление изоляции меток JourneyMap

Обновлён принадлежащий сборке скрипт: явный выбор Java-перегрузок устраняет неоднозначность настоящих KubeJS/Rhino type wrappers, а корневая ссылка saves принимается только от нативного Minecraft level storage. Дочерние ссылки и подмена корня по-прежнему отклоняются. Метки прежней генерации сохраняются в локальном архиве; обычные старые миры не очищаются по эвристике даты. [Версии и ограничения](tools/journeymap-waypoints-policy.json), [проверки](tools/qa/journeymap-world-isolation-v2.json). Авторские JAR и игровые параметры не изменены.
