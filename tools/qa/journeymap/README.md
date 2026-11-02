These fixtures use unmodified JourneyMap5.10.3, Rhino2001.2.3-build10 and the exact Minecraft1.20.1/Forge47.4.0 client classes. They do not start Minecraft, attach to a game or access personal worlds/waypoints. The cache-removal test uses a nonpersistent synthetic point, so native file deletion is not exercised.

Run with explicit paths to Java17, a JDK17+ compiler, the corresponding launcher's shared `libraries` and `versions` folders, the pack's `mods`, and a private empty output directory:

```text
python run_native_public_probe.py --java <java17.exe> --javac <javac.exe> --libraries <libraries> --versions <versions> --mods <mods> --out <private-output>
```

The parser fixture checks16 cases using the real Rhino evaluator and native public Waypoint/cache APIs. The alias fixture reads the actual bundled `mm.jsmappings`, checks native method/field aliases, and evaluates `LevelResource.ROOT.getId()` through Rhino's real remapper. Native logging-in ordering was separately checked from exact class bytecode, including all646 JourneyMap classes; it is not an in-game lifecycle PASS.

The `candidate` files record the reviewed glue and its ten synthetic dispatch checks. Those checks prove bootstrap-failure handling and selection of the native path under the supplied model. They do not post real Forge events or validate the file IO adapter. Only the final reviewed combined pack script is eligible for delivery.

Name-based late-death filtering is optional and has conservative limits documented in the proof. It is not part of this fixture's runtime acceptance. Map image files are outside the waypoint policy's scope.

The current lifecycle uses the public path resolver `getJMWorldDirForWorldId`, which does not call the directory-creation wrapper. The source IO validates an absent target and every existing ancestor before its own guarded creation. The runner also evaluates ten explicit dispatcher-model cases using the current glue on actual Rhino; these are models, not real Forge events. The native death callback delay is a minimum sleep plus executor queuing, without a generation recheck.
