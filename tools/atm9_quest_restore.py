"""Restore a schema2-authorized exact new ATM9 lock without changing legacy import.

The caller owns whole-pack extra-content/support checks and normalizes its
validated display spans first. This helper checks every original BASE row and
all official download bindings before any cache/source writes. No metadata API
or latest-version lookup is used; only missing pinned binaries can be restored.
"""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re

import import_upstream
import atm9_quest_profile as profile

PROJECT_ID = 715572
CF_HOSTS = {"edge.forgecdn.net", "mediafilez.forgecdn.net", "media.forgecdn.net"}
MOJANG_HOSTS = {"piston-data.mojang.com", "launcher.mojang.com"}


def positive(value):
    return type(value) is int and value > 0


def official_url(row, *, client=False):
    url = row.get("sourceUrl")
    if not isinstance(url, str):
        raise ValueError("Missing pinned original download URL: " + row["path"])
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.username or parsed.password or
            parsed.query or parsed.fragment or parsed.port is not None):
        raise ValueError("Original download is not a plain pinned HTTPS URL")
    if client:
        if parsed.hostname not in MOJANG_HOSTS or not re.fullmatch(r"/v1/objects/[0-9a-f]{40}/client\.jar", parsed.path):
            raise ValueError("Not a pinned official Mojang client URL")
        if row.get("sha1") is not None and parsed.path.split("/")[3] != row["sha1"]:
            raise ValueError("Mojang source path differs from its SHA1")
    else:
        filename, file_id = row.get("fileName"), row.get("fileId")
        if (not isinstance(filename, str) or not filename or "/" in filename or "\\" in filename or
                filename != row["path"].rsplit("/", 1)[-1] or not positive(file_id) or not positive(row.get("projectId"))):
            raise ValueError("Missing exact author project/file/filename binding")
        expected = f"/files/{file_id // 1000}/{file_id % 1000:03d}/{filename}"
        if parsed.hostname not in CF_HOSTS or unquote(parsed.path) != expected:
            raise ValueError("Original URL differs from exact CurseForge file identity")
    return url


def validate_author_downloads(upstreamBytes, originalRows):
    """Pure author identity/row/URL check for both load adapters, before writes."""
    upstream = profile.parse(upstreamBytes)
    identity = upstream.get("pack", {}) if isinstance(upstream, dict) else {}
    if (not isinstance(upstream, dict) or type(upstream.get("schemaVersion")) is not int or upstream["schemaVersion"] != 1 or
            type(identity.get("projectId")) is not int or identity["projectId"] != PROJECT_ID or not positive(identity.get("clientFileId")) or
            not isinstance(identity.get("clientArchiveSha256"), str) or
            not re.fullmatch("[0-9a-f]{64}", identity["clientArchiveSha256"]) or
            not isinstance(identity.get("version"), str) or not re.fullmatch(r"[A-Za-z0-9._+-]{1,64}", identity["version"])):
        raise ValueError("Not a data-pinned ATM9 author release")
    files, overrides, client = upstream.get("files"), upstream.get("overrides"), upstream.get("client")
    if (not isinstance(files, list) or not isinstance(overrides, list) or not isinstance(client, dict) or
            any(not isinstance(row, dict) or not row.get("included", True) for row in files)):
        raise ValueError("Invalid active author record groups")
    native = profile.index_rows([*files, *overrides, client], "author BASE")
    supplied = profile.index_rows(originalRows, "caller BASE")
    core = lambda rows: {p: (r["sizeBytes"], r["sha256"]) for p, r in rows.items()}
    if core(native) != core(supplied):
        raise ValueError("Caller original BASE differs from exact new author lock")
    downloads = [(row, False) for row in files] + [(client, True)]
    urls = {}
    for row, is_client in downloads:
        if not row["path"].lower().endswith((".jar", ".zip")):
            raise ValueError("Only declared original binary/client downloads may be restored")
        urls[row["path"]] = official_url(row, client=is_client)
    return {"upstream": upstream, "identity": identity, "rows": native, "downloads": downloads,
            "urls": urls, "overridePaths": {row["path"] for row in overrides}}


