"""Source restoration and actual native-API guards for the pack's client policies."""
from pathlib import Path
import copy
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("native_client_policy", ROOT / "tools/client-policy/prepare.py")
policy_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy_tool)


class ClientPolicyTests(unittest.TestCase):
    def test_current_author_public_apis_and_owned_scripts(self):
        report = policy_tool.prepare(ROOT)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["restoredOwnedScripts"], 0)
        self.assertEqual(len(report["nativeApis"]), 2)
        self.assertFalse(report["personalConfigFilesTouched"])

    def test_changed_native_api_requires_review(self):
        policy = json.loads((ROOT / "tools/client-policy/policy.json").read_text())
        changed = copy.deepcopy(policy)
        changed["apiContracts"][0]["fields"][1]["name"] = "removed_disable_warnings_setting"
        with self.assertRaisesRegex(ValueError, "Native member missing/changed"):
            policy_tool.verify_apis(ROOT, changed)

    def test_templates_only_restores_without_mods_but_full_api_check_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root / "tools/client-policy"
            (tool / "scripts").mkdir(parents=True)
            original = ROOT / "tools/client-policy"
            policy = json.loads((original / "policy.json").read_text())
            (tool / "policy.json").write_text(json.dumps(policy))
            for row in policy["scripts"]:
                (tool / row["template"]).write_bytes((original / row["template"]).read_bytes())
            report = policy_tool.prepare(root, apply=True, templates_only=True)
            self.assertEqual(report["status"], "SOURCE_SCRIPTS_READY_NATIVE_API_NOT_CHECKED")
            self.assertFalse(report["nativeApiValidated"])
            self.assertEqual(report["restoredOwnedScripts"], len(policy["scripts"]))
            for row in policy["scripts"]:
                self.assertEqual((root / row["path"]).read_bytes(), (tool / row["template"]).read_bytes())
            with self.assertRaisesRegex(ValueError, "Required native client-policy API"):
                policy_tool.prepare(root)
            with self.assertRaisesRegex(ValueError, "requires --apply"):
                policy_tool.prepare(root, templates_only=True)

    def test_restore_only_missing_owned_script_preserves_personal_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root / "tools/client-policy"
            (tool / "scripts").mkdir(parents=True)
            raw = b"// synthetic owned client policy\n"
            (tool / "scripts/owned.js").write_bytes(raw)
            personal = root / "config/immediatelyfast.json"
            personal.parent.mkdir()
            before = b'{"hud_batching":true,"synthetic_personal":17}\n'
            personal.write_bytes(before)
            policy = {"scripts": [{"path": "kubejs/client_scripts/owned.js", "template": "scripts/owned.js",
                                   "sizeBytes": len(raw), "sha256": policy_tool.digest(raw)}]}
            self.assertEqual(policy_tool.prepare_outputs(root, tool, policy, True), 1)
            self.assertEqual((root / "kubejs/client_scripts/owned.js").read_bytes(), raw)
            self.assertEqual(personal.read_bytes(), before)
            self.assertEqual(policy_tool.prepare_outputs(root, tool, policy, True), 0)
            (root / "kubejs/client_scripts/owned.js").write_bytes(b"// foreign source file\n")
            with self.assertRaisesRegex(ValueError, "Conflicting source script"):
                policy_tool.prepare_outputs(root, tool, policy, True)
            self.assertEqual((root / "kubejs/client_scripts/owned.js").read_bytes(), b"// foreign source file\n")
            self.assertEqual(personal.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
