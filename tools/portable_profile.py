"""The reviewed display/logging/key-preset profile on original ATM9 1.1.1.

This does not accept general replacement files, added mods or another pack profile.
The unchanged upstream lock remains the authority for all author payloads.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

import atm9_ru_quests
import atm9_quest_profile

PROFILE = "tools/portable-profile.json"
LOCK_SHA = "bb55c188102bd637b927dadbaa815d8e14e162761bda2abb52dd2cbcd9b2df18"
IMPORTER_SHA = "5c417dd8eb19cabeb7d4062b18428f5d762fbac48c897ea9e6a4b1e84c11accf"
TOOL_SHA = "8be48f103b2f20aebb53c986ff9c1f2dd458c34f8673e9f25c851e3b00bf2cc7"
MANIFEST_SHA = "9ebb5aca30cc15ecdd231e534fc1a77d8af6377943ef9b76b6143e848725fde6"
SUPPORT = {
    "kubejs/assets/kubejs/lang/ru_ru.json", "config/log4j2.xml",
    "launcher/jvm-args.txt", "kubejs/atm9_ru_quests_license.txt",
    "kubejs/atm9_ru_quests_provenance.md",
    "launcher/controls-preset.txt", "launcher/controls-guide.md",
}
NOTICES = {
    "library/licenses/Scriptora-ATM9-MIT.txt", "library/ru-quests-provenance.md",
    "tools/atm9_ru_quests/native-structural-proof.json",
}
AUTHOR_ROOTS = {
    "mods", "config", "kubejs", "scripts", "defaultconfigs", "data",
    "resourcepacks", "shaderpacks", "configureddefaults", "packmenu",
    "datapacks", "resources",
}


def working_root(path: Path) -> Path:
    root = path.resolve(strict=True)
    # The frozen author tree contains long structure-tag names. Keep their bytes
    # and names intact on Windows instead of shortening or renaming resources.
    if os.name == "nt" and not str(root).startswith("\\\\?\\"):
        root = Path("\\\\?\\" + str(root))
    return root


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resource(pack: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or "\\" in relative or ":" in relative or
            any(p in {"", ".", ".."} for p in relative.split("/"))):
        raise ValueError("Unsafe profile resource path")
    target = pack
    for part in relative.split("/"):
        target /= part
        if target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction()):
            raise ValueError("Linked profile resource: " + relative)
    if not target.resolve().is_relative_to(pack):
        raise ValueError("Profile resource leaves pack root")
    return target


def verify_pin(pack: Path, pin: dict, expected_path=None, expected_sha=None):
    relative = pin.get("path")
    if expected_path is not None and relative != expected_path:
        raise ValueError("Unexpected fixed profile resource")
    if expected_sha is not None and pin.get("sha256") != expected_sha:
        raise ValueError("Unreviewed profile identity: " + relative)
    path = resource(pack, relative)
    if (type(pin.get("sizeBytes")) is not int or not path.is_file() or
            path.stat().st_size != pin["sizeBytes"] or digest(path) != pin.get("sha256")):
        raise ValueError("Profile resource size/SHA256 mismatch: " + relative)


def load(pack: Path):
    if not (pack / PROFILE).is_file():
        return None
    doc = json.loads((pack / PROFILE).read_text(encoding="utf-8-sig"))
    if doc.get("schemaVersion") == 2:
        # Opt-in only: the frozen schema1 branch below remains unchanged.
        return load_dynamic(pack, atm9_quest_profile.parse(resource(pack, PROFILE).read_bytes()))
    if (doc.get("schemaVersion"), doc.get("kind"), doc.get("sourceVersion")) != (
            1, "atm9-original-russian-quests-and-logging", "1.1.1"):
        raise ValueError("Unsupported original ATM9 portable profile")
    verify_pin(pack, doc["upstreamLock"], "tools/upstream-lock.json", LOCK_SHA)
    verify_pin(pack, doc["unmodifiedImporter"], "tools/import_upstream.py", IMPORTER_SHA)
    verify_pin(pack, doc["localization"]["patchTool"], "tools/atm9_ru_quests.py", TOOL_SHA)
    verify_pin(pack, doc["localization"]["manifest"], "tools/atm9_ru_quests/manifest.json", MANIFEST_SHA)
    for key, expected in [("supportFiles", SUPPORT), ("sourceNotices", NOTICES)]:
        pins = doc[key]
        if len(pins) != len(expected) or {p["path"] for p in pins} != expected:
            raise ValueError("Unexpected original ATM9 support allowlist")
        for pin in pins:
            verify_pin(pack, pin)
    support = {row["path"]: row for row in doc["supportFiles"]}
    notices = {row["path"]: row for row in doc["sourceNotices"]}
    for source, shipped in [
        ("library/licenses/Scriptora-ATM9-MIT.txt", "kubejs/atm9_ru_quests_license.txt"),
        ("library/ru-quests-provenance.md", "kubejs/atm9_ru_quests_provenance.md"),
    ]:
        if notices[source]["sha256"] != support[shipped]["sha256"]:
            raise ValueError("Native payload omits the exact translation notice")
    lock = json.loads((pack / "tools/upstream-lock.json").read_text(encoding="utf-8-sig"))
    records = [*lock["files"], *lock["overrides"], lock["client"]]
    indexed = {r["path"]: r for r in records}
    if len(indexed) != len(records) or len(records) != 1794:
        raise ValueError("Unexpected original author record set")
    overlays = atm9_ru_quests.load_manifest(pack / "tools/atm9_ru_quests/manifest.json")
    for row in overlays:
        original = indexed.get(row["path"])
        if (original is None or row["originalSha256"] != original["sha256"] or
                row["originalSizeBytes"] != original["sizeBytes"]):
            raise ValueError("Display profile differs from frozen author row: " + row["path"])
        if row["path"] == atm9_ru_quests.ENGLISH and any(
                base64.b64decode(edit["originalBase64"], validate=True) for edit in row["edits"]):
            raise ValueError("Original English fallback changes must be insert-only")
    return {"document": doc, "records": records, "overlays": {r["path"]: r for r in overlays},
            "overrides": {r["path"] for r in lock["overrides"]}, "support": support}


def load_dynamic(pack: Path, doc: dict):
    fields = {"schemaVersion", "kind", "sourceVersion", "upstreamLock", "unmodifiedImporter",
              "questLocalization", "baseReplacements", "supportFiles", "sourceNotices"}
    if (set(doc) != fields or doc.get("kind") != "atm9-original-russian-quests-and-logging" or
            type(doc.get("schemaVersion")) is not int or doc["schemaVersion"] != 2):
        raise ValueError("Unsupported explicit original ATM9 profile")
    verify_pin(pack, doc["upstreamLock"], "tools/upstream-lock.json")
    verify_pin(pack, doc["unmodifiedImporter"], "tools/import_upstream.py", IMPORTER_SHA)
    raw = resource(pack, "tools/upstream-lock.json").read_bytes()
    lock = atm9_quest_profile.parse(raw)
    if doc["sourceVersion"] != lock["pack"]["version"]:
        raise ValueError("Original profile differs from native author version")
    records = [*lock["files"], *lock["overrides"], lock["client"]]
    import atm9_quest_restore
    atm9_quest_restore.validate_author_downloads(raw, records)
    native = atm9_quest_profile.index_rows(records, "original BASE")
    supports = atm9_quest_profile.index_rows(doc["supportFiles"], "support")
    required = SUPPORT - {atm9_quest_profile.RU} - set(native)
    if not required <= set(supports) or set(supports) - (required | {atm9_quest_profile.RU}):
        raise ValueError("Unexpected dynamic original support allowlist")
    notices = atm9_quest_profile.index_rows(doc["sourceNotices"], "source notices")
    if set(notices) != NOTICES:
        raise ValueError("Unexpected dynamic original notice allowlist")
    for pin in [*supports.values(), *notices.values()]:
        verify_pin(pack, pin)
    for source, shipped in [
        ("library/licenses/Scriptora-ATM9-MIT.txt", "kubejs/atm9_ru_quests_license.txt"),
        ("library/ru-quests-provenance.md", "kubejs/atm9_ru_quests_provenance.md"),
    ]:
        if shipped in supports and notices[source]["sha256"] != supports[shipped]["sha256"]:
            raise ValueError("Native payload omits the exact translation notice")
    reviewed = atm9_quest_profile.validate(pack, doc["questLocalization"], raw, records,
                                           doc["baseReplacements"], doc["supportFiles"])
    return {"document": doc, "records": records, "overlays": reviewed["overlays"],
            "overrides": {r["path"] for r in lock["overrides"]}, "support": supports,
            "dynamic": reviewed, "upstreamBytes": raw}


def preflight(pack: Path, profile: dict, *, require_all=False,
              require_overrides=False, original_only=False, localized_only=False):
    """Check the whole present tree before any normalization, import or download."""
    localized = missing = 0
    expected = set()
    for row in profile["records"]:
        rel = row["path"]
        expected.add(rel)
        path = resource(pack, rel)
        if not path.exists():
            missing += 1
            if require_all or (require_overrides and rel in profile["overrides"]):
                raise ValueError("Missing original author resource; restore checkout/full import: " + rel)
            continue
        if not path.is_file():
            raise ValueError("Author resource is not a regular file: " + rel)
        size, current = path.stat().st_size, digest(path)
        original = size == row["sizeBytes"] and current == row["sha256"]
        overlay = profile["overlays"].get(rel)
        translated = overlay is not None and size == overlay["localizedSizeBytes"] and current == overlay["localizedSha256"]
        if not (original or translated) or (original_only and not original):
            raise ValueError("Unknown author resource size/SHA256: " + rel)
        if localized_only and overlay is not None and not translated:
            raise ValueError("Reviewed display localization is missing: " + rel)
        localized += int(translated)
    allowed = expected | set(profile["support"])
    actual = {p.relative_to(pack).as_posix() for root in AUTHOR_ROOTS
              for p in (pack / root).rglob("*") if p.is_file()}
    unknown = actual - allowed
    if unknown:
        raise ValueError("Unexpected original pack content: " + repr(sorted(unknown)[:20]))
    launcher = {p.relative_to(pack).as_posix() for p in (pack / "launcher").rglob("*") if p.is_file()}
    launcher_expected = {"launcher/pack-owned.txt"} | {p for p in profile["support"] if p.startswith("launcher/")}
    if profile.get("dynamic"):
        launcher_expected |= {r["path"] for r in profile["records"] if r["path"].startswith("launcher/")}
    if launcher != launcher_expected:
        raise ValueError("Unexpected original launcher files: " + repr(sorted(launcher)))
    return {"baseResources": len(profile["records"]), "localizedDisplayResources": localized,
            "missingAuthorResources": missing, "newPayloadSupportFiles": len(profile["support"])}
