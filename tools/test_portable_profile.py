import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import portable_profile as profile_tools
import prepare_pack


def pin(relative, data):
    return {"path": relative, "sizeBytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class WholeTreePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.pack = profile_tools.working_root(Path(self.temporary.name))
        self.original = b"original"
        self.localized = b"localized"
        names = ["mods/base.jar", "config/ftbquests/quests/chapter.snbt",
                 "kubejs/assets/kubejs/lang/en_us.json"]
        records = [pin(name, self.original) for name in names]
        overlays = {name: {"localizedSizeBytes": len(self.localized),
                          "localizedSha256": hashlib.sha256(self.localized).hexdigest()} for name in names[1:]}
        self.profile = {"records": records, "overlays": overlays,
                        "overrides": set(names[1:]), "support": {p: {} for p in profile_tools.SUPPORT}}
        for name in [*names, *profile_tools.SUPPORT, "launcher/pack-owned.txt"]:
            path = self.pack / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.original)
        self.quest = self.pack / names[1]
        self.english = self.pack / names[2]

    def test_mixed_known_original_and_localized_bytes_are_accepted(self):
        self.quest.write_bytes(self.localized)
        result = profile_tools.preflight(self.pack, self.profile, require_all=True)
        self.assertEqual(result["localizedDisplayResources"], 1)

    def test_final_effective_check_requires_all_localized_display_files(self):
        self.quest.write_bytes(self.localized)
        with self.assertRaisesRegex(ValueError, "localization is missing"):
            profile_tools.preflight(self.pack, self.profile, require_all=True, localized_only=True)
        self.english.write_bytes(self.localized)
        self.assertEqual(profile_tools.preflight(self.pack, self.profile, localized_only=True)["localizedDisplayResources"], 2)

    def test_missing_binary_can_be_restored_but_missing_override_is_rejected(self):
        (self.pack / "mods/base.jar").unlink()
        self.assertEqual(profile_tools.preflight(self.pack, self.profile, require_overrides=True)["missingAuthorResources"], 1)
        self.quest.unlink()
        with self.assertRaisesRegex(ValueError, "Missing original author resource"):
            profile_tools.preflight(self.pack, self.profile, require_overrides=True)

    def test_late_corrupt_base_file_prevents_any_normalization_or_import(self):
        self.quest.write_bytes(self.localized)
        self.english.write_bytes(b"X" * len(self.original))
        before = self.quest.read_bytes()
        with patch.object(profile_tools, "load", return_value=self.profile), \
                patch.object(prepare_pack.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "Unknown author resource"):
                prepare_pack.prepare(self.pack, self.pack / "cache", restore_locked_files=True)
        execute.assert_not_called()
        self.assertEqual(self.quest.read_bytes(), before)

    def test_missing_override_prevents_any_normalization_or_download(self):
        self.quest.unlink()
        with patch.object(profile_tools, "load", return_value=self.profile), \
                patch.object(prepare_pack.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "Missing original author resource"):
                prepare_pack.prepare(self.pack, self.pack / "cache", restore_locked_files=True)
        execute.assert_not_called()

    def test_unknown_extra_jar_prevents_any_normalization_or_download(self):
        (self.pack / "mods/unapproved.jar").write_bytes(b"not an author file")
        with patch.object(profile_tools, "load", return_value=self.profile), \
                patch.object(prepare_pack.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "Unexpected original pack content"):
                prepare_pack.prepare(self.pack, self.pack / "cache", restore_locked_files=True)
        execute.assert_not_called()

    def test_bad_import_result_is_rejected_before_applying_localization(self):
        def execute(command, **kwargs):
            if command[2].endswith("import_upstream.py"):
                self.english.write_bytes(b"X" * len(self.original))
        with patch.object(profile_tools, "load", return_value=self.profile), \
                patch.object(prepare_pack.subprocess, "run", side_effect=execute) as commands:
            with self.assertRaisesRegex(ValueError, "Unknown author resource"):
                prepare_pack.prepare(self.pack, self.pack / "cache", restore_locked_files=True)
        self.assertEqual(commands.call_count, 2)
        self.assertEqual(self.quest.read_bytes(), self.original)

    def test_normalized_author_check_rejects_remaining_translated_bytes(self):
        self.quest.write_bytes(self.localized)
        with self.assertRaisesRegex(ValueError, "Unknown author resource"):
            profile_tools.preflight(self.pack, self.profile, require_all=True, original_only=True)


class FixedReviewIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.pack = profile_tools.working_root(Path(self.temporary.name))
        source = profile_tools.working_root(Path(__file__).resolve().parents[1])
        document = json.loads((source / profile_tools.PROFILE).read_text(encoding="utf-8"))
        names = [profile_tools.PROFILE, document["upstreamLock"]["path"],
                 document["unmodifiedImporter"]["path"],
                 document["localization"]["patchTool"]["path"],
                 document["localization"]["manifest"]["path"],
                 *(p["path"] for p in document["supportFiles"]),
                 *(p["path"] for p in document["sourceNotices"])]
        for name in names:
            destination = self.pack / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, destination)

    def test_real_profile_binds_exactly_107_frozen_author_resources(self):
        profile = profile_tools.load(self.pack)
        self.assertEqual(len(profile["records"]), 1794)
        self.assertEqual(len(profile["overlays"]), 107)
        self.assertEqual(set(profile["support"]), profile_tools.SUPPORT)

    def test_changed_patch_tool_cannot_be_approved_by_editing_profile_pin(self):
        document = json.loads((self.pack / profile_tools.PROFILE).read_text(encoding="utf-8"))
        relative = document["localization"]["patchTool"]["path"]
        data = (self.pack / relative).read_bytes() + b"\n# unreviewed change\n"
        (self.pack / relative).write_bytes(data)
        document["localization"]["patchTool"] = pin(relative, data)
        (self.pack / profile_tools.PROFILE).write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unreviewed profile identity"):
            profile_tools.load(self.pack)

    def test_changed_manifest_cannot_be_approved_by_editing_profile_pin(self):
        document = json.loads((self.pack / profile_tools.PROFILE).read_text(encoding="utf-8"))
        relative = document["localization"]["manifest"]["path"]
        data = (self.pack / relative).read_bytes() + b" "
        (self.pack / relative).write_bytes(data)
        document["localization"]["manifest"] = pin(relative, data)
        (self.pack / profile_tools.PROFILE).write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unreviewed profile identity"):
            profile_tools.load(self.pack)

    def test_missing_native_payload_notice_is_rejected(self):
        (self.pack / "kubejs/atm9_ru_quests_license.txt").unlink()
        with self.assertRaisesRegex(ValueError, "Profile resource size/SHA256 mismatch"):
            profile_tools.load(self.pack)


if __name__ == "__main__":
    unittest.main()
