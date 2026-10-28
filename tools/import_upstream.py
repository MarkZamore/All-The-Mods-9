#!/usr/bin/env python3
"""Reproduce the portable ATM9 1.1.1 client from its official upstream export.

Python 3.12 standard library only. From the pack root:
    python tools/import_upstream.py --pack . --cache artifacts/upstream
    python tools/import_upstream.py --pack . --restore-locked-files

An existing preparation cache may contain ATM9-client-1.1.1.zip,
client-file-metadata.json and ATM9-server-1.1.1.zip. The server archive is
only a download cache: its additional files are never installed. Files in
the pack are created or compared byte-for-byte; conflicting files fail.

CurseForge's public website API currently supplies sizes but no hashes.
The client export is pinned below; downloads use its exact project/file IDs,
official HTTPS CDN and size. The first import records SHA-256 in the public
tools/upstream-lock.json. Subsequent imports require those same hashes.
Mojang's client additionally uses Mojang's published SHA-1. No API key is used.
Superseded upstream duplicates are recorded separately in historicalFiles;
active files contain only installed files. The restore mode uses committed hashes only;
it restores omitted binary files and verifies all remaining installed payloads.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import zipfile

PROJECT_ID = 715572
CLIENT_FILE_ID = 7097953
SERVER_FILE_ID = 7097957
CLIENT_SHA256 = "5d7f7b4a3775a3902274311b5d3949367e7da3baaba97a0bf55312d966302a6d"
CLIENT_ARCHIVE = "ATM9-client-1.1.1.zip"
SERVER_SHA256 = "5551e78de29a2d869f5ea97eb6d8e8bd3b57b17cb920dba564292df5b836804a"
EXCLUDED_FILES = {
    "cc-tweaked-1.20.1-forge-1.113.1.jar": "Superseded by upstream bundled override mods/cc-tweaked-1.20.1-forge-1.116.1.jar",
    "oculus-mc1.20.1-1.8.0.jar": "Superseded by upstream Mekalus 1.8.0.1 fork; both register the same oculus mod ID",
}
USER_AGENT = "LANMinecraft-ATM9-UpstreamImporter/1"
CHUNK = 1024 * 1024


def digest(path: Path, algorithm="sha256") -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def fetch_json(url: str):
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=90) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt + 1)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(data)


def safe_relative(value: str) -> str:
    if not value or "\\" in value or ":" in value or "\x00" in value:
        raise ValueError("Unsafe upstream path: " + repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("Unsafe upstream path: " + repr(value))
    return path.as_posix()


def target_path(root: Path, relative: str) -> Path:
    relative = safe_relative(relative)
    target = root / relative
    # Existing symlinks or reparse links may not redirect writes outside the pack.
    for part in [target, *target.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("Refusing linked destination: " + str(part))
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Destination escapes pack: " + relative)
    return target


def expected_ok(path: Path, size: int, hashes: dict[str, str]) -> bool:
    return path.is_file() and path.stat().st_size == size and all(
        digest(path, algorithm).lower() == value.lower() for algorithm, value in hashes.items())


def download(url: str, target: Path, size: int, hashes: dict[str, str]):
    if hashes and expected_ok(target, size, hashes):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        temporary = target.with_name(target.name + ".part")
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=120) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output, CHUNK)
            if not expected_ok(temporary, size, hashes):
                raise ValueError("Size/hash mismatch: " + target.name)
            os.replace(temporary, target)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(attempt + 1)


def install(source: Path, target: Path):
    if target.exists():
        if target.is_file() and source.stat().st_size == target.stat().st_size and digest(source) == digest(target):
            return
        raise ValueError("Existing file differs; refusing to overwrite: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


class ProjectLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            url = dict(attrs).get("href", "")
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.netloc != "www.curseforge.com" or not parsed.path.startswith("/minecraft/"):
                raise ValueError("Nonofficial project link in upstream modlist")
            self.current = {"websiteUrl": url, "title": ""}

    def handle_data(self, data):
        if self.current is not None:
            self.current["title"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.rows.append(self.current)
            self.current = None


def file_url(file_id: int, filename: str) -> str:
    safe_relative(filename)
    if "/" in filename:
        raise ValueError("Upstream filename contains a directory")
    return f"https://edge.forgecdn.net/files/{file_id // 1000}/{file_id % 1000:03d}/{quote(filename)}"


def metadata_hashes(metadata: dict) -> dict[str, str]:
    algorithms = {1: "sha1", 2: "md5"}
    return {algorithms[h["algo"]]: h["value"] for h in (metadata.get("hashes") or []) if h.get("algo") in algorithms}


def extract_overrides(archive: zipfile.ZipFile, prefix: str, pack: Path, cache: Path):
    records = []
    seen = set()
    for item in archive.infolist():
        if not item.filename.startswith(prefix + "/") or item.is_dir():
            continue
        relative = safe_relative(item.filename[len(prefix) + 1:])
        if stat.S_ISLNK(item.external_attr >> 16) or relative.casefold() in seen:
            raise ValueError("Linked or duplicate upstream entry: " + relative)
        seen.add(relative.casefold())
        target = target_path(pack, relative)
        with tempfile.TemporaryDirectory(prefix="override-", dir=cache) as folder:
            temporary = Path(folder) / "payload"
            with archive.open(item) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output, CHUNK)
            install(temporary, target)
        records.append({"path": relative, "sizeBytes": target.stat().st_size, "sha256": digest(target)})
    return records


def restore_locked_files(pack: Path, cache: Path):
    """Restore omitted downloads without contacting mutable file metadata APIs."""
    lock_path = pack / "tools/upstream-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    if (lock.get("schemaVersion") != 1 or lock.get("pack", {}).get("projectId") != PROJECT_ID or
            lock["pack"].get("clientFileId") != CLIENT_FILE_ID or
            lock["pack"].get("clientArchiveSha256") != CLIENT_SHA256):
        raise ValueError("Unexpected ATM9 upstream lock identity")
    seen = set()
    downloads = []
    for record in lock["files"]:
        target = target_path(pack, record["path"])
        key = record["path"].casefold()
        if key in seen:
            raise ValueError("Duplicate path in upstream lock: " + record["path"])
        seen.add(key)
        if record["fileName"] in EXCLUDED_FILES and record.get("included", True):
            raise ValueError("Committed lock lacks portable exclusion: " + record["path"])
        if record.get("included", True):
            downloads.append(record)
        elif target.exists():
            raise ValueError("Excluded upstream file is present: " + record["path"])
    downloads.append(lock["client"])
    # Validate the complete existing tree before downloading or writing any file.
    for record in [*downloads, *lock["overrides"]]:
        relative = record["path"]
        target = target_path(pack, relative)
        size, sha256 = record["sizeBytes"], record["sha256"]
        if (not isinstance(size, int) or isinstance(size, bool) or size < 0 or
                not isinstance(sha256, str) or len(sha256) != 64 or
                any(c not in "0123456789abcdef" for c in sha256)):
            raise ValueError("Invalid size/hash in upstream lock: " + relative)
        if target.exists() and not expected_ok(target, size, {"sha256": sha256}):
            raise ValueError("Existing file differs from committed lock; refusing to overwrite: " + relative)
    for record in lock["overrides"]:
        if not target_path(pack, record["path"]).is_file():
            raise ValueError("Missing upstream override: " + record["path"] + "; restore the checkout or run a full import")
    restored = 0
    for record in downloads:
        target = target_path(pack, record["path"])
        if target.is_file():
            continue
        url = record["sourceUrl"]
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in {"edge.forgecdn.net", "piston-data.mojang.com", "launcher.mojang.com"}
                or parsed.username or parsed.password):
            raise ValueError("Nonofficial locked download URL: " + record["path"])
        payload = cache / "locked" / record["sha256"]
        download(url, payload, record["sizeBytes"], {"sha256": record["sha256"]})
        install(payload, target)
        restored += 1
        print("Restored verified binary: " + record["path"], flush=True)
    print(f"Verified locked pack: {len(downloads)} downloads, {len(lock['overrides'])} overrides; restored {restored}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--restore-locked-files", action="store_true",
                        help="Restore missing downloads from committed SHA-256 lock and verify existing files")
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    pack = args.pack.resolve()
    cache = (args.cache or pack / "artifacts/upstream").resolve()
    pack.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    if args.restore_locked_files:
        restore_locked_files(pack, cache)
        return
    lock_path = pack / "tools/upstream-lock.json"
    old_lock = json.loads(lock_path.read_text(encoding="utf-8-sig")) if lock_path.exists() else {}
    old_files = {(r["projectId"], r["fileId"]): r for r in [*old_lock.get("files", []), *old_lock.get("historicalFiles", [])]}

    client = cache / CLIENT_ARCHIVE
    client_metadata_path = cache / (CLIENT_ARCHIVE + ".metadata.json")
    client_metadata = (json.loads(client_metadata_path.read_text(encoding="utf-8-sig")) if client_metadata_path.exists()
                       else fetch_json(f"https://www.curseforge.com/api/v1/mods/{PROJECT_ID}/files/{CLIENT_FILE_ID}")["data"])
    download(file_url(CLIENT_FILE_ID, client_metadata["fileName"]), client,
             client_metadata["fileLength"], {"sha256": CLIENT_SHA256})
    with zipfile.ZipFile(client) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        links = ProjectLinks()
        links.feed(archive.read("modlist.html").decode("utf-8-sig"))
        if (manifest["name"] != "All the Mods 9" or manifest["version"] != "1.1.1" or
                manifest["minecraft"]["version"] != "1.20.1" or
                manifest["minecraft"]["modLoaders"] != [{"id": "forge-47.4.0", "primary": True}] or
                len(manifest["files"]) != len(links.rows)):
            raise ValueError("Unexpected upstream client manifest or modlist")
        overrides = extract_overrides(archive, manifest["overrides"], pack, cache)
    write_json(cache / "client-manifest.json", manifest)

    metadata_path = cache / "client-file-metadata.json"
    cached_metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig")) if metadata_path.exists() else []
    metadata_by_id = {(r["projectID"], r["fileID"]): r.get("metadata", r) for r in cached_metadata}
    server = cache / "ATM9-server-1.1.1.zip"
    server_entries = {}
    lionfish_cache = cache / "files/5922047/lionfishapi-2.4-Fix.jar"
    lionfish_shipped = pack / "mods/lionfishapi-2.4-Fix.jar"
    if (not lionfish_cache.is_file() and expected_ok(lionfish_shipped, 162767,
            {"sha256": "7f54de417aae331bf39f2847d3029d0976b90b50f217f9b4cc856433d34aee6f"})):
        lionfish_cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(lionfish_shipped, lionfish_cache)
    if not zipfile.is_zipfile(server) and not expected_ok(lionfish_cache, 162767, {"sha1": "b198f38fb27dfc6db490b496d56aa1622d5a5b87"}):
        server_meta_path = cache / "ATM9-server-1.1.1.zip.metadata.json"
        server_meta = (json.loads(server_meta_path.read_text(encoding="utf-8-sig")) if server_meta_path.exists()
                       else fetch_json(f"https://www.curseforge.com/api/v1/mods/{PROJECT_ID}/files/{SERVER_FILE_ID}")["data"])
        print("Fetching pinned upstream server export for the withdrawn Lionfish API file", flush=True)
        download(file_url(SERVER_FILE_ID, server_meta["fileName"]), server, server_meta["fileLength"], {"sha256": SERVER_SHA256})
    if server.is_file() and zipfile.is_zipfile(server):
        if digest(server) != SERVER_SHA256:
            raise ValueError("Server archive differs from pinned official ATM9 1.1.1 export")
        with zipfile.ZipFile(server) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    server_entries.setdefault(PurePosixPath(info.filename).name, []).append(info.filename)

    def import_file(pair):
        row, project = pair
        project_id, file_id = row["projectID"], row["fileID"]
        metadata_url = f"https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}"
        key = project_id, file_id
        locked = old_files.get(key)
        metadata = metadata_by_id.get(key)
        origin_archive = None
        if key == (1001614, 5922047) and metadata is None:
            # This file was withdrawn from CurseForge's file API. The exact jar
            # remains bundled in the author's verified 1.1.1 server export.
            metadata = {"id": file_id, "projectId": project_id, "fileName": "lionfishapi-2.4-Fix.jar", "fileLength": 162767,
                        "hashes": [{"algo": 1, "value": "b198f38fb27dfc6db490b496d56aa1622d5a5b87"}]}
            origin_archive = {"projectId": PROJECT_ID, "fileId": SERVER_FILE_ID, "sha256": SERVER_SHA256,
                              "entry": "Server-Files-1.1.1/mods/lionfishapi-2.4-Fix.jar"}
        if metadata is None and locked is None:
            metadata = fetch_json(metadata_url)["data"]
        if metadata is None:
            if locked is None:
                raise ValueError(f"Upstream file metadata unavailable: project {project_id}, file {file_id} ({project['title']})")
            metadata = {"id": file_id, "projectId": project_id, "fileName": locked["fileName"], "fileLength": locked["sizeBytes"]}
        if metadata.get("id") != file_id or metadata.get("projectId") != project_id:
            raise ValueError("CurseForge returned metadata for another project/file")
        filename, size = metadata["fileName"], metadata["fileLength"]
        url = file_url(file_id, filename)
        page_path = urlsplit(project["websiteUrl"]).path
        if page_path.startswith("/minecraft/mc-mods/") and filename.lower().endswith(".jar"):
            root = "mods"
        elif page_path.startswith("/minecraft/shaders/") and filename.lower().endswith(".zip"):
            root = "shaderpacks"
        elif page_path.startswith("/minecraft/texture-packs/") and filename.lower().endswith(".zip"):
            root = "resourcepacks"
        else:
            raise ValueError("Unsupported upstream category/file combination: " + project["websiteUrl"])
        relative = root + "/" + filename
        record = {"projectId": project_id, "fileId": file_id, "fileName": filename, "path": relative,
                  "sizeBytes": size, "sourceUrl": url, "websiteUrl": project["websiteUrl"],
                  "title": project["title"], "metadataUrl": metadata_url}
        if filename in EXCLUDED_FILES:
            if target_path(pack, relative).exists():
                raise ValueError("Excluded upstream file is already present: " + relative)
            payload = cache / "files" / str(file_id) / filename
            hashes = metadata_hashes(metadata)
            if locked is not None and locked.get("sha256"):
                hashes["sha256"] = locked["sha256"]
            download(url, payload, size, hashes)
            record["sha256"] = digest(payload)
            return dict(record, included=False, reason=EXCLUDED_FILES[filename])
        hashes = metadata_hashes(metadata)
        if locked is not None and locked.get("sha256"):
            if locked["path"] != relative or locked["sizeBytes"] != size or locked["websiteUrl"] != project["websiteUrl"]:
                raise ValueError("Upstream metadata differs from committed lock: " + filename)
            hashes["sha256"] = locked["sha256"]
        target = target_path(pack, relative)
        payload = cache / "files" / str(file_id) / filename
        payload.parent.mkdir(parents=True, exist_ok=True)
        # Reuse only the exact filename and byte size from the official client
        # manifest. No additional server-only files enter the client pack.
        entries = server_entries.get(filename, [])
        if not payload.exists() and len(entries) == 1:
            with zipfile.ZipFile(server) as archive:
                info = archive.getinfo(entries[0])
                if info.file_size == size:
                    with archive.open(info) as source, payload.open("wb") as output:
                        shutil.copyfileobj(source, output, CHUNK)
        download(url, payload, size, hashes)
        install(payload, target)
        record.update(included=True, sha256=digest(payload))
        if origin_archive is not None:
            record["originArchive"] = origin_archive
        return record

    rows = [(row, project) for row, project in zip(manifest["files"], links.rows, strict=True) if row.get("required", True)]
    records, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(import_file, row): row for row in rows}
        for completed, future in enumerate(concurrent.futures.as_completed(pending), 1):
            try:
                records.append(future.result())
            except Exception as error:
                errors.append(str(error))
                print("ERROR: " + str(error), flush=True)
            if completed % 25 == 0 or completed == len(rows):
                print(f"Imported {completed}/{len(rows)} upstream files ({len(errors)} errors)", flush=True)
    if errors:
        write_json(cache / "import-errors.json", errors)
        # Completed files remain cached; the next invocation retries only missing
        # downloads. An incomplete public lock is never presented as a release.
        raise SystemExit("Import incomplete: " + "; ".join(errors))

    versions = fetch_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    version_ref = next(item for item in versions["versions"] if item["id"] == "1.20.1")
    version = fetch_json(version_ref["url"])
    client_download = version["downloads"]["client"]
    client_name = "minecraft-1.20.1-client.jar"
    client_payload = cache / client_name
    download(client_download["url"], client_payload, client_download["size"], {"sha1": client_download["sha1"]})
    install(client_payload, target_path(pack, client_name))
    lock = {"schemaVersion": 1,
            "pack": {"projectId": PROJECT_ID, "clientFileId": CLIENT_FILE_ID, "serverFileId": SERVER_FILE_ID,
                     "version": "1.1.1", "minecraftVersion": "1.20.1", "loader": {"type": "forge", "version": "47.4.0"},
                     "url": "https://www.curseforge.com/minecraft/modpacks/all-the-mods-9",
                     "clientArchiveSha256": CLIENT_SHA256},
            "files": sorted([{k:v for k,v in r.items() if k != "included"} for r in records if r.get("included", True)], key=lambda r: (r["projectId"], r["fileId"])),
            "historicalFiles": sorted([r for r in records if not r.get("included",True)], key=lambda r: (r["projectId"], r["fileId"])),
            "overrides": sorted(overrides, key=lambda r: r["path"]),
            "client": {"path": client_name, "sizeBytes": client_download["size"], "sha1": client_download["sha1"],
                       "sha256": digest(client_payload), "sourceUrl": client_download["url"]}}
    write_json(lock_path, lock)
    print(f"Verified upstream lock: {len(records)} files, {len(overrides)} overrides, Minecraft 1.20.1", flush=True)


if __name__ == "__main__":
    main()
