#!/usr/bin/env python3
"""Verify original ATM9 and only its pinned display/logging additions."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import tomllib
import zipfile

import portable_profile


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(pack: Path) -> dict:
    pack = portable_profile.working_root(pack)
    profile = portable_profile.load(pack)
    lock = json.loads((pack / "tools/upstream-lock.json").read_text(encoding="utf-8-sig"))
    manifest = json.loads((pack / "tools/upstream-manifest.json").read_text(encoding="utf-8-sig"))
    assert lock["pack"]["version"] == manifest["version"] == "1.1.1"
    assert lock["pack"]["minecraftVersion"] == manifest["minecraft"]["version"] == "1.20.1"
    assert manifest["minecraft"]["modLoaders"] == [{"id": "forge-47.4.0", "primary": True}]
    active = lock["files"]
    history = lock.get("historicalFiles", [])
    assert all(row.get("included", True) for row in active), "Inactive row in active files"
    author_ids = {(row["projectID"], row["fileID"]) for row in manifest["files"]}
    locked_ids = {(row["projectId"], row["fileId"]) for row in [*active, *history]}
    assert author_ids == locked_ids, "Author manifest differs from active/history source IDs"
    records = [*active, *lock["overrides"], lock["client"]]
    seen = set()
    for row in records:
        rel = row["path"]
        assert "\\" not in rel and ":" not in rel and not rel.startswith("/")
        assert all(part not in ("", ".", "..") for part in rel.split("/"))
        assert rel.casefold() not in seen, "Duplicate managed path: " + rel
        seen.add(rel.casefold())
        path = pack.joinpath(*PurePosixPath(rel).parts)
        assert path.is_file(), "Missing author file: " + rel
        overlay = profile["overlays"].get(rel) if profile else None
        size = overlay["localizedSizeBytes"] if overlay else row["sizeBytes"]
        expected_sha = overlay["localizedSha256"] if overlay else row["sha256"]
        assert path.stat().st_size == size, "Size mismatch: " + rel
        assert sha256(path) == expected_sha, "SHA256 mismatch: " + rel
    expected_jars = {r["path"] for r in records if r["path"].startswith("mods/") and r["path"].endswith(".jar")}
    actual_jars = {f.relative_to(pack).as_posix() for f in (pack / "mods").rglob("*.jar")}
    assert actual_jars == expected_jars, "Unexpected or missing JAR files"
    author_roots = {"mods", "config", "kubejs", "scripts", "defaultconfigs", "data",
                    "resourcepacks", "shaderpacks", "configureddefaults", "packmenu",
                    "datapacks", "resources"}
    expected_author = {row["path"] for row in records if row["path"].split("/", 1)[0] in author_roots}
    if profile:
        expected_author.update(p for p in profile["support"] if p.split("/", 1)[0] in author_roots)
    actual_author = {f.relative_to(pack).as_posix() for root in author_roots
                     for f in (pack / root).rglob("*") if f.is_file()}
    assert actual_author == expected_author, "Unexpected or missing author content: " + repr(sorted(actual_author ^ expected_author)[:20])
    launcher_files = {f.relative_to(pack).as_posix() for f in (pack / "launcher").rglob("*") if f.is_file()}
    expected_launcher = {"launcher/pack-owned.txt"}
    if profile:
        expected_launcher.add("launcher/jvm-args.txt")
    assert launcher_files == expected_launcher, "Unexpected launcher additions: " + repr(launcher_files)
    portable = json.loads((pack / "portable-pack.json").read_text(encoding="utf-8-sig"))
    assert portable["minecraftVersion"] == "1.20.1"
    assert portable["loader"] == {"type": "forge", "version": "47.4.0"}
    assert portable["clientJar"] == lock["client"]["path"]
    top_ids = defaultdict(list)
    for relative in sorted(actual_jars):
        with zipfile.ZipFile(pack / relative) as jar:
            if "META-INF/mods.toml" in jar.namelist():
                mods = tomllib.loads(jar.read("META-INF/mods.toml").decode("utf-8-sig")).get("mods", [])
                for row in mods:
                    top_ids[row["modId"]].append(relative)
    duplicates = {key: value for key, value in top_ids.items() if len(value) > 1}
    assert not duplicates, "Duplicate top-level Forge mod IDs: " + repr(duplicates)
    required_diagnostics = {"spark", "observable", "crashutilities"}
    assert required_diagnostics <= set(top_ids), "Original diagnostic mods are missing"
    assert "mods/CrashAssistant-forge-1.19-1.20.1-1.10.10.jar" in actual_jars
    return {"authorVersion": "1.1.1", "minecraftVersion": "1.20.1", "forgeVersion": "47.4.0",
            "sourceManifestFiles": len(manifest["files"]), "activeDownloads": len(active),
            "authorOverrides": len(lock["overrides"]), "historicalDuplicates": len(history),
            "verifiedPayloadFiles": len(records), "jarFiles": len(actual_jars),
            "topLevelForgeModIds": len(top_ids), "duplicateTopLevelIds": duplicates,
            "localizedBaseDisplayResources": len(profile["overlays"]) if profile else 0,
            "newPayloadSupportFiles": len(profile["support"]) if profile else 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.pack.resolve())
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
