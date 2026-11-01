# Bounded native Connection logging

The owned `config/log4j2.xml` adds only the native
`net.minecraft.network.Connection` logger at DEBUG. Its disconnect handler logs
the exception at DEBUG, so the previous INFO policy could retain only the brief
disconnect message. Root/other logger levels, appenders, formatting and retention
remain unchanged; Console and ServerGui still filter DEBUG. The JVM argument is
still the pack's declarative `-Dlog4j.configurationFile=config/log4j2.xml`.

This captures diagnostics. It does not fix Steam transport or identify a current
guest failure. No JAR, network method, recipe, quest, control or personal option
is changed. A new real guest attempt is needed to observe its exception.

`native-routing-proof.json` records the before/after synthetic fixture on Java17
with 95 exact Minecraft1.20.1/Forge47.4.0/Log4j2.19.0 libraries and native layout
plugins. Only the candidate writes the labelled Connection DEBUG throwable into
`latest.log`. Unrelated DEBUG, Connection TRACE and Console DEBUG stay absent;
ERROR remains preserved. This is not a real player exception or a game launch.
The older native title report is historical parent-runtime evidence, not a test
of this new logging file or a fresh world/network PASS.

Reproduce with Python3.12+, Java17, a JDK17+ compiler and the exact native Maven
libraries named by `native-libraries.json`:

```text
python tools/qa/connection-logging/verify_native.py --libraries MAVEN_LIBRARY_ROOT --java JAVA17_EXE --javac JAVAC_EXE --work NEW_PRIVATE_QA_DIRECTORY
```

The tool checks all library hashes and the only semantic XML difference, compiles
the source-only labelled fixture with `--release17`, then starts two standalone
JVMs in the private output directory using the production relative config path.
It creates no game/mod/agent JAR and does not touch an installed pack or world.
Raw user logs, account identifiers and local paths are not published.
