"""Exercise the full release-verification CLI used by the publish workflow."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import network_logging_policy
import carpets_recipe_policy
import waypoint_source_policy
import shutil


class ReleaseVerificationTests(unittest.TestCase):
    def test_verify_all_checks_assets_beyond_the_sample_without_generating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = root / 'source'
            pack.mkdir()
            (pack / 'config').mkdir()
            source = Path(__file__).resolve().parents[1]
            (pack / 'config/log4j2.xml').write_bytes((source / 'config/log4j2.xml').read_bytes())
            version = json.loads((source / 'portable-pack.json').read_text(encoding='utf-8-sig'))['minecraftVersion']
            (pack / 'portable-pack.json').write_text(json.dumps(waypoint_source_policy.PLATFORM), encoding='utf-8')
            network_logging_policy.prepare(pack)
            # The publication CLI also requires the source-owned recipe policy.
            jar = 'mods/alchemistry-1.20.1-2.3.4.jar'
            (pack / 'mods').mkdir()
            shutil.copyfile(source / jar, pack / jar)
            shutil.copyfile(source / 'launcher/pack-owned.txt', pack / 'launcher/pack-owned.txt')
            carpets_recipe_policy.prepare(pack)
            for relative in [waypoint_source_policy.SCRIPT, waypoint_source_policy.TEMPLATE,
                             waypoint_source_policy.RECEIPT, 'tools/client-policy/policy.json']:
                target = pack / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            native = json.loads((source / waypoint_source_policy.RECEIPT).read_bytes())['nativeModules']
            for row in native:
                shutil.copyfile(source / row['path'], pack / row['path'])
            dist = root / 'dist'
            assets = dist / 'assets'
            assets.mkdir(parents=True)
            rows = []
            for index in range(11):
                payload = bytes([index])
                name = f'asset-{index}.bin'
                (assets / name).write_bytes(payload)
                rows.append({'name': name, 'sizeBytes': len(payload),
                             'sha256': hashlib.sha256(payload).hexdigest()})
            manifest = dist / 'pack-manifest.json'
            manifest.write_text(json.dumps({'assets': rows}), encoding='utf-8')
            original_manifest = manifest.read_bytes()
            command = [sys.executable, str(Path(__file__).with_name('generate_manifest.py')),
                       '--pack', str(pack), '--out', str(dist), '--verify-all']
            passed = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
            self.assertIn('verified 11 of 11 staged assets', passed.stdout)
            self.assertEqual(original_manifest, manifest.read_bytes())
            receipt = pack / 'tools/network-logging-policy.json'
            pinned = receipt.read_bytes()
            receipt.unlink()
            no_policy = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(0, no_policy.returncode)
            self.assertIn('network logging policy invalid', no_policy.stderr)
            self.assertEqual(original_manifest, manifest.read_bytes())
            receipt.write_bytes(pinned)
            recipe_receipt = pack / carpets_recipe_policy.RECEIPT
            recipe_pinned = recipe_receipt.read_bytes()
            recipe_receipt.unlink()
            no_recipe_policy = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(0, no_recipe_policy.returncode)
            self.assertIn('carpets recipe policy invalid', no_recipe_policy.stderr)
            self.assertEqual(original_manifest, manifest.read_bytes())
            recipe_receipt.write_bytes(recipe_pinned)
            waypoint_receipt = pack / waypoint_source_policy.RECEIPT
            waypoint_pinned = waypoint_receipt.read_bytes()
            waypoint_receipt.unlink()
            no_waypoint_policy = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(0, no_waypoint_policy.returncode)
            self.assertIn('waypoint generation policy invalid', no_waypoint_policy.stderr)
            self.assertEqual(original_manifest, manifest.read_bytes())
            waypoint_receipt.write_bytes(waypoint_pinned)
            for row in rows:
                asset = assets / row['name']
                original = asset.read_bytes()
                asset.write_bytes(b'X')
                failed = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(0, failed.returncode, row['name'])
                self.assertIn('hash/size mismatch', failed.stderr)
                self.assertEqual(original_manifest, manifest.read_bytes())
                asset.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