def restore_profiled_author(pack, cache, descriptor, upstreamBytes, originalRows):
    """Return a restoration report after complete preflight and exact checks."""
    pack, cache = Path(pack), Path(cache)
    if (not isinstance(descriptor, dict) or set(descriptor) != profile.FIELDS or
            type(descriptor.get("schemaVersion")) is not int or descriptor["schemaVersion"] != 2 or
            descriptor.get("kind") != profile.KIND):
        raise ValueError("Not an explicitly selected schema2 author restore")
    if (descriptor["manifestPath"] != profile.MANIFEST or descriptor["patchTool"] != profile.PATCH_TOOL or
            descriptor["patchToolSha256"] != profile.PATCH_SHA):
        raise ValueError("Unapproved schema2 restore profile/tool")
    if profile.digest(upstreamBytes) != descriptor["upstreamLockSha256"]:
        raise ValueError("Author restore upstream pin differs")
    if profile.resource(pack, "tools/upstream-lock.json").read_bytes() != upstreamBytes:
        raise ValueError("Physical author lock changed before restore")
    checked = validate_author_downloads(upstreamBytes, originalRows)
    identity = checked["identity"]
    if descriptor["sourceVersion"] != identity["version"]:
        raise ValueError("Schema2 descriptor differs from author version")
    # Recheck executable/data pins at this write boundary. The caller already
    # performed full semantic span validation with the shared pure reader.
    manifest = profile.parse(profile.read_pin(pack, profile.MANIFEST, descriptor["manifestSha256"]))
    profile.read_pin(pack, profile.PATCH_TOOL, profile.PATCH_SHA, limit=1024 * 1024)
    if (type(manifest.get("schemaVersion")) is not int or manifest["schemaVersion"] != 2 or
            manifest.get("kind") != profile.PROFILE_KIND or manifest.get("sourceVersion") != identity["version"]):
        raise ValueError("Author restore profile/version differs")
    native, urls, override_paths = checked["rows"], checked["urls"], checked["overridePaths"]
    missing = []
    # Global preflight before even a cache directory or first download exists.
    for row in native.values():
        path = profile.resource(pack, row["path"])
        if not path.exists():
            if row["path"] in override_paths:
                raise ValueError("Missing tracked author override: " + row["path"])
            missing.append(row)
        elif not path.is_file() or not import_upstream.expected_ok(path, row["sizeBytes"], {"sha256": row["sha256"]}):
            raise ValueError("Unknown original BASE resource before restore: " + row["path"])
    payloads, downloaded = [], 0
    for row in missing:
        payload = profile.resource(cache, "locked/" + row["sha256"])
        cached = import_upstream.expected_ok(payload, row["sizeBytes"], {"sha256": row["sha256"]})
        import_upstream.download(urls[row["path"]], payload, row["sizeBytes"], {"sha256": row["sha256"]})
        if not import_upstream.expected_ok(payload, row["sizeBytes"], {"sha256": row["sha256"]}):
            raise ValueError("Pinned original cache validation failed")
        payloads.append((payload, row));downloaded += not cached
    # Every missing payload is verified before installing the first source file.
    for payload, row in payloads:
        import_upstream.install(payload, profile.resource(pack, row["path"]))
    for row in native.values():
        if not import_upstream.expected_ok(profile.resource(pack, row["path"]), row["sizeBytes"], {"sha256": row["sha256"]}):
            raise ValueError("Restored original BASE differs from pinned author data")
    return {"status": "PASS", "authorVersion": identity["version"], "projectId": PROJECT_ID,
            "clientFileId": identity["clientFileId"], "clientArchiveSha256": identity["clientArchiveSha256"],
            "upstreamLockSha256": descriptor["upstreamLockSha256"], "verifiedOriginalRows": len(native),
            "restoredBinaryFiles": [r["path"] for r in missing], "downloadedBinaries": downloaded,
            "metadataFetchPerformed": False, "runtimeAcceptanceClaimed": False}
