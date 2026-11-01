# Normal logging restored after temporary Connection diagnostics

The active `config/log4j2.xml` is byte-identical to the preceding normal INFO
policy, SHA256 `6752b55f7a2ede24cef57d8bab70cfeec8f471f7adb72b6fb13b46853151c65d`.
The user accepted real Steam joins and requested removal of unnecessary changes.
There is no explicit Connection DEBUG logger in the active policy. Root/other
levels, appenders, formatting, retention and Console/ServerGui filters retain
their previous values. The JVM argument remains the pack-owned declarative
`-Dlog4j.configurationFile=config/log4j2.xml`.

`temporary-debug-log4j2.xml` retains the removed 4310-byte diagnostic file only
under `tools`, outside the runtime payload. `native-routing-proof.json` and
`reproduced-native-routing.json` remain unchanged historical evidence of that
temporary capture. They are not the current pack policy.

`native-default-info-proof.json` checks the reference INFO policy, historical
bounded DEBUG capture and restored current INFO policy in three standalone
Java 17 JVMs with 95 exact Minecraft 1.20.1/Forge 47.4.0/Log4j 2.19.0 libraries and
native layout plugins. The labelled synthetic Connection throwable reaches the
file only in the historical DEBUG fixture; current INFO retains ERROR while
unrelated DEBUG, Connection TRACE and Console DEBUG remain absent.

Reproduce with Python 3.12+, Java 17, a JDK 17+ compiler and the exact native Maven
libraries named by `native-libraries.json`:

```text
python tools/qa/connection-logging/verify_native.py --libraries MAVEN_LIBRARY_ROOT --java JAVA17_EXE --javac JAVAC_EXE --work NEW_PRIVATE_QA_DIRECTORY
```

The tool verifies every library hash and the exact current/historical XML,
compiles the source-only labelled fixture with `--release 17`, and uses the
production relative config path. It creates no game/mod/agent JAR, starts no
game, and changes no installed pack, running process or personal world.

The real Steam session with Original ATM9 on launcher 422 is recorded in
`../original-steam-422.json`. Neither its success nor this logging cleanup proves
the origin or permanent resolution of an earlier intermittent exception. No CME,
timeout or content patch was applied. Raw user logs and identities stay private.
