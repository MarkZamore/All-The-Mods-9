# Draconic Evolution Render Patcher 1.3.0: static native-site review

This standalone source-only helper parses classfiles with ASM. It does not launch
Minecraft, initialize game classes, apply Mixins, touch a world, or install a mod.
The actual author mod is downloaded separately using its pinned official file.

Read `derenderpatcher-1.3.0-static.json` for the exact mod/provider hashes, scope,
required selectors, authored optional aliases and the explicit no-game limitation.
`derenderpatcher-1.3.0-sites.json` is the measured output, retaining target class,
provider basename, shadow/accessor and exact instruction matches. The two native
Minecraft providers are ordered Forge-patched client first, SRG client second.
The helper is a parser, not a hash authority: before reproducing the report,
verify the author patcher and all seven providers against the pinned report.
Different bytes require a new reviewed proof rather than relabeling this result.

Use JDK17+ and explicit ASM9.8/ASM-tree9.8 files. Write a private UTF8 text file
with one provider JAR path per line, in the order listed by `nativeInputs`.
Do not commit that machine-specific path file. Put compiled classes/output under
an artifact directory outside the pack source/runtime roots.

```text
javac -encoding UTF-8 -cp ASM98;ASM_TREE98 -d OUTPUT_CLASSES tools/qa/derenderpatcher/MixinStaticAudit.java
java -cp OUTPUT_CLASSES;ASM98;ASM_TREE98 MixinStaticAudit AUTHOR_PATCHER.jar PRIVATE_PROVIDER_PATHS.txt OUTPUT.json
```

Use `:` instead of `;` for the Java classpath separator on Unix.

All 21 targets, 3 accessors, 18 shadow fields, 3 shadow methods and one invoker
were present. The 51 injections and 23 direct FIELD/INVOKE selectors were read:
20 sites exist in untransformed native classes; three are authored optional
MCP aliases or the post-Oculus shader hook. Both authored MCP/SRG groups have
one SRG match and zero MCP matches. The mandatory shader RETURN path exists.
All 69 direct external-mod member references resolve against the reviewed files.
This is not full JVM linkage, a shared-target Mixin application, rendered output,
or gameplay acceptance. The user explicitly waived in-game runs for this fix.
