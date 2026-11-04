# Pack-owned launcher runtime QA

This repository owns the identity, fixture defaults and historical content scenarios in `launcher-runtime-contract.json`. They are QA inputs only: no game options, distributed JVM settings, JARs or locks are changed. The declared loader must match `portable-pack.json`; changing the pack platform requires reviewing this QA declaration too.

The three retired helper prefixes were moved from the shared launcher's historical probe. Their authoritative exact paths, sizes and SHA256 already live in [../legacy-files.json](../legacy-files.json). The shared migration runner still verifies the actual archived manifest and bytes; this contract does not replace those pins.

Only this pack's existing source checks and publication workflow apply to a pack-only release. Do not run LANMinecraft's full/core Release gate again merely to publish these QA files. If launcher runtime/adapter code changes, its own universal launcher gate remains necessary. Existing [../../.github/workflows/publish.yml](../../.github/workflows/publish.yml) continues to validate actual content before publication.

Use the shared `tools/ForgeRuntimeQa` and `tools/PackMigrationQa` from a reviewed launcher source checkout. Build that specific tool once; this thin entrypoint does not build or execute anything automatically:

```powershell
tools/qa/launcher-runtime.ps1 -LauncherRoot <launcher-checkout> -RunnerArguments @('prepare', '<new-artifacts/agent-runs/task/fixture>', '--source', '<independent-pack-source>', '--mode', 'baseline')
tools/qa/launcher-runtime.ps1 -LauncherRoot <launcher-checkout> -RunnerArguments @('launch', '<fixture>', '--label', 'baseline-01', '--agent', '<forge-runtime-qa-agent.jar>', '--fresh-world', 'ATM9QaFresh')
tools/qa/launcher-runtime.ps1 -LauncherRoot <launcher-checkout> -Tool Migration -RunnerArguments @('<old-installation>', '<staged-distribution>')
```

The native runner is scoped to Minecraft 1.20.1 Forge, shared by all packs on that platform. It waits for explicit `ready` after the actual menu; `audit` and `stop` retain the same native lifecycle guards. Runtime acceptance and comparison follow the latest agreed scope for this pack, including actual client/world readiness and explicit analysis of changed ERROR signatures. A prepared manifest or server Done is not a full-client result. Unperformed visual, two-account, Steam or model-conversation checks remain unverified.

Existing evidence under `tools/qa` keeps its original revision and limitations. This QA-only separation does not claim a fresh gameplay PASS or rerun a test. Use one current independent stand, retain its `RUN.json`, check the shared 50 GiB budget, and remove owned bulky runtime copies after producing the compact reports. Personal worlds and active installations are never the stand.
