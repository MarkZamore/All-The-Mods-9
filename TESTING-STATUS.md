# ATM9 original rebuild verification

Author release: ATM9 1.1.1, Minecraft 1.20.1, Forge 47.4.0.
Verification date: 28 October 2026.

## Reviewed display and diagnostic update, 30 October 2026

The original author lock and all 431 JARs remain unchanged. The explicit
localization profile replaces 106 SNBT resources and appends 325 English keys;
the new Russian language file has 7,538 entries. The source includes the full
MIT license/provenance, also copied verbatim into the native runtime payload.
The additional pack-owned logging configuration/JVM argument changes diagnostic
output and retention, without patching an author JAR.

The actual FTB SNBT parser and native Minecraft display/language serializers
parsed all 145 quest documents. Deep comparison found exactly 327 display-only
changes and 80,167 unchanged other native leaf tags. All 327 display strings
resolve in Russian; 326 English strings are preserved and one existing brace
typo is explicitly corrected. All 7,538 Russian values passed native formatting
and FTB macro checks without an error. This is structural/parser evidence,
not a new game launch, font-rendering or visual translation PASS.

Nine real 107-file CLI checks passed: exact apply/reverse, verify, idempotence,
mixed known states, missing input and unknown original/localized bytes rejected
globally before writes. All 28 original source tests passed and additionally cover whole-tree
preflight, unknown extra JARs, missing overrides, fixed executable/profile pins
and the exact runtime license. The wrapper leaves the original importer and
author lock untouched; it checks all 1,794 original rows before reapplying the
display spans and verifies all effective rows and five new runtime support files.
The actual localized-to-author-to-localized wrapper cycle passed twice. Full
release staging verified all 219 payload asset hashes across 1,801 shipped files;
the native loaded-mod inventory stays at 452 pack IDs. All 455 project-page
mappings, comprising 450 distinct official URLs, remain unchanged.

The historical full-client, error and connection results below describe the
28 October source/launcher versions. No new two-client, menu, Steam-connectivity
or visual-language result is inferred from this data-only publication.

## Author composition and library

- A fresh official client archive download matches 51,433,990 bytes and the
  full SHA256 in README. All 435 exact author manifest IDs are accounted for:
  433 active downloads and two documented historical duplicate entries.
- All 1,360 author overrides, active downloads and the Mojang client match
  their committed sizes and SHA256: 1,794 author payload files. The strict
  composition verifier rejects extra JARs, scripts, configs and resources.
- The payload has 431 JARs. The actual running Forge ModList registered 454
  unique IDs including Minecraft and Forge: **452 pack mod IDs**, including
  selected nested dependencies. All 431 observed author JAR hashes match.
  `library/loaded-mods.json` binds the observed IDs/versions to those exact JARs.
- Original Spark, Observable, Crash Utilities and Crash Assistant remain.
  No Modified content, helper or Safety mod was copied.
- Library descriptions and preview retain the existing ATM9 card. Official
  primary project pages were verified for all 450 distinct source URLs.
- Locked restore is idempotent. Tooling checks cover hash reuse, same-size
  corruption, refusal of size-only cache reuse, interrupted/invalid download
  preserving previous bytes, and rejection of stale scripts/configs.

## Full author baseline: observed

The full native client reached its title screen at 15:10:35 (Asia/Qyzylorda).
A fresh disposable world was created through Minecraft's normal world flow,
joined at 15:14:14 and saved across all dimensions at 15:16:38. Native UI
observation independently confirmed the world. Normal exit code was 0 at
15:17:40. This was a new QA world; no personal world was copied or tested.

The baseline audit contains **97 ERROR events in 56 first-line families**.
These were observed before launcher Steam integration and were not suppressed:

- Three events in two families are QA offline credentials: authentication
  verification and profile key retrieval.
- Nine events in nine families are JEI timing/resource notices at 5/10/15-second
  thresholds. They are environment-sensitive, not attributed to author defects.
- The remaining 85 events in 45 families are recorded baseline behavior.
  Principal callers/IDs include `coremods/field_to_method.js` biome transforms;
  Embeddium internal-mixin taint; six obsolete JEI advanced keys;
  `cataclysm:item/music_disc_maledictus` / Amendments palette-mask size and
  Respriter palettes; `rebornstorage:rs_book`; Mystical Agriculture `ICrop`;
  `client_scripts:ponder/corail.js#111`; `pneumaticcraft:fuel_quality`;
  `gtceu:create_creative_blaze_cake`; missing Ratlantis/CTOV Wares tags;
  Megacells, Extended Pattern Provider, Twilight Delight and Advanced Generators
  loot entries; `occultism:miner/ores/thorium_ore`; `sob:get_prickly_pear`;
  `tconstruct:extra`; Advanced Peripherals Powah name lookups; Moonlight
  `DispenserHelper` lunch basket; Utilitix/Generator Galore JEI; GTCEu empty
  potion inputs; and an oversized conversion list. No blanket root-cause or
  inherited-error claim is made from the game continuing to run.

