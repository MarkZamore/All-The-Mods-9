"""New-author archive identity/cache behavior; no network or game execution."""
from pathlib import Path
import hashlib,json,shutil,tempfile,unittest
from unittest.mock import patch
import import_upstream
import atm9_quest_profile as q
import atm9_quest_restore as r


class PinnedAuthorRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='atm9-pinned-restore-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.pack=self.root/'pack';self.cache=self.root/'cache'
        self.values={'mods/base.jar':b'original author binary','config/author.toml':b'author=true\n','minecraft-client.jar':b'original Mojang client fixture'}
        for name,value in self.values.items():self.put(name,value)
        mod={**self.record('mods/base.jar'),'fileName':'base.jar','projectId':123456,'fileId':1000001,'sourceUrl':'https://edge.forgecdn.net/files/1000/001/base.jar'}
        client={**self.record('minecraft-client.jar'),'sha1':hashlib.sha1(self.values['minecraft-client.jar']).hexdigest()}
        client['sourceUrl']='https://piston-data.mojang.com/v1/objects/'+client['sha1']+'/client.jar'
        self.upstream={'schemaVersion':1,'pack':{'version':'2.0.0-fixture','projectId':715572,'clientFileId':9999999,'clientArchiveSha256':'a'*64},'files':[mod],'overrides':[self.record('config/author.toml')],'client':client}
        manifest={'schemaVersion':2,'kind':q.PROFILE_KIND,'sourceVersion':'2.0.0-fixture','files':[]}
        self.put(q.MANIFEST,self.encode(manifest));self.put(q.PATCH_TOOL,(Path(__file__).parent/'atm9_ru_display.py').read_bytes())
        self.desc={'schemaVersion':2,'kind':q.KIND,'sourceVersion':'2.0.0-fixture','upstreamLockSha256':'','manifestPath':q.MANIFEST,'manifestSha256':q.digest(self.encode(manifest)),'patchTool':q.PATCH_TOOL,'patchToolSha256':q.PATCH_SHA,'russianRole':'absent'}
        self.save()
    def encode(self,value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    def put(self,path,raw):
        target=self.pack/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    def record(self,name):return {'path':name,'sha256':q.digest(self.values[name]),'sizeBytes':len(self.values[name])}
    def save(self):
        self.raw=self.encode(self.upstream);self.put('tools/upstream-lock.json',self.raw);self.desc['upstreamLockSha256']=q.digest(self.raw)
        self.rows=[*self.upstream['files'],*self.upstream['overrides'],self.upstream['client']]
    def run_restore(self):return r.restore_profiled_author(self.pack,self.cache,self.desc,self.raw,self.rows)

    def test_new_archive_identity_and_version_require_data_only(self):
        self.assertNotEqual(self.upstream['pack']['clientFileId'],import_upstream.CLIENT_FILE_ID)
        self.assertNotEqual(self.upstream['pack']['clientArchiveSha256'],import_upstream.CLIENT_SHA256)
        with patch.object(import_upstream,'urlopen') as network:
            report=self.run_restore();again=self.run_restore()
        network.assert_not_called();self.assertEqual(report['clientFileId'],9999999)
        self.assertEqual(report['verifiedOriginalRows'],3);self.assertEqual(again['restoredBinaryFiles'],[])
        self.assertFalse(self.cache.exists())

    def test_missing_original_binary_recovered_from_exact_cache_without_network(self):
        row=self.upstream['files'][0];payload=self.cache/'locked'/row['sha256'];payload.parent.mkdir(parents=True);payload.write_bytes(self.values[row['path']]);(self.pack/row['path']).unlink()
        with patch.object(import_upstream,'urlopen') as network:report=self.run_restore()
        network.assert_not_called();self.assertEqual(report['restoredBinaryFiles'],['mods/base.jar']);self.assertEqual(report['downloadedBinaries'],0)
        self.assertEqual((self.pack/'mods/base.jar').read_bytes(),self.values['mods/base.jar'])

    def test_unknown_last_original_row_fails_before_cache_or_download(self):
        (self.pack/'mods/base.jar').unlink();self.put('config/author.toml',b'unknown=true\n')
        with patch.object(import_upstream,'download') as network:
            with self.assertRaisesRegex(ValueError,'Unknown original BASE'):self.run_restore()
        network.assert_not_called();self.assertFalse(self.cache.exists());self.assertFalse((self.pack/'mods/base.jar').exists())
        self.assertEqual((self.pack/'config/author.toml').read_bytes(),b'unknown=true\n')

    def test_missing_tracked_nonbinary_override_is_not_downloaded_or_invented(self):
        (self.pack/'config/author.toml').unlink()
        with patch.object(import_upstream,'download') as network:
            with self.assertRaisesRegex(ValueError,'Missing tracked author override'):self.run_restore()
        network.assert_not_called();self.assertFalse(self.cache.exists())

    def test_wrong_project_or_upstream_binding_fails_without_writes(self):
        for invalid in [123,715572.0]:
            self.upstream['pack']['projectId']=invalid;self.save()
            with self.subTest(projectId=invalid),self.assertRaisesRegex(ValueError,'data-pinned ATM9'):self.run_restore()
        self.assertFalse(self.cache.exists())
        self.upstream['pack']['projectId']=715572;self.save();self.desc['upstreamLockSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'upstream pin differs'):self.run_restore()

    def test_physical_lock_change_is_detected_at_write_boundary(self):
        self.put('tools/upstream-lock.json',self.raw+b' ')
        with self.assertRaisesRegex(ValueError,'Physical author lock changed'):self.run_restore()
        self.assertFalse(self.cache.exists())

    def test_nonofficial_or_wrong_file_url_rejected_even_when_binary_exists(self):
        for url in ['https://example.invalid/files/1000/001/base.jar','https://edge.forgecdn.net/files/1000/002/base.jar']:
            self.upstream['files'][0]['sourceUrl']=url;self.save()
            with self.subTest(url=url),self.assertRaisesRegex(ValueError,'exact CurseForge'):self.run_restore()
        self.assertFalse(self.cache.exists())

    def test_all_missing_payloads_verified_before_first_source_install(self):
        (self.pack/'mods/base.jar').unlink();(self.pack/'minecraft-client.jar').unlink()
        def download(url,target,size,hashes):
            if url.endswith('base.jar'):
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(self.values['mods/base.jar'])
            else:raise OSError('simulated missing second payload')
        with patch.object(import_upstream,'download',side_effect=download):
            with self.assertRaises(OSError):self.run_restore()
        self.assertFalse((self.pack/'mods/base.jar').exists());self.assertFalse((self.pack/'minecraft-client.jar').exists())

    def test_replaced_profile_or_tool_refused_before_source_install(self):
        self.put(q.MANIFEST,b'unknown pinned profile')
        with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):self.run_restore()
        self.assertFalse(self.cache.exists())


if __name__=='__main__':unittest.main(verbosity=2)
