"""Owner workflow guards; actual native full-wrapper evidence is recorded separately."""
from __future__ import annotations
import copy,json,tempfile,unittest,shutil
from pathlib import Path
import atm9_ru_future as f
import update_atm9_quests as w


class OwnerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='atm9-owner-');self.root=Path(self.temp.name)
        self.fresh=self.root/'pristine';self.published=self.root/'published';self.fresh.mkdir();self.published.mkdir()
        self.en={'native':'Native English'}
        self.author={f.EN:f.json_bytes(self.en),'mods/author.jar':b'exact author jar',
            'config/ftbquests/quests/new.snbt':b'{ id: "0123456789ABCDEF", title: "New native title" }\n'}
        self.lock=self.lock_for('1.1.1')
        self.lock_path=self.root/'fresh-lock.json';self.lock_path.write_bytes(f.json_bytes(self.lock))
        for path,value in self.author.items():self.put(self.fresh,path,value);self.put(self.published,path,value)
        self.cache=self.root/'community.json';self.cache.write_bytes(f.json_bytes(f.community_capture({'native':'Русский автора'},{'providerId':'external'},self.en,provider_english=self.en)))
        support={f.RU:f.json_bytes({'native':'Русский автора'}),'kubejs/attribution.txt':b'known attribution',
                 'launcher/pack-owned.txt':b'config\nkubejs\nmods\n'}
        controls={'portable-pack.json':b'{}\n','tools/upstream-lock.json':f.json_bytes(self.lock),
            'tools/portable-profile.json':b'{"published":"profile"}\n','tools/atm9_ru_quests.py':b'# frozen legacy transformer\n',
            'tools/atm9_ru_quests/manifest.json':f.json_bytes({'schemaVersion':2,'kind':f.PROFILE,'sourceVersion':'1.1.1','files':[]})}
        for path,value in {**support,**controls}.items():self.put(self.published,path,value)
        self.snapshot={'schemaVersion':1,'kind':w.KIND,'sourceKind':'original','sourceVersion':'1.1.1',
            'isAuthorTranslationSource':False,'content':[w.pin(self.published,p) for p in sorted({**self.author,**support})],
            'sourceControls':[w.pin(self.published,p) for p in sorted(controls)],'originalBaseRows':self.lock['files']+self.lock['overrides'],
            'supportFiles':[w.pin(self.published,p) for p in support if p!='launcher/pack-owned.txt'],'additionFiles':[],
            'upstreamLock':w.pin(self.published,'tools/upstream-lock.json'),'publicationLock':w.pin(self.published,'tools/portable-profile.json'),
            'localization':{'patchTool':w.pin(self.published,'tools/atm9_ru_quests.py'),'manifest':w.pin(self.published,'tools/atm9_ru_quests/manifest.json')}}

    def tearDown(self):
        # Only this exact owned temporary test tree is removed. Extended paths
        # are required for the deliberately >260-character resource fixture.
        self.assertEqual(self.root.parent.resolve(),Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.root.name.startswith('atm9-owner-'))
        if self.root.exists():shutil.rmtree(w.long_path(self.root))
        self.temp.cleanup()
    def put(self,root,path,value):
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)
    def lock_for(self,version):
        rows=[{'path':p,'sizeBytes':len(v),'sha256':f.sha(v)} for p,v in self.author.items()]
        return {'schemaVersion':1,'pack':{'version':version},'files':[r for r in rows if r['path'].endswith('.jar')],'overrides':[r for r in rows if not r['path'].endswith('.jar')]}
    def update_author(self,version):
        self.lock=self.lock_for(version);self.lock_path.write_bytes(f.json_bytes(self.lock))
        for p,v in self.author.items():self.put(self.fresh,p,v)
    def review(self,name='review',inputs_lock=None):return w.review(self.fresh,self.lock_path,self.published,self.snapshot,self.cache,self.root/name,inputs_lock=inputs_lock)

    def test_current_identical_payload_preserves_legacy_profile_and_support(self):
        report=self.review();out=self.root/'review'
        self.assertEqual(report['mode'],'reuse-frozen-current-publication-profile')
        self.assertEqual(report['changedPublishedPayloadResources'],0)
        update=f.load(out/'required-lock-updates.json')
        self.assertEqual(update['keepPublishedLocalizationPins'],self.snapshot['localization'])
        for row in [self.snapshot['publicationLock'],*self.snapshot['localization'].values()]:
            self.assertEqual((out/'preserved-current'/row['path']).read_bytes(),(self.published/row['path']).read_bytes())
        self.assertEqual(update['preserveAllOtherPublishedSupportPins'],[r for r in self.snapshot['supportFiles'] if r['path']!=f.RU])

    def test_new_author_english_version_not_blocked_by_old_fingerprint_or_count(self):
        self.author[f.EN]=f.json_bytes({'native':'Changed English','added':'Entirely new paragraph'});self.update_author('2.0.0')
        report=self.review();out=self.root/'review'
        self.assertEqual(report['sourceVersion'],'2.0.0');self.assertEqual(report['refreshQueueCount'],2)
        self.assertEqual(f.load(out/'overlay'/f.RU),{})
        update=f.load(out/'required-lock-updates.json')
        self.assertEqual(update['baseReplacements'],[])
        self.assertTrue(update['requiresExplicitOwnerDataIntegration'])
        descriptor=update['proposedDynamicQuestLocalization']
        self.assertEqual(descriptor['schemaVersion'],2)
        self.assertEqual(descriptor['upstreamLockSha256'],f.sha(self.lock_path.read_bytes()))
        self.assertEqual(descriptor['sourceVersion'],'2.0.0')
        self.assertEqual(descriptor['russianRole'],'support')
        self.assertIsNone(update['keepPublishedLocalizationPins'])
        self.assertEqual((self.fresh/'config/ftbquests/quests/new.snbt').read_bytes(),self.author['config/ftbquests/quests/new.snbt'])

    def test_new_real_author_ru_wins_and_is_not_managed_support(self):
        self.author[f.RU]=f.json_bytes({'native':'Новый настоящий авторский перевод'});self.update_author('2.0.0')
        self.review();out=self.root/'review'
        self.assertEqual(f.load(out/'overlay'/f.RU)['native'],'Новый настоящий авторский перевод')
        updates=f.load(out/'required-lock-updates.json')
        self.assertTrue(updates['russianIsNativeBase']);self.assertTrue(updates['removePriorManagedRussianSupportRow'])
        self.assertIsNone(updates['russianSupportPin'])

    def test_unknown_published_personal_config_refused_without_output(self):
        self.put(self.published,'config/personal.toml',b'private=true\n')
        with self.assertRaisesRegex(ValueError,'Unknown or missing published content'):self.review()
        self.assertFalse((self.root/'review').exists())
        self.assertEqual((self.published/'config/personal.toml').read_bytes(),b'private=true\n')

    def test_changed_known_managed_ru_refused_before_any_copy(self):
        self.put(self.published,f.RU,b'unknown managed output')
        with self.assertRaisesRegex(ValueError,'snapshot pin mismatch'):self.review()
        self.assertFalse((self.root/'review').exists())

    def test_unknown_fresh_base_jar_remains_fatal(self):
        self.put(self.fresh,'mods/author.jar',b'unknown changed jar')
        with self.assertRaisesRegex(ValueError,'BASE resource'):self.review()
        self.assertFalse((self.root/'review').exists())

    def test_cached_pinned_retry_deterministic_and_new_cache_requires_explicit_review(self):
        self.review('first');inputs=f.load(self.root/'first/review-inputs.json')
        first=(self.root/'first/overlay'/f.RU).read_bytes()
        self.review('retry',inputs_lock=inputs)
        self.assertEqual(first,(self.root/'retry/overlay'/f.RU).read_bytes())
        newer=f.community_capture({'native':'Новый внешний перевод'},{'providerId':'external'},self.en,provider_english=self.en)
        self.cache.write_bytes(f.json_bytes(newer))
        with self.assertRaisesRegex(ValueError,'Pinned review inputs differ'):self.review('blocked',inputs_lock=inputs)
        self.assertFalse((self.root/'blocked').exists())
        self.review('explicit-update')
        self.assertEqual(f.load(self.root/'explicit-update/overlay'/f.RU)['native'],'Новый внешний перевод')

    def test_generated_output_never_becomes_community_author_source(self):
        invalid=f.load(self.cache);invalid['isGeneratedOutput']=True;self.cache.write_bytes(f.json_bytes(invalid))
        with self.assertRaisesRegex(ValueError,'generated'):self.review()
        self.assertFalse((self.root/'review').exists())

    def test_future_unsupported_locale_emits_empty_review_not_old_version_failure(self):
        self.author[f.EN]=f.json_bytes({'future':['native typed array']});self.update_author('3.0.0')
        report=self.review();out=self.root/'review'
        self.assertEqual(report['payloadResources'],0)
        self.assertIsNotNone(report['translationSkippedReason'])
        updates=f.load(out/'required-lock-updates.json')
        self.assertTrue(updates['removePriorManagedRussianSupportRow'])
        self.assertIsNone(updates['russianSupportPin'])
        self.assertEqual((self.fresh/f.EN).read_bytes(),self.author[f.EN])

    def test_unsupported_native_ru_reports_without_changing_author_bytes(self):
        self.author[f.RU]=b'{ unsupported native JSON }\n';self.update_author('3.0.0')
        report=self.review()
        self.assertEqual(report['payloadResources'],0)
        self.assertIn('Native Russian locale',report['translationSkippedReason'])
        self.assertEqual((self.fresh/f.RU).read_bytes(),self.author[f.RU])
        self.assertEqual((self.published/f.RU).read_bytes(),f.json_bytes({'native':'Русский автора'}))

    def test_toolchain_order_uses_portable_case_sensitive_posix_strings(self):
        paths=[r['path'] for r in w.tools_pins()]
        self.assertEqual(paths,sorted(paths))
        self.assertLess(paths.index('atm9_ru_future/Scriptora-LICENSE.txt'),paths.index('atm9_ru_future/community-source.json'))

    def test_output_cannot_contain_or_overwrite_source(self):
        with self.assertRaisesRegex(ValueError,'separate'):w.review(self.fresh,self.lock_path,self.published,self.snapshot,self.cache,self.fresh/'overlay')
        self.assertFalse((self.fresh/'overlay').exists())

    def test_stage_author_copies_only_locked_originals_and_reports_known_support_exclusion(self):
        staged=self.root/'staged';report=w.stage_author(self.published,self.snapshot,staged)
        self.assertFalse((staged/f.RU).exists())
        self.assertFalse((staged/'kubejs/attribution.txt').exists())
        self.assertFalse(report['managedRussianPromotedToAuthor'])
        self.assertIn(f.RU,{r['path'] for r in report['knownNonAuthorFilesExcluded']})
        self.assertEqual(f.verify_source(w.physical_root(staged),self.lock),{r['path']:r for r in self.lock['files']+self.lock['overrides']})

    def test_stage_author_unknown_content_fails_before_excluding_anything(self):
        self.put(self.published,'config/personal.toml',b'must remain')
        with self.assertRaisesRegex(ValueError,'Unknown or missing'):w.stage_author(self.published,self.snapshot,self.root/'staged')
        self.assertFalse((self.root/'staged').exists())
        self.assertEqual((self.published/'config/personal.toml').read_bytes(),b'must remain')

    def test_long_native_resource_paths_work_without_relaxing_containment(self):
        deep=self.root.joinpath(*(['long_review_source_segment_12345']*8),'published')
        shutil.copytree(self.published,w.long_path(deep))
        report=w.review(self.fresh,self.lock_path,deep,self.snapshot,self.cache,self.root/'deep-review')
        self.assertEqual(report['changedPublishedPayloadResources'],0)
        with self.assertRaisesRegex(ValueError,'separate'):w.check_output(deep/'nested-overlay',w.physical_root(deep))


if __name__=='__main__':unittest.main(verbosity=2)