The QA worker's initial observation timeout was an instrumentation defect,
separate from game ERROR events. Native UI and save/exit evidence independently
established the world result. Private audit SHA256:
`ba78f52e9c442b5260b0a5ff9f7aa444c984f09bf35ffe24eaa391acbcea6a8a`.
Raw logs, account data and local paths are not published.

## Old installation migration: observed

Production sync and instance services migrated independent technical copies of
revision `4450beb81609647f2db0fbb3cb11143176940994` with both a complete sync
ownership marker and the legacy path without that marker. Both passed interrupted
network retry, interrupted-apply recovery, removal of retired managed content,
preservation of five personal-data sentinels and unknown files, and an idempotent
second sync with zero payload download. The source installation remained intact;
no personal world was copied. Correct existing files were reused: 1,790 files,
1,310,575,793 bytes.

A separate exact-hash history proof used the three former managed helper JARs
from published revision `02b2dc9c633b14545cfed24605cecce259542653`:
`atm9-modified-alchemy-wire`, `lanmc-steam-flow` and
`lanminecraft-memory-warnings`. All three were removed from both canonical pack
and instance. The original snapshot stayed unchanged, and the next sync required
zero payload bytes. Launcher migration regression tests: **41 PASS**.
The manifest carries 1,798 historical exact-hash rows separately from active files.
This does not promise registry compatibility or lossless migration of old worlds.

## Launcher integration: observed

The final integrated run used the author's Forge e4steam 0.3.4, SHA256
`33421acbea4d904ac3cefa62ac1d4bd5f62f9e9169b81a4d16a052d2330bc6fc`,
as a launcher-managed component outside the author pack. The only added runtime
mod ID is `e4steam`; all 454 baseline IDs and versions remain unchanged. None
of the author JARs was patched or replaced beyond the documented duplicate
normalization.

- The full integrated client and fresh QA world ran with the game window titled
  exactly **All The Mods 9**.
- Native one-click Open to LAN published the existing integrated server without
  the intermediate LAN parameter screen. The native session became Steam-ready.
  Read-only observations recorded 230 published samples over 744.7 seconds,
  without Steam runtime failure or QA worker timeout.
- The user physically confirmed **Shift+Tab**. Native UI observation confirmed
  the Steam invitation picker opened. No invitation was sent to another person.
- The final run saved all dimensions at 16:41:20 (Asia/Qyzylorda), logged normal
  stopping at 16:41:24 and exited with code 0 at 16:41:26. Read-only process/exit
  evidence confirms completion. The initiator of closing is not attributed.

The earlier integrated run with author transport 0.3.2 tore its runtime down
when the optional Steam process hint stayed false, despite successful Steam API
initialization and LoggedOn. Author 0.3.4 corrected that never-confirmed hint
case. The established true-to-lost guard remains; the author's JAR was not
patched. The launcher now distinguishes successful API authentication from that
optional process hint. These environment and integration fixes did not alter
pack content.

The final read-only log comparison contains **89 ERROR events in 53 raw
first-line families**: 80 events match exact source-baseline signatures, three
are QA offline credential events, five are JEI timing notices, and one is a new
OpenAL event. These counts are not normalized rates and do not imply a general
reduction in errors. No Steam runtime ERROR occurred.

The new event is `com.mojang.blaze3d.audio.OpenAlUtil` reporting
`Deleting stream buffers: Invalid operation` at 16:32:54. It also occurred in
the earlier integrated run, was not observed in the baseline, and its cause
remains unassigned; the world continued running. The unchanged Lootr conversion
list message occurred in a different world phase and is retained for review.
The earlier integrated run also observed a Sculk Shrieker selector-codec error
in generated terrain; it did not recur in the final run. These observations
are explicitly retained, not relabeled as proven inherited errors.

Launcher verification separately passed 99 Steam/authentication cases,
166 Java adapter cases and 93 native preflight targets. These are integration
and mapping evidence, not substitutes for an actual remote client joining.

## Acceptance boundaries and publication

- The native Minecraft Multiplayer screen was **not tested separately**.
- Real overlay invite/join and in-game Multiplayer discovery/join between two
  players were **not tested**: the user confirmed that a second PC/account is
  currently unavailable.
- The skin check is **SKIPPED by the latest explicit user decision**; no visual
  skin PASS is claimed.
- Computer input stopped when the user requested it. Subsequent save/exit facts
  came from read-only evidence; no further app input was performed.
- Final release staging and public download are recorded by the publishing
  revision and manifest; this source report does not itself claim publication.

No raw account logs, local paths, user identifiers or personal worlds are
published. Static checks, one-host success and overlay controls do not represent
two-client connection PASS.
