"""Real prepare/verify schema2 rehearsals on small isolated author snapshots.

These are source restoration checks, not a Minecraft runtime acceptance claim.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import portable_profile as p
import prepare_pack
import verify_upstream
import atm9_ru_future as locale
from test_atm9_quest_profile import Fixture, pin, js, q, HERE, CHAPTER


class OriginalFixture(Fixture):
    def __init__(self, root, role="support", empty=False):
        super().__init__(root, role, empty)
        binary = io.BytesIO()
        with zipfile.ZipFile(binary, "w") as jar:
            jar.writestr("META-INF/mods.toml", 'modLoader="javafml"\nloaderVersion="[47,)"\nlicense="MIT"\n[[mods]]\nmodId="native_author"\nversion="1"\n')
        self.old["mods/native.jar"] = self.new["mods/native.jar"] = binary.getvalue()
        self.write("mods/native.jar", binary.getvalue())
        native_jar = {**pin("mods/native.jar", binary.getvalue()), "projectId": 12345, "fileId": 9000123,
            "fileName": "native.jar", "sourceUrl": "https://edge.forgecdn.net/files/9000/123/native.jar"}
        client = b"future pinned official client bytes"
        self.write("minecraft-1.20.1-client.jar", client)
        self.old["minecraft-1.20.1-client.jar"] = self.new["minecraft-1.20.1-client.jar"] = client
        client_row = {**pin("minecraft-1.20.1-client.jar", client), "sha1": hashlib.sha1(client).hexdigest(),
            "sourceUrl": "https://piston-data.mojang.com/v1/objects/" + hashlib.sha1(client).hexdigest() + "/client.jar"}
        self.upstream["pack"].update(minecraftVersion="1.20.1", loader={"type": "forge", "version": "47.5.0"})
        self.upstream["files"] = [native_jar]
        self.upstream["client"] = client_row
        self.rows = [*self.upstream["files"], *self.upstream["overrides"], client_row]
        self.support = [*self.support]
        for relative in sorted(p.SUPPORT - {q.RU}):
            data = (HERE.parent / relative).read_bytes()
            self.write(relative, data);self.support.append(pin(relative, data))
        self.notices = []
        for relative in sorted(p.NOTICES):
            data = (HERE.parent / relative).read_bytes()
            self.write(relative, data);self.notices.append(pin(relative, data))
        self.write("launcher/pack-owned.txt", b"config\nkubejs\nmods\nlauncher\n")
        importer = (HERE / "import_upstream.py").read_bytes()
        self.write("tools/import_upstream.py", importer)
        self.importer = pin("tools/import_upstream.py", importer)
        self.write("tools/upstream-manifest.json", js({"version": "2.0.0", "minecraft": {"version": "1.20.1",
            "modLoaders": [{"id": "forge-47.5.0", "primary": True}]}, "files": [{"projectID": 12345, "fileID": 9000123}]}))
        self.write("portable-pack.json", js({"schemaVersion": 1, "minecraftVersion": "1.20.1",
            "loader": {"type": "forge", "version": "47.5.0"}, "clientJar": client_row["path"]}))
        self.save()

    def save(self):
        self.raw = js(self.upstream)
        self.write("tools/upstream-lock.json", self.raw)
        self.descriptor["upstreamLockSha256"] = q.digest(self.raw)
        self.refresh()
        self.document = {"schemaVersion": 2, "kind": "atm9-original-russian-quests-and-logging",
            "sourceVersion": "2.0.0", "upstreamLock": pin("tools/upstream-lock.json", self.raw),
            "unmodifiedImporter": self.importer, "questLocalization": self.descriptor,
            "baseReplacements": self.replacements, "supportFiles": self.support, "sourceNotices": self.notices}
        self.write(p.PROFILE, js(self.document))


class OriginalDynamicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="atm9-reader-")
        self.root = Path(self.temp.name)
        self.pack = p.working_root(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self):
        return prepare_pack.prepare(self.pack, self.root / "cache", restore_locked_files=True)

    def test_new_release_ids_archive_version_platform_and_count_need_only_data(self):
        f = OriginalFixture(self.root)
        result = self.prepare()
        self.assertEqual(result["authorVersion"], "2.0.0")
        self.assertNotEqual(f.upstream["pack"]["clientFileId"], 7097953)
        self.assertNotEqual(f.upstream["pack"]["clientArchiveSha256"], "5d7f7b4a3775a3902274311b5d3949367e7da3baaba97a0bf55312d966302a6d")
        first = {r["path"]: (self.root / r["path"]).read_bytes() for r in f.rows}
        self.prepare()
        self.assertEqual(first, {r["path"]: (self.root / r["path"]).read_bytes() for r in f.rows})
        proof = verify_upstream.verify(self.pack)
        self.assertEqual((proof["authorVersion"], proof["forgeVersion"], proof["jarFiles"]), ("2.0.0", "47.5.0", 1))
        self.assertEqual((self.root / "mods/native.jar").read_bytes(), f.old["mods/native.jar"])

    def test_missing_binary_restores_only_exact_pinned_cache(self):
        f = OriginalFixture(self.root)
        row = f.upstream["files"][0]
        cached = self.root / "cache/locked" / row["sha256"]
        cached.parent.mkdir(parents=True);cached.write_bytes(f.old[row["path"]])
        (self.root / row["path"]).unlink()
        self.prepare()
        self.assertEqual((self.root / row["path"]).read_bytes(), f.old[row["path"]])
        verify_upstream.verify(self.pack)

    def test_future_native_ru_is_base_and_keeps_real_author_translation(self):
        f = OriginalFixture(self.root, "base")
        self.prepare();self.prepare()
        self.assertEqual(json.loads((self.root / q.RU).read_bytes())["k"], "Авторский перевод")
        self.assertNotIn(q.RU, p.load(self.pack)["support"])
        verify_upstream.verify(self.pack)

    def test_unsupported_locale_empty_profile_is_nonblocking_native_fallback(self):
        f = OriginalFixture(self.root, "absent", empty=True)
        raw = js({"future": ["author native format"]})
        f.old[q.EN] = f.new[q.EN] = raw;f.write(q.EN, raw)
        f.upstream["overrides"][0] = pin(q.EN, raw);f.rows = [*f.upstream["files"], *f.upstream["overrides"], f.upstream["client"]]
        f.save()
        self.prepare();self.prepare()
        self.assertEqual((self.root / q.EN).read_bytes(), raw)
        self.assertFalse((self.root / q.RU).exists())
        self.assertEqual(verify_upstream.verify(self.pack)["localizedBaseDisplayResources"], 0)

    def test_unknown_jar_bytes_fail_before_normalize_or_download(self):
        f = OriginalFixture(self.root)
        (self.root / "mods/native.jar").write_bytes(b"unrecognized JAR")
        with patch.object(prepare_pack.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "Unknown author"):
                self.prepare()
            run.assert_not_called()
        self.assertEqual((self.root / CHAPTER).read_bytes(), f.old[CHAPTER])
        self.assertFalse((self.root / "cache").exists())

    def test_unknown_config_fail_before_normalize_without_discard(self):
        f = OriginalFixture(self.root)
        f.write("config/unreviewed.toml", b"keep = true\n")
        with patch.object(prepare_pack.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "Unexpected original pack content"):
                self.prepare()
            run.assert_not_called()
        self.assertEqual((self.root / "config/unreviewed.toml").read_bytes(), b"keep = true\n")
        self.assertEqual((self.root / CHAPTER).read_bytes(), f.old[CHAPTER])

    def test_missing_tracked_override_fail_before_normalize(self):
        f = OriginalFixture(self.root)
        (self.root / CHAPTER).unlink()
        with patch.object(prepare_pack.subprocess, "run") as run:
            with self.assertRaises((ValueError, OSError)):
                self.prepare()
            run.assert_not_called()
        self.assertFalse((self.root / "cache").exists())

    def test_extra_replacement_or_support_path_not_authorized(self):
        f = OriginalFixture(self.root)
        f.document["baseReplacements"].append({**f.replacements[0], "path": "mods/native.jar"})
        f.write(p.PROFILE, js(f.document))
        with self.assertRaises(ValueError): p.load(self.pack)
        f.save();f.document["supportFiles"].append(pin("mods/custom.jar", b"added"));f.write(p.PROFILE, js(f.document))
        with self.assertRaisesRegex(ValueError, "allowlist"):
            p.load(self.pack)

    def test_invalid_author_download_binding_fails_before_normalize(self):
        f = OriginalFixture(self.root)
        f.upstream["files"][0]["sourceUrl"] = "https://example.org/unreviewed.jar"
        f.save()
        with patch.object(prepare_pack.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "CurseForge"):
                self.prepare()
            run.assert_not_called()
        self.assertEqual((self.root / CHAPTER).read_bytes(), f.old[CHAPTER])
        self.assertFalse((self.root / "cache").exists())

    def test_actual_future_merge_output_activates_with_author_community_and_manual_priority(self):
        f = OriginalFixture(self.root, "base", empty=True)
        en = {"k": "English", "community": "Community English", "manual": "Manual English",
              "stale": "Changed English", "fresh": "New untranslated English"}
        raw = locale.json_bytes(en)
        f.old[q.EN] = f.new[q.EN] = raw;f.write(q.EN, raw)
        f.upstream["overrides"][0] = pin(q.EN, raw)
        f.rows = [*f.upstream["files"], *f.upstream["overrides"], f.upstream["client"]]
        fresh = self.root / "pristine-input"
        for row in f.rows:
            target = fresh / row["path"];target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.old[row["path"]])
        community = locale.community_capture({"k": "Внешний", "community": "Новый перевод сообщества"},
            {"providerId": "reviewed-author"}, en, provider_english=en)
        manual = {"schemaVersion": 1, "kind": locale.KIND, "entries": {
            key: {"text": text, "englishFingerprint": locale.fp(value), "decision": "translated"}
            for key, value, text in [("k", en["k"], "Наш"), ("community", en["community"], "Старый запасной"),
                ("manual", en["manual"], "Проверенный ручной перевод"), ("stale", "Previous English", "Устаревший перевод")]}}
        overlay, profile, _, report = locale.prepare(fresh, f.upstream, manual, community, {"files": []}, {}, [])
        f.files = profile["files"];f.save()
        self.prepare();self.prepare()
        actual = json.loads((self.root / q.RU).read_bytes())
        self.assertEqual(actual["k"], "Авторский перевод")
        self.assertEqual(actual["community"], "Новый перевод сообщества")
        self.assertEqual(actual["manual"], "Проверенный ручной перевод")
        self.assertNotIn("stale", actual);self.assertNotIn("fresh", actual)
        self.assertEqual({r["key"] for r in report["refreshQueue"]}, {"stale", "fresh"})
        self.assertEqual((self.root / CHAPTER).read_bytes(), f.old[CHAPTER])
        self.assertEqual((self.root / q.EN).read_bytes(), raw)
        verify_upstream.verify(self.pack)


if __name__ == "__main__":
    unittest.main()
