# Native upper-memory warning policy

`kubejs/client_scripts/lanmc_memory_warning_policy.js` uses the native Memory
Settings config API to set only the loaded `disableWarnings=true` option before
the initial game-menu panel check. It prevents the upper-memory panel when the
launcher-selected heap exceeds the author's 14336 MiB (14 GiB) recommendation. It imposes
no heap or rendering limit and never rewrites the player's memorysettings.json.
Every other native option and the original author JSON bytes are preserved.

Memory Settings 5.9's ClienModLoaderMixin checks this loaded flag at
ClientModLoader.completeModLoading RETURN. KubeJS 2001 constructs its client
manager and calls PROXY.init/reloadClientScripts before that loading-complete
screen. The earlier low-heap Swing dialog and constructor warning log remain
outside this client-stage policy. This is not a global suppression of log errors.

After an author import retain this source-owned directory and run:

    python tools/client-policy/prepare.py --pack . --templates-only --apply
    # Restore exact author JARs with the pack's existing restore tool.
    python tools/client-policy/prepare.py --pack . --apply

The first stage reports SOURCE_SCRIPTS_READY_NATIVE_API_NOT_CHECKED; it does not
pretend missing author JARs have been verified. Run it before strict support-file
preflight/author restoration, then run the full API stage after all JARs exist.
The template stage restores only a missing owned script from its hash-pinned
template and refuses a conflicting source file. The full native stage validates
the public mutable fields/method in the actual native JARs. The API contract allows updated author JARs with unchanged
public APIs. Changed APIs require review. CI runs this before pack verification.
It does not download mods, rewrite JARs or write personal configs.

`NativeMemory59Probe.java` is source-only. With the exact native Forge runtime,
Memory Settings 5.9, Cupboard 2.7 and Rhino 2001.2.3 on the classpath, run Java 17+
in a fresh separate empty working directory; pass the prepared pack root as its
single argument. For Windows long classpaths use Java's standard @arguments.txt.
The probe copies the author's JSON into that fresh fixture, uses native FMLPaths,
executes the actual pack script with real Rhino NativeJavaClass handling and
checks only disableWarnings changes, personal file bytes and idempotence. Its
small Java.loadClass binding delegates to actual native Java/Rhino classes and
is not a full KubeJS lifecycle/game test. No private paths or logs are shipped.
