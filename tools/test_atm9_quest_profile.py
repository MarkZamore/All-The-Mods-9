"""Portable behavioral gates for the opt-in, data-bound native locale reader."""
from __future__ import annotations
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import atm9_quest_profile as q

HERE = Path(__file__).resolve().parent
CHAPTER = "config/ftbquests/quests/chapters/new.snbt"
ALIAS = "atm9.translation.inline." + "a" * 24


def js(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def pin(path, raw):
    return {"path": path, "sizeBytes": len(raw), "sha256": q.digest(raw)}


def whole(path, old, new, *, field=None, before=None, after=None):
    before = old if before is None else before
    after = new if after is None else after
    at = old.index(before) if before else old.rfind(b"}")
    edit = {"originalOffset": at, "localizedOffset": at,
            "originalBase64": base64.b64encode(before).decode(),
            "localizedBase64": base64.b64encode(after).decode()}
    if field is not None:
        edit["displayPath"] = field
    return {"path": path, "originalSha256": q.digest(old), "originalSizeBytes": len(old),
            "localizedSha256": q.digest(new), "localizedSizeBytes": len(new), "edits": [edit]}


class Fixture:
    def __init__(self, root, role="support", empty=False):
        self.root, self.role = root, role
        self.old = {q.EN: js({"k": "English"}), CHAPTER: b'{title:"New quest",quests:[{id:"ABC",tasks:[{type:"item",count:9}]}]}\n',
                    "mods/native.jar": b"pinned author JAR"}
        self.new = dict(self.old)
        self.files = []
        if not empty:
            a, b = b'"New quest"', ('"{' + ALIAS + '}"').encode()
            self.new[CHAPTER] = self.old[CHAPTER].replace(a, b)
            self.files.append(whole(CHAPTER, self.old[CHAPTER], self.new[CHAPTER], field=["title"], before=a, after=b))
            insertion = (',"' + ALIAS + '":"New quest"').encode()
            at = self.old[q.EN].rfind(b"}")
            self.new[q.EN] = self.old[q.EN][:at] + insertion + self.old[q.EN][at:]
            self.files.append(whole(q.EN, self.old[q.EN], self.new[q.EN], before=b"", after=insertion))
        if role == "base":
            self.old[q.RU] = js({"k": "Авторский перевод"})
            self.new[q.RU] = js({"k": "Авторский перевод", ALIAS: "Новый квест"})
            if not empty:
                self.files.append(whole(q.RU, self.old[q.RU], self.new[q.RU]))
            else:
                self.new[q.RU] = self.old[q.RU]
        self.support = [pin(q.RU, js({"k": "English", ALIAS: "Новый квест"}))] if role == "support" else []
        for p, data in self.old.items():
            self.write(p, data)
        if self.support:
            self.write(q.RU, js({"k": "English", ALIAS: "Новый квест"}))
        for rel in [q.PATCH_TOOL, "tools/atm9_ru_future/legacy-1.1.1-manifest.json", "tools/atm9_ru_future/legacy-alias-english.json"]:
            self.write(rel, (HERE / rel.removeprefix("tools/")).read_bytes())
        self.rows = [pin(p, raw) for p, raw in self.old.items()]
        self.upstream = {"schemaVersion": 1, "pack": {"version": "2.0.0", "projectId": 715572,
            "clientFileId": 9876543, "clientArchiveSha256": "b" * 64},
            "files": [r for r in self.rows if r["path"].startswith("mods/")],
            "overrides": [r for r in self.rows if not r["path"].startswith("mods/")]}
        self.raw = js(self.upstream)
        self.descriptor = {"schemaVersion": 2, "kind": q.KIND, "sourceVersion": "2.0.0",
            "upstreamLockSha256": q.digest(self.raw), "manifestPath": q.MANIFEST,
            "manifestSha256": "0" * 64, "patchTool": q.PATCH_TOOL,
            "patchToolSha256": q.PATCH_SHA, "russianRole": role}
        self.refresh()

    def write(self, rel, raw):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def refresh(self):
        profile = {"schemaVersion": 2, "kind": q.PROFILE_KIND, "sourceVersion": "2.0.0", "files": self.files}
        raw = js(profile)
        self.write(q.MANIFEST, raw)
        self.descriptor["manifestSha256"] = q.digest(raw)
        self.replacements = [{"path": r["path"], "originalSha256": r["originalSha256"],
            "originalSizeBytes": r["originalSizeBytes"], "sha256": r["localizedSha256"],
            "sizeBytes": r["localizedSizeBytes"], "kind": "quest-localization", "reason": "Reviewed native display only"} for r in self.files]

    def validate(self):
        return q.validate(self.root, self.descriptor, self.raw, self.rows, self.replacements, self.support)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_future_native_count_and_version_are_data(self):
        f = Fixture(self.root)
        result = f.validate()
        self.assertEqual(len(result["overlays"]), 2)
        self.assertEqual(result["profile"]["sourceVersion"], "2.0.0")
        self.assertEqual(next(r for r in result["effectiveBaseRows"] if r["path"] == "mods/native.jar"), f.rows[-1])

    def test_localized_input_reconstructs_identical_author_context(self):
        f = Fixture(self.root)
        for p in f.new:
            f.write(p, f.new[p])
        self.assertEqual(set(f.validate()["overlays"]), {q.EN, CHAPTER})

    def test_native_author_russian_wins(self):
        f = Fixture(self.root, "base")
        self.assertEqual(f.validate()["russianRole"], "base")

    def test_native_author_russian_may_not_be_overwritten(self):
        f = Fixture(self.root, "base")
        f.new[q.RU] = js({"k": "Наш перевод", ALIAS: "Новый квест"})
        f.files[-1] = whole(q.RU, f.old[q.RU], f.new[q.RU])
        f.refresh()
        with self.assertRaisesRegex(ValueError, "Native author Russian"):
            f.validate()

    def test_native_english_placeholder_may_gain_russian(self):
        f = Fixture(self.root, "base")
        f.old[q.RU] = js({"k": "English"})
        f.write(q.RU, f.old[q.RU])
        f.rows[-1] = pin(q.RU, f.old[q.RU])
        f.upstream["overrides"][-1] = f.rows[-1]
        f.raw = js(f.upstream);f.descriptor["upstreamLockSha256"] = q.digest(f.raw)
        f.new[q.RU] = js({"k": "Русский", ALIAS: "Новый квест"})
        f.files[-1] = whole(q.RU, f.old[q.RU], f.new[q.RU]);f.refresh()
        f.validate()

    def test_empty_unsupported_locale_recipe_does_not_parse_native_locale(self):
        f = Fixture(self.root, "absent", empty=True)
        f.old[q.EN] = b"future author locale format not supported by fallback"
        f.write(q.EN, f.old[q.EN]);f.rows[0] = pin(q.EN, f.old[q.EN])
        f.upstream["overrides"][0] = f.rows[0]
        f.raw = js(f.upstream);f.descriptor["upstreamLockSha256"] = q.digest(f.raw)
        self.assertEqual(f.validate()["overlays"], {})

    def test_absent_russian_is_valid_native_fallback(self):
        self.assertEqual(Fixture(self.root, "absent").validate()["russianRole"], "absent")

    def test_russian_support_cannot_shadow_native_base(self):
        f = Fixture(self.root, "base");f.support = [pin(q.RU, f.old[q.RU])]
        with self.assertRaisesRegex(ValueError, "shadow"):
            f.validate()

    def test_wrong_role_rejected(self):
        f = Fixture(self.root);f.descriptor["russianRole"] = "base"
        with self.assertRaisesRegex(ValueError, "role"):
            f.validate()

    def test_undeclared_descriptor_fields_rejected(self):
        f = Fixture(self.root);f.descriptor["generalReplacements"] = True
        with self.assertRaises(ValueError): f.validate()

    def test_schema_versions_are_integers_not_equal_looking_floats(self):
        f = Fixture(self.root);f.descriptor["schemaVersion"] = 2.0
        with self.assertRaises(ValueError): f.validate()
        f.descriptor["schemaVersion"] = 2
        raw = (self.root / q.MANIFEST).read_bytes().replace(b'"schemaVersion":2', b'"schemaVersion":2.0')
        f.write(q.MANIFEST, raw);f.descriptor["manifestSha256"] = q.digest(raw)
        with self.assertRaises(ValueError): f.validate()

    def test_other_project_or_malformed_archive_identity_rejected_by_pure_reader(self):
        for field, value in [("projectId", 715572.0), ("projectId", 123), ("clientFileId", True), ("clientArchiveSha256", "not a hash")]:
            f = Fixture(self.root);f.upstream["pack"][field] = value
            f.raw = js(f.upstream);f.descriptor["upstreamLockSha256"] = q.digest(f.raw)
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "author release identity"):
                f.validate()

    def test_raw_upstream_pin_not_just_version(self):
        f = Fixture(self.root);f.raw += b" "
        with self.assertRaisesRegex(ValueError, "exact upstream"):
            f.validate()

    def test_caller_may_not_substitute_native_rows(self):
        f = Fixture(self.root);f.rows = copy.deepcopy(f.rows);f.rows[0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "Caller BASE"):
            f.validate()

    def test_profile_pin_rechecked(self):
        f = Fixture(self.root);f.write(q.MANIFEST, (self.root / q.MANIFEST).read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            f.validate()

    def test_tool_pin_rechecked(self):
        f = Fixture(self.root);f.write(q.PATCH_TOOL, b"raise RuntimeError('untrusted')")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            f.validate()

    def test_linked_profile_rejected_before_read_or_import(self):
        f = Fixture(self.root)
        with patch.object(Path, "is_symlink", lambda p: p.name == "generated-profile.json"):
            with self.assertRaisesRegex(ValueError, "Linked"):
                f.validate()

    def test_claimed_display_path_must_match_actual_leaf(self):
        f = Fixture(self.root);f.files[0]["edits"][0]["displayPath"] = ["quests", 0, "title"]
        f.refresh()
        with self.assertRaisesRegex(ValueError, "path does not exist"):
            f.validate()

    def test_span_must_cover_one_whole_string_leaf(self):
        f = Fixture(self.root)
        f.files[0]["edits"][0]["originalOffset"] += 1
        f.refresh()
        with self.assertRaises(ValueError): f.validate()

    def test_tasks_cannot_be_changed_with_display_label(self):
        f = Fixture(self.root)
        before = f.old[CHAPTER];after = before.replace(b"count:9", b"count:8")
        f.files[0] = whole(CHAPTER, before, after, field=["title"], before=b"9", after=b"8")
        f.refresh()
        with self.assertRaisesRegex(ValueError, "actual native leaf"):
            f.validate()

    def test_nested_functional_item_nbt_title_is_not_a_display_field(self):
        f = Fixture(self.root)
        old = b'{title:"Chapter",quests:[{tasks:[{item:{tag:{title:"New quest"}}}]}]}\n'
        new = old.replace(b'"New quest"', ('"{' + ALIAS + '}"').encode())
        f.old[CHAPTER] = old;f.write(CHAPTER, old)
        f.rows[1] = pin(CHAPTER, old);f.upstream["overrides"][1] = f.rows[1]
        f.raw = js(f.upstream);f.descriptor["upstreamLockSha256"] = q.digest(f.raw)
        f.files[0] = whole(CHAPTER, old, new, field=["quests", 0, "tasks", 0, "item", "tag", "title"],
                           before=b'"New quest"', after=('"{' + ALIAS + '}"').encode())
        f.refresh()
        with self.assertRaisesRegex(ValueError, "direct native FTB display path"):
            f.validate()

    def test_direct_native_task_and_image_display_paths_remain_allowed(self):
        self.assertEqual(q.display_field(["quests", 0, "tasks", 0, "title"]), "title")
        self.assertEqual(q.display_field(["quests", 0, "description", 2]), "description")
        self.assertEqual(q.display_field(["images", 0, "hover", 1]), "hover")
        for trail in [["quests", "#", "title"], ["quests", True, "title"], ["quests", 0, "rewards", 0, "item", "tag", "description", 0]]:
            with self.subTest(trail=trail), self.assertRaises(ValueError):
                q.display_field(trail)

    def test_english_alias_must_equal_original_display(self):
        f = Fixture(self.root)
        f.new[q.EN] = f.new[q.EN].replace(b'"New quest"', b'"Changed meaning"')
        f.files[1] = whole(q.EN, f.old[q.EN], f.new[q.EN], before=b"", after=f.new[q.EN][f.old[q.EN].rfind(b"}"):-2])
        f.refresh()
        with self.assertRaisesRegex(ValueError, "semantics"):
            f.validate()

    def test_english_values_remain_unchanged(self):
        f = Fixture(self.root)
        # Duplicate property tricks are rejected even when exact hashes agree.
        addition = b',"k":"Changed"'
        at = f.old[q.EN].rfind(b"}")
        new = f.old[q.EN][:at] + addition + f.old[q.EN][at:]
        f.files = [whole(q.EN, f.old[q.EN], new, before=b"", after=addition)];f.refresh()
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            f.validate()

    def test_new_unused_english_key_cannot_sneak_in(self):
        f = Fixture(self.root)
        addition = b',"unrelated":"Not a display alias"'
        at = f.old[q.EN].rfind(b"}")
        new = f.old[q.EN][:at] + addition + f.old[q.EN][at:]
        f.files = [whole(q.EN, f.old[q.EN], new, before=b"", after=addition)];f.refresh()
        with self.assertRaisesRegex(ValueError, "used native display"):
            f.validate()

    def test_missing_replacement_or_old_hash_rejected(self):
        f = Fixture(self.root);f.replacements.pop()
        with self.assertRaisesRegex(ValueError, "path set"):
            f.validate()
        f.refresh();f.replacements[0]["originalSha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "bound"):
            f.validate()

    def test_jar_or_config_cannot_be_profile_replacement(self):
        f = Fixture(self.root)
        f.files[0]["path"] = "mods/native.jar";f.refresh()
        with self.assertRaisesRegex(ValueError, "cannot modify"):
            f.validate()

    def test_case_duplicates_and_unsafe_paths_rejected(self):
        f = Fixture(self.root);f.rows.append({**f.rows[0], "path": f.rows[0]["path"].upper()})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            f.validate()
        for path in ["../outside", "tools//x", "C:/outside", "mods\\bad.jar"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                q.resource(self.root, path)

    def test_component_translation_preserves_click_style_and_hover(self):
        old = {"text": "Click here", "color": "green", "clickEvent": {"action": "change_page", "value": "ABCDEF"},
               "hoverEvent": {"action": "show_text", "contents": {"text": "More detail"}}}
        new = copy.deepcopy(old);new.pop("text");new["translate"] = ALIAS
        new["hoverEvent"]["contents"] = {"translate": ALIAS[:-1] + "b"}
        result = q.display_aliases(json.dumps(old), json.dumps(new), "description")
        self.assertEqual(result, {ALIAS: "Click here", ALIAS[:-1] + "b": "More detail"})

    def test_component_cannot_change_click_destination(self):
        old = {"text": "Click", "clickEvent": {"action": "open_url", "value": "https://example.org/official"}}
        new = {"translate": ALIAS, "clickEvent": {"action": "open_url", "value": "https://example.org/other"}}
        with self.assertRaisesRegex(ValueError, "non-text"):
            q.display_aliases(json.dumps(old), json.dumps(new), "description")

    def test_component_cannot_drop_style_or_add_gameplay_action(self):
        for new in [{"translate": ALIAS}, {"translate": ALIAS, "color": "green", "clickEvent": {"action": "run_command", "value": "/op someone"}}]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                q.display_aliases('{"text":"Click","color":"green"}', json.dumps(new), "description")

    def test_bare_locale_key_allowed_only_for_native_hover(self):
        self.assertEqual(q.display_aliases("Helpful text", ALIAS, "hover"), {ALIAS: "Helpful text"})
        with self.assertRaises(ValueError):
            q.display_aliases("Helpful text", ALIAS, "description")

    def test_existing_native_locale_reference_is_supported(self):
        self.assertEqual(q.display_aliases("English title", "{atm9.native.title}", "title"), {"atm9.native.title": "English title"})


if __name__ == "__main__":
    unittest.main()
