"""Exercise the full release-verification CLI used by the publish workflow."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import network_logging_policy


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
            (pack / 'portable-pack.json').write_text(json.dumps({'minecraftVersion': version}), encoding='utf-8')
            network_logging_policy.prepare(pack)
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
