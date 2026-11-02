from pathlib import Path
import hashlib
import json
import tempfile
import unittest

import waypoint_source_policy as policy


class WaypointSourceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pack = Path(self.temp.name)
        self.write('launcher/pack-owned.txt', b'kubejs/**\n')
        script = b'// reviewed fixture; not a runtime test\n'
        self.write(policy.SCRIPT, script)
        self.write(policy.TEMPLATE, script)
        row = self.pin(policy.SCRIPT)
        row['template'] = policy.TEMPLATE
        native = []
        for mod_id in sorted(policy.NATIVE_IDS):
            path = 'mods/' + mod_id + '.jar'
            self.write(path, ('fixture ' + mod_id).encode())
            native.append({**self.pin(path), 'modId': mod_id})
        self.receipt = {'schemaVersion': 1, 'kind': 'pack-owned-waypoint-generation-association',
                        'platform': policy.PLATFORM, 'script': row, 'nativeModules': native}
        self.dump(policy.RECEIPT, self.receipt)
        self.dump('portable-pack.json', policy.PLATFORM)
        self.dump('tools/client-policy/policy.json', {'scripts': [
            {**row, 'template': 'scripts/lanmc_journeymap_waypoint_policy.js'}]})

    def write(self, path, raw):
        target = self.pack / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def dump(self, path, value):
        self.write(path, json.dumps(value).encode())

    def pin(self, path):
        raw = (self.pack / path).read_bytes()
        return {'path': path, 'sizeBytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def test_known_source_delivery_is_only_source_pass(self):
        result = policy.verify(self.pack)
        self.assertEqual('PASS_SOURCE_ONLY', result['status'])
        self.assertFalse(result['runtimeOrWorldAcceptanceClaimed'])

    def test_changed_native_author_requires_review(self):
        self.write('mods/journeymap.jar', b'new author version')
        with self.assertRaisesRegex(ValueError, 'changed or is missing'):
            policy.verify(self.pack)

    def test_missing_owned_script_does_not_pass_publication(self):
        (self.pack / policy.SCRIPT).unlink()
        with self.assertRaisesRegex(ValueError, 'changed or is missing'):
            policy.verify(self.pack)

    def test_changed_template_cannot_restore_different_runtime(self):
        self.write(policy.TEMPLATE, b'unknown replacement')
        with self.assertRaisesRegex(ValueError, 'changed or is missing'):
            policy.verify(self.pack)

    def test_template_must_be_in_real_producer_restore_stage(self):
        self.dump('tools/client-policy/policy.json', {'scripts': []})
        with self.assertRaisesRegex(ValueError, 'actual restore stage'):
            policy.verify(self.pack)

    def test_pack_ownership_is_required(self):
        self.write('launcher/pack-owned.txt', b'config/**\n')
        with self.assertRaisesRegex(ValueError, 'ownership'):
            policy.verify(self.pack)

    def test_receipt_native_path_cannot_escape_source(self):
        self.receipt['nativeModules'][0]['path'] = 'mods/../../outside.jar'
        self.dump(policy.RECEIPT, self.receipt)
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            policy.verify(self.pack)

    def test_new_minecraft_platform_requires_native_review(self):
        self.dump('portable-pack.json', {**policy.PLATFORM, 'minecraftVersion': '1.21.1'})
        with self.assertRaisesRegex(ValueError, 'platform changed'):
            policy.verify(self.pack)


if __name__ == '__main__':
    unittest.main()
