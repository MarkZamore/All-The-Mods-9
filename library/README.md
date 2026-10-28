# ATM9 library metadata

The stable catalogue ID is `all-the-mods-9`; the title, Russian descriptions and
preview are preserved from the existing original ATM9 card. The gameplay source
is ATM9 1.1.1, official CurseForge client file 7097953 (Minecraft 1.20.1,
Forge 47.4.0). Names, versions and unique loaded mod IDs are derived from the
shipped author JAR metadata, including registered JarJar dependencies. Services
JCPlugin and Scalable Cat's Force have no loaded mod ID: they remain visible
library components with `isLoadedMod: false` and do not inflate the counter.

`loaded-mods.json`, when present, records the tested client's actual Forge ModList
and SHA256 of every author JAR. Generation rejects a stale inventory. This
resolves JarJar alternatives using the loader's selected IDs and versions.
Minecraft and Forge platform IDs do not count as pack mods. An absent inventory
uses metadata discovery and requires runtime comparison before publication.
The original 1.1.1 baseline reported 454 ModList entries: 452 author-pack mod
IDs plus Minecraft and Forge. The selected MixinExtras JAR is not a separate
loaded mod ID; unselected older JarJar candidates do not inflate the count.

Project pages retain the previously verified original pack mappings. Restored
Crash Assistant, Crash Utilities, Observable and spark match the official client
manifest/modlist's project IDs 1154099, 371813, 509575 and 361579 respectively.
Nested library mappings were checked against their embedded mod ID, authors,
Maven group/artifact and declared author URL on 2026-10-28. CurseForge is used
where the same project has a page; development libraries without a standalone
CurseForge/Modrinth project use their actual author's source repository.

`fabric_api_base` is the registered Forge implementation from Sinytra's
Forgified Fabric API, not an unrelated Fabric-only JAR. `thermal` is the embedded
ThermalCore project, not Thermal Foundation under a different mod ID. Ponder
links to Creators-of-Create's source rather than the unrelated Ponder for KubeJS
or a third-party standalone port. Nitrogen's author documents it as an internal
library with no CurseForge release. Current Flywheel is bundled; its original
author's CurseForge page explicitly describes that distribution model.

No Modified helper, content or protection mod is part of this metadata source.
Steam transport and the common identity/LAN Java agent are launcher-managed
integration components and are not added as authored pack content here.

A preparation audit on 2026-10-28 opened all 450 distinct official URLs used
by the 455 mapping keys (454 displayed components after native selection).
The primary pages were reachable; plain HTTP tooling returned anti-bot 403s
for many CurseForge URLs, which were verified through the primary site instead
of being incorrectly marked unavailable. The current Almost Unified slug is
`almostunified`; the author client modlist still contains its previous slug.
