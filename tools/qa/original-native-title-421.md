# Original ATM9 native title check

The full native Forge 47.4.0 client reached its title screen in three consecutive
observations and exited normally with code 0. All 432 source JARs and the pinned
shared e4steam JAR matched before and after the run. Actual ModList: 456 total,
453 pack IDs after excluding Minecraft, Forge and the explicitly pinned Steam
component. Render Patcher 1.3.0 was present as a real loaded mod.

Memory Settings was already fully initialized; read-only backing-field observation
found disableWarnings=true with the original minimum8192/maximum14336 values.
The observer initialized no config class and called no getter, setter, load or
save. All 488 preset names match the 488 native Options entries; the registry has
502 entries. This does not claim the optional preset was applied or physically
tested. The source preset bytes remain unchanged.

This check used an isolated launcher candidate intended for421, not a claimed
byte-identical public EXE. See the JSON's exact assembly/adapter/agent hashes.
The scope is title and normal quit only. No world, LAN action, peer connection,
Steam gameplay, skin or Draconic visual result is claimed. The user waived a
separate Draconic rendering test. Remaining ERROR counts and loggers are in the
JSON. Root reviewed the 41 exact signatures against the existing original
baseline; that comparison receipt is referenced by SHA256. This is not a rate
comparison or a claim that all ERROR entries are harmless. No raw logs
or personal paths are published.
