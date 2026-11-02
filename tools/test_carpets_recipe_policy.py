"""Exact author-recipe source tests; no installed pack, game or real network."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import carpets_recipe_policy as policy

# The unmodified639-byte entry from official Alchemistry2.3.4,
# whole JAR fe993f8e0586a9c65209c230de21225991d9e91c5482a262ce80b3eab2eb02e1.
AUTHOR = base64.b64decode('ewogICJ0eXBlIjogImFsY2hlbWlzdHJ5OmRpc3NvbHZlciIsCiAgImdyb3VwIjogImFsY2hlbWlzdHJ5OmRpc3NvbHZlciIsCiAgImlucHV0IjogewogICAgImNvdW50IjogMSwKICAgICJpbmdyZWRpZW50IjogewogICAgICAidGFnIjogIm1pbmVjcmFmdDpjYXJwZXRzIgogICAgfQogIH0sCiAgIm91dHB1dCI6IHsKICAgICJncm91cHMiOiBbCiAgICAgIHsKICAgICAgICAicHJvYmFiaWxpdHkiOiA2Ni42NjY2NjY2NjY2NjY2NiwKICAgICAgICAicmVzdWx0cyI6IFsKICAgICAgICAgIHsKICAgICAgICAgICAgImNvdW50IjogMiwKICAgICAgICAgICAgIml0ZW0iOiAiY2hlbWxpYjprZXJhdGluIgogICAgICAgICAgfSwKICAgICAgICAgIHsKICAgICAgICAgICAgIml0ZW0iOiAiY2hlbWxpYjp0cmlnbHljZXJpZGUiCiAgICAgICAgICB9CiAgICAgICAgXQogICAgICB9LAogICAgICB7CiAgICAgICAgInByb2JhYmlsaXR5IjogMzMuMzMzMzMzMzMzMzMzMzQsCiAgICAgICAgInJlc3VsdHMiOiBbCiAgICAgICAgICB7CiAgICAgICAgICAgICJpdGVtIjogIm1pbmVjcmFmdDphaXIiCiAgICAgICAgICB9CiAgICAgICAgXQogICAgICB9CiAgICBdLAogICAgInJvbGxzIjogMSwKICAgICJ3ZWlnaHRlZCI6IGZhbHNlCiAgfQp9')


def differences(before, after, pointer=''):
    if isinstance(before, dict) and isinstance(after, dict):
        if set(before) != set(after): return [pointer]
        return [p for key in before for p in differences(before[key], after[key], pointer+'/'+key)]
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after): return [pointer]
        return [p for index,(a,b) in enumerate(zip(before,after)) for p in differences(a,b,pointer+'/'+str(index))]
    return [] if before == after else [pointer]


class CarpetsRecipePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='carpets-source-policy-')
        self.addCleanup(self.temporary.cleanup)
        self.pack = Path(self.temporary.name)
        (self.pack/'mods').mkdir()
        (self.pack/'launcher').mkdir()
        (self.pack/'launcher/pack-owned.txt').write_text('kubejs/**\n',encoding='utf-8')
        self.jar = self.pack/'mods/alchemistry-1.20.1-2.3.4.jar'
        self.write_author(AUTHOR)
        self.assertEqual(len(AUTHOR),639)
        self.assertEqual(hashlib.sha256(AUTHOR).hexdigest(),policy.AUTHOR_SHA)

    def write_author(self, raw):
        with zipfile.ZipFile(self.jar,'w') as archive:
            archive.writestr(policy.AUTHOR_ENTRY,raw)

    def snapshot(self):
        return {p.relative_to(self.pack).as_posix():(p.read_bytes(),p.stat().st_mtime_ns)
                for p in self.pack.rglob('*') if p.is_file()}

    def test_prepare_exact_only_tag_deep_diff_no_global_alias(self):
        initial = set(self.snapshot())
        result = policy.prepare(self.pack)
        self.assertEqual(set(result['changed']),{policy.OVERRIDE,policy.RECEIPT})
        raw = (self.pack/policy.OVERRIDE).read_bytes()
        self.assertEqual(len(raw),644)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),policy.OVERRIDE_SHA)
        before,after = json.loads(AUTHOR),json.loads(raw)
        self.assertEqual(differences(before,after),['/input/ingredient/tag'])
        expected = copy.deepcopy(before);expected['input']['ingredient']['tag']='minecraft:wool_carpets'
        self.assertEqual(after,expected)
        self.assertEqual(set(self.snapshot())-initial,{policy.OVERRIDE,policy.RECEIPT})
        self.assertFalse(any('/tags/' in name for name in self.snapshot()))
        self.assertEqual(result['policy']['recipeId'],'alchemistry:dissolver/carpets')

    def test_verify_is_read_only(self):
        policy.prepare(self.pack);before=self.snapshot()
        result=policy.verify(self.pack)
        self.assertEqual(result['onlyChangedJsonPointer'],'/input/ingredient/tag')
        self.assertEqual(before,self.snapshot())

    def test_prepare_is_idempotent(self):
        policy.prepare(self.pack);before=self.snapshot()
        self.assertEqual(policy.prepare(self.pack)['changed'],[])
        self.assertEqual(before,self.snapshot())

    def test_deleted_known_override_is_restored_without_receipt_rewrite(self):
        policy.prepare(self.pack);receipt=(self.pack/policy.RECEIPT).read_bytes()
        (self.pack/policy.OVERRIDE).unlink()
        self.assertEqual(policy.prepare(self.pack)['changed'],[policy.OVERRIDE])
        self.assertEqual((self.pack/policy.RECEIPT).read_bytes(),receipt)
        policy.verify(self.pack)

    def test_changed_or_author_fixed_recipe_fails_before_any_write(self):
        policy.prepare(self.pack)
        for raw in [AUTHOR+b' ',AUTHOR.replace(policy.LEGACY,policy.CORRECT,1)]:
            with self.subTest(authorFixed=policy.CORRECT in raw):
                self.write_author(raw);before=self.snapshot()
                with self.assertRaisesRegex(ValueError,'changed or was fixed'):policy.prepare(self.pack)
                self.assertEqual(before,self.snapshot())

    def test_unknown_override_is_preserved_without_creating_receipt(self):
        target=self.pack/policy.OVERRIDE;target.parent.mkdir(parents=True)
        target.write_bytes(b'{"userOverride":true}')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Unknown existing recipe override'):policy.prepare(self.pack)
        self.assertEqual(before,self.snapshot())
        self.assertFalse((self.pack/policy.RECEIPT).exists())

    def test_each_installed_marker_is_refused_before_writes(self):
        for name in ('.portable-instance.json','.portable-pack-sync.json','portable-pack-source.json'):
            marker=self.pack/name;marker.write_text('{}',encoding='utf-8');before=self.snapshot()
            with self.subTest(marker=name):
                with self.assertRaisesRegex(ValueError,'not an installed/live pack'):policy.prepare(self.pack)
                self.assertEqual(before,self.snapshot())
            marker.unlink()

    def test_unowned_override_is_refused_before_writes(self):
        (self.pack/'launcher/pack-owned.txt').write_text('config/**\n',encoding='utf-8')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'explicitly source-owned'):policy.prepare(self.pack)
        self.assertEqual(before,self.snapshot())


if __name__=='__main__':unittest.main()
