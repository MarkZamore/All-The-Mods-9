import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import import_upstream as importer
import verify_upstream as verifier


class AuthorPayloadDownloadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.target = Path(self.folder.name) / "payload.jar"
        self.payload = b"author-payload"
        self.hashes = {"sha256": hashlib.sha256(self.payload).hexdigest()}

    def test_reuses_only_verified_existing_bytes(self):
        self.target.write_bytes(self.payload)
        with patch.object(importer, "urlopen") as network:
            importer.download("https://edge.forgecdn.net/example", self.target,
                              len(self.payload), self.hashes)
        network.assert_not_called()

    def test_same_size_corruption_is_downloaded_again(self):
        self.target.write_bytes(b"x" * len(self.payload))
        with patch.object(importer, "urlopen", return_value=io.BytesIO(self.payload)) as network:
            importer.download("https://edge.forgecdn.net/example", self.target,
                              len(self.payload), self.hashes)
        network.assert_called_once()
        self.assertEqual(self.target.read_bytes(), self.payload)

    def test_existing_size_without_expected_hash_is_not_reused(self):
        self.target.write_bytes(b"x" * len(self.payload))
        with patch.object(importer, "urlopen", return_value=io.BytesIO(self.payload)) as network:
            importer.download("https://edge.forgecdn.net/example", self.target,
                              len(self.payload), {})
        network.assert_called_once()
        self.assertEqual(self.target.read_bytes(), self.payload)

    def test_failed_download_preserves_existing_file_and_removes_part(self):
        previous = b"previous-byte"
        self.target.write_bytes(previous)
        with patch.object(importer, "urlopen", side_effect=lambda *a, **k: io.BytesIO(b"bad")), \
                patch.object(importer.time, "sleep"):
            with self.assertRaisesRegex(ValueError, "Size/hash mismatch"):
                importer.download("https://edge.forgecdn.net/example", self.target,
                                  len(self.payload), self.hashes)
        self.assertEqual(self.target.read_bytes(), previous)
        self.assertFalse(self.target.with_name("payload.jar.part").exists())


class AuthorCompositionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.pack = Path(self.folder.name)
        (self.pack / "tools").mkdir()
        (self.pack / "mods").mkdir()
        (self.pack / "launcher").mkdir()
        (self.pack / "launcher/pack-owned.txt").write_text("config/**\n", encoding="utf-8")
        records = []
        for index, mod_id in enumerate(["spark", "observable", "crashutilities", None], 1):
            filename = mod_id + ".jar" if mod_id else "CrashAssistant-forge-1.19-1.20.1-1.10.10.jar"
            path = self.pack / "mods" / filename
            with zipfile.ZipFile(path, "w") as jar:
                if mod_id:
                    jar.writestr("META-INF/mods.toml", '[[mods]]\nmodId="' + mod_id + '"\nversion="1"\n')
            records.append({"path": "mods/" + filename, "projectId": index, "fileId": index,
                            "sizeBytes": path.stat().st_size, "sha256": verifier.sha256(path)})
        client = self.pack / "minecraft-1.20.1-client.jar"
        client.write_bytes(b"test-client")
        lock = {"pack": {"version": "1.1.1", "minecraftVersion": "1.20.1"}, "files": records,
                "overrides": [], "client": {"path": client.name, "sizeBytes": client.stat().st_size,
                                              "sha256": verifier.sha256(client)}}
        manifest = {"version": "1.1.1", "minecraft": {"version": "1.20.1",
                    "modLoaders": [{"id": "forge-47.4.0", "primary": True}]},
                    "files": [{"projectID": r["projectId"], "fileID": r["fileId"]} for r in records]}
        (self.pack / "tools/upstream-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        (self.pack / "tools/upstream-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.pack / "portable-pack.json").write_text(json.dumps({"minecraftVersion": "1.20.1",
            "loader": {"type": "forge", "version": "47.4.0"}, "clientJar": client.name}), encoding="utf-8")

    def test_locked_composition_is_accepted(self):
        self.assertEqual(verifier.verify(self.pack)["duplicateTopLevelIds"], {})

    def test_stale_script_or_config_is_rejected(self):
        for relative in ["kubejs/server_scripts/stale.js", "config/stale.toml"]:
            with self.subTest(relative=relative):
                extra = self.pack / relative
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text("stale", encoding="utf-8")
                with self.assertRaisesRegex(AssertionError, "Unexpected or missing author content"):
                    verifier.verify(self.pack)
                extra.unlink()


if __name__ == "__main__":
    unittest.main()
