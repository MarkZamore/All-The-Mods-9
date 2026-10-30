"""Behavioral gates for source ownership, future fallback and exact-byte restoration."""
from __future__ import annotations
import base64,copy,hashlib,json,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
import atm9_ru_future as f
import atm9_ru_display as d


HERE=Path(__file__).resolve().parent
RESEARCH=HERE.parents[1]


def fallback(en,text='Наш перевод',**extra):
    return {'englishFingerprint':f.fp(en),'text':text,'decision':'translated',**extra}


def manual(entries=None,**extra):
    return {'schemaVersion':1,'kind':f.KIND,'entries':entries or {},**extra}


def community(en=None,ru=None,**extra):
    ru=ru or {};en=en or {}
    return f.community_capture(ru,{'providerId':'test-author',**extra},en,provider_english=en)


def row(path,a,b,edits):
    return {'path':path,'originalSha256':f.sha(a),'originalSizeBytes':len(a),
            'localizedSha256':f.sha(b),'localizedSizeBytes':len(b),'edits':edits}


def display_row(path,a,b,old,new,display_path=None):
    at=a.index(old)
    return row(path,a,b,[{'originalOffset':at,'localizedOffset':at,
        'originalBase64':base64.b64encode(old).decode(),
        'localizedBase64':base64.b64encode(new).decode(),
        'displayPath':display_path or ['title']}])


class MergeTests(unittest.TestCase):
    def run_merge(self,en,native=None,ext=None,own=None,rows=None):
        return f.merge(en,native or {},ext or community(),own or manual(),rows or {})

    def test_real_native_author_translation_wins(self):
        values,report=self.run_merge({'k':'English'},{'k':'Авторский перевод'},community({'k':'English'},{'k':'Сообщество'}),manual({'k':fallback('English')}))
        self.assertEqual(values['k'],'Авторский перевод')
        self.assertEqual(report['sources']['k'],'native-author')
        self.assertNotIn('k',report['ownedEntries'])

    def test_new_external_value_replaces_our_reviewed_correction(self):
        own=manual({'k':fallback('English',replacesReviewedCommunityFingerprint=f.fp('Старая ошибка'),reviewedCommunityProviderId='test-author')})
        old=community({'k':'English'},{'k':'Старая ошибка'})
        fixed,report=self.run_merge({'k':'English'},ext=old,own=own)
        self.assertEqual(fixed['k'],'Наш перевод')
        new=f.community_capture({'k':'Новый авторский перевод'},{'providerId':'test-author'},{'k':'English'},old)
        values,report=self.run_merge({'k':'English'},ext=new,own=own)
        self.assertEqual(values['k'],'Новый авторский перевод')
        self.assertNotIn('k',report['ownedEntries'])

    def test_manual_used_only_for_matching_english(self):
        own=manual({'k':fallback('Old English')})
        values,report=self.run_merge({'k':'Old English'},own=own)
        self.assertEqual(values['k'],'Наш перевод')
        values,report=self.run_merge({'k':'Changed English'},ext=community({'k':'Old English'},{'k':'Старый перевод'}),own=own)
        self.assertNotIn('k',values)
        self.assertEqual(report['refreshQueue'][0]['key'],'k')
        self.assertEqual(report['staleCommunityKeysSkipped'],['k'])
        self.assertFalse(report['futureUpdateBlockedByTranslationStaleness'])

    def test_new_and_removed_english_do_not_freeze_key_count(self):
        values,report=self.run_merge({'new':'New English'},own=manual({'removed':fallback('Old')}))
        self.assertEqual(values,{})
        self.assertEqual(report['removedManualKeys'],['removed'])
        self.assertEqual(report['refreshQueue'][0]['key'],'new')

    def test_ru_only_refresh_cannot_realign_stale_english(self):
        old=community({'k':'Old'},{'k':'Старый'})
        refreshed=f.community_capture({'k':'Даже новый русский текст'},{'providerId':'test-author'},{'k':'Changed'},old)
        self.assertIsNone(refreshed['entries']['k']['englishFingerprint'])
        values,report=self.run_merge({'k':'Changed'},ext=refreshed)
        self.assertEqual(values,{})
        self.assertEqual(report['staleCommunityKeysSkipped'],['k'])

    def test_provider_english_or_explicit_review_can_align_new_source(self):
        en={'k':'Changed'};old=community({'k':'Old'},{'k':'Старый'})
        for kwargs in [{'provider_english':en},{'review_bindings':{'k':f.fp('Changed')}}]:
            with self.subTest(kwargs=kwargs):
                new=f.community_capture({'k':'Новый'},{'providerId':'test-author'},en,old,**kwargs)
                values,_=self.run_merge(en,ext=new)
                self.assertEqual(values['k'],'Новый')

    def test_different_provider_cannot_inherit_reviewed_alignment(self):
        old=community({'k':'English'},{'k':'Первый'})
        new=f.community_capture({'k':'Другой'},{'providerId':'different-author'},{'k':'English'},old)
        self.assertIsNone(new['entries']['k']['englishFingerprint'])

    def test_generated_ru_cannot_become_author_input(self):
        bad=community({'k':'English'},{'k':'Русский'});bad['isGeneratedOutput']=True
        with self.assertRaisesRegex(ValueError,'generated'):self.run_merge({'k':'English'},ext=bad)
        with self.assertRaisesRegex(ValueError,'generated'):f.community_capture({}, {'providerId':'test-author'}, {}, bad)

    def test_community_value_tamper_rejected(self):
        bad=community({'k':'English'},{'k':'Русский'});bad['entries']['k']['text']='Подмена'
        with self.assertRaisesRegex(ValueError,'provenance'):self.run_merge({'k':'English'},ext=bad)

    def test_unavailable_provider_reuses_only_verified_cache_without_rebinding(self):
        old=community({'k':'Old English'},{'k':'Старый перевод'})
        with tempfile.TemporaryDirectory(prefix='atm9-community-offline-') as temp:
            root=Path(temp);previous=root/'previous.json';english=root/'en.json';out=root/'out.json';report=root/'report.json'
            previous.write_bytes(f.json_bytes(old));english.write_bytes(f.json_bytes({'k':'Changed English'}))
            argv=['atm9_ru_future.py','refresh-community','--english',str(english),'--previous',str(previous),'--out',str(out),'--report',str(report)]
            with patch.object(sys,'argv',argv),patch.object(f,'fetch_scriptora',side_effect=OSError('offline')):f.main()
            self.assertEqual(f.load(out),old)
            self.assertEqual(f.load(report)['status'],'PROVIDER_UNAVAILABLE_REUSED_VERIFIED_SOURCE')
            values,merged=self.run_merge({'k':'Changed English'},ext=f.load(out))
            self.assertEqual(values,{})
            self.assertEqual(merged['staleCommunityKeysSkipped'],['k'])
            with patch.object(sys,'argv',[*argv,'--require-fresh']),patch.object(f,'fetch_scriptora',side_effect=OSError('offline')):
                with self.assertRaises(OSError):f.main()

    def test_exact_english_reuse_alias_tracks_new_external_translation(self):
        en={'base':'The same English','alias':'The same English'}
        own=manual({'alias':fallback(en['alias'],'Наш старый',reuseFromNativeKeys=['base'])})
        values,report=self.run_merge(en,ext=community(en,{'base':'Новое внешнее'}),own=own)
        self.assertEqual(values['alias'],'Новое внешнее')
        self.assertEqual(report['sources']['alias'],'exact-English-source-reuse')
        self.assertNotIn('alias',report['ownedEntries'])

    def test_ambiguous_exact_english_reuse_retains_reviewed_fallback(self):
        en={'a':'Same','b':'Same','alias':'Same'}
        values,_=self.run_merge(en,ext=community(en,{'a':'Один','b':'Другой'}),own=manual({'alias':fallback('Same','Проверенный',reuseFromNativeKeys=['a','b'])}))
        self.assertEqual(values['alias'],'Проверенный')

    def test_reference_only_fallback_has_no_fake_english_fingerprint(self):
        refs=[{'path':'config/ftbquests/quests/x.snbt','sha256':'a'*64}]
        own=manual(nativeReferences={'orphan':refs},referenceOnlyFallbacks={'orphan':{'text':'Контекстный перевод'}})
        values,report=self.run_merge({},own=own,rows={refs[0]['path']:{'sha256':'a'*64}})
        self.assertEqual(values['orphan'],'Контекстный перевод')
        self.assertIsNone(report['ownedEntries']['orphan']['englishFingerprint'])
        values,report=self.run_merge({},own=own,rows={refs[0]['path']:{'sha256':'b'*64}})
        self.assertEqual(values,{})
        self.assertEqual(report['staleNativeReferenceFallbacksSkipped'],['orphan'])
        values,report=self.run_merge({'orphan':'New native English'},own=own,rows={refs[0]['path']:{'sha256':'a'*64}})
        self.assertNotIn('orphan',values)
        self.assertEqual(report['refreshQueue'][0]['key'],'orphan')

    def test_new_external_reference_only_value_supersedes_ours_in_exact_context(self):
        refs=[{'path':'config/ftbquests/quests/x.snbt','sha256':'a'*64}]
        old=community({}, {'orphan':'Известная ошибка'})
        old['entries']['orphan']['nativeReferenceBindings']=refs
        own=manual(nativeReferences={'orphan':refs},referenceOnlyFallbacks={'orphan':{'text':'Наша правка','replacesReviewedCommunityFingerprint':f.fp('Известная ошибка'),'reviewedCommunityProviderId':'test-author'}})
        rows={refs[0]['path']:{'sha256':'a'*64}}
        original,_=self.run_merge({},own=own,ext=old,rows=rows)
        self.assertEqual(original['orphan'],'Наша правка')
        refreshed=f.community_capture({'orphan':'Новая авторская строка'},{'providerId':'test-author'},{},old)
        values,report=self.run_merge({},own=own,ext=refreshed,rows=rows)
        self.assertEqual(values['orphan'],'Новая авторская строка')
        self.assertNotIn('orphan',report['ownedEntries'])
        values,report=self.run_merge({},own=own,ext=refreshed,rows={refs[0]['path']:{'sha256':'b'*64}})
        self.assertNotIn('orphan',values)

    def test_native_reference_manual_fallback_must_remain_native_string(self):
        refs=[{'path':'config/ftbquests/quests/x.snbt','sha256':'a'*64}]
        own=manual(nativeReferences={'orphan':refs},referenceOnlyFallbacks={'orphan':{'text':['invalid list']}})
        with self.assertRaisesRegex(ValueError,'native-reference fallback'):
            self.run_merge({},own=own,rows={refs[0]['path']:{'sha256':'a'*64}})


class SourceFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='atm9-future-')
        self.root=Path(self.temp.name)/'author';self.root.mkdir()
        self.files={f.EN:f.json_bytes({'native':'Native English'}),'mods/stock.jar':b'author exact jar fixture',
                    'config/ftbquests/quests/chapter.snbt':b'{ title: "Inline English", id: "0123456789ABCDEF" }\n'}
        for path,data in self.files.items():self.put(path,data)
        self.lock=self.make_lock('1.2.3')
        self.alias=f.PREFIX+'a'*24
        self.old=self.files['config/ftbquests/quests/chapter.snbt']
        self.new=self.old.replace(b'Inline English',('{'+self.alias+'}').encode())
        self.legacy={'files':[display_row('config/ftbquests/quests/chapter.snbt',self.old,self.new,b'Inline English',('{'+self.alias+'}').encode())]}
        self.aliases={self.alias:'Inline English'}
        self.own=manual({'native':fallback('Native English'),self.alias:fallback('Inline English','Встроенный перевод')})

    def tearDown(self):self.temp.cleanup()
    def put(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    def make_lock(self,version):
        rows=[{'path':p,'sizeBytes':len(v),'sha256':f.sha(v)} for p,v in self.files.items()]
        return {'schemaVersion':1,'pack':{'version':version},'files':[r for r in rows if r['path'].endswith('.jar')],'overrides':[r for r in rows if not r['path'].endswith('.jar')]}
    def prepare(self):return f.prepare(self.root,self.lock,self.own,community(),self.legacy,self.aliases)
    def profile(self,profile):
        path=Path(self.temp.name)/'profile.json';path.write_bytes(f.json_bytes(profile));return path

    def test_future_version_no_old_fixed_count_and_no_source_write(self):
        before={p:x.read_bytes() for p in self.files for x in [self.root/p]}
        overlay,profile,_,report=self.prepare()
        self.assertEqual(profile['sourceVersion'],'1.2.3')
        self.assertEqual(len(profile['files']),2)
        self.assertEqual(d.load_manifest(self.profile(profile)),profile['files'])
        self.assertEqual(report['strictBaseRowsVerified'],3)
        self.assertEqual({p:(self.root/p).read_bytes() for p in self.files},before)
        self.assertEqual(overlay['config/ftbquests/quests/chapter.snbt'],self.new)

    def test_changed_native_chapter_not_rewritten_with_old_offsets(self):
        path='config/ftbquests/quests/chapter.snbt';self.files[path]=self.old.replace(b'Inline English',b'A newly authored paragraph')
        self.put(path,self.files[path]);self.lock=self.make_lock('2.0.0')
        overlay,profile,_,report=self.prepare()
        self.assertNotIn(path,overlay)
        self.assertNotIn(f.EN,overlay)
        self.assertEqual(profile['files'],[])
        self.assertEqual(len(d.load_manifest(self.profile(profile))),0)
        self.assertEqual(report['skippedDisplayFiles'][0]['path'],path)
        self.assertEqual((self.root/path).read_bytes(),self.files[path])

    def test_native_quest_scope_reports_added_changed_and_removed_without_blocking(self):
        snapshot=[{'path':'config/ftbquests/quests/old.snbt','sha256':'a'*64},
                  {'path':'config/ftbquests/quests/changed.snbt','sha256':'a'*64}]
        rows={'config/ftbquests/quests/changed.snbt':{'sha256':'b'*64},'config/ftbquests/quests/new.snbt':{'sha256':'c'*64}}
        report=f.quest_source_scope(rows,snapshot)
        self.assertEqual(report['changedPreviouslyReviewedFiles'],['config/ftbquests/quests/changed.snbt'])
        self.assertEqual(report['addedUnreviewedFiles'],['config/ftbquests/quests/new.snbt'])
        self.assertEqual(report['removedReviewedFiles'],['config/ftbquests/quests/old.snbt'])
        self.assertTrue(report['doesNotBlockPackUpdate'])

    def test_native_alias_collision_does_not_overwrite_author(self):
        self.files[f.EN]=f.json_bytes({'native':'Native English',self.alias:'Different native meaning'})
        self.put(f.EN,self.files[f.EN]);self.lock=self.make_lock('2.0.0')
        overlay,profile,_,report=self.prepare()
        self.assertEqual(profile['files'],[])
        self.assertEqual(report['skippedDisplayFiles'][0]['reason'],'native-English-alias-collision')
        self.assertNotIn(f.EN,overlay)

    def test_future_native_ru_is_author_input_and_exact_reversible_base_resource(self):
        self.files[f.RU]=f.json_bytes({'native':'Новый перевод автора'})
        self.put(f.RU,self.files[f.RU]);self.lock=self.make_lock('2.0.0')
        overlay,profile,_,report=self.prepare()
        self.assertEqual(json.loads(overlay[f.RU])['native'],'Новый перевод автора')
        rurow=next(r for r in profile['files'] if r['path']==f.RU)
        self.assertEqual(d.transform(overlay[f.RU],rurow,False),self.files[f.RU])
        self.assertEqual(d.load_manifest(self.profile(profile)),profile['files'])

    def test_unknown_or_missing_jar_still_rejected_before_output(self):
        for kind in ['changed','missing','extra']:
            with self.subTest(kind=kind):
                self.put('mods/stock.jar',self.files['mods/stock.jar'])
                extra=self.root/'mods/extra.jar'
                if extra.exists():extra.unlink()
                if kind=='changed':self.put('mods/stock.jar',b'unknown')
                elif kind=='missing':(self.root/'mods/stock.jar').unlink()
                else:self.put('mods/extra.jar',b'extra')
                with self.assertRaises(ValueError):self.prepare()

    def test_managed_ru_not_in_pristine_lock_is_not_author_source(self):
        self.put(f.RU,f.json_bytes({'native':'Наша предыдущая генерация'}))
        with self.assertRaisesRegex(ValueError,'Unexpected author content'):self.prepare()

    def test_personal_instance_markers_are_rejected(self):
        (self.root/'saves').mkdir()
        with self.assertRaisesRegex(ValueError,'pristine'):self.prepare()

    def test_exact_reversible_apply_normalize_verify_and_idempotence(self):
        overlay,profile,_,_=self.prepare();manifest=self.profile(profile)
        for mode in ['apply','apply','verify','normalize','normalize']:
            result=d.run(mode,self.root,manifest)
            if mode=='verify':self.assertEqual(result['unchanged'],2)
        self.assertEqual((self.root/'config/ftbquests/quests/chapter.snbt').read_bytes(),self.old)
        self.assertEqual((self.root/f.EN).read_bytes(),self.files[f.EN])

    def test_unknown_later_file_preflight_prevents_earlier_writes(self):
        _,profile,_,_=self.prepare();manifest=self.profile(profile)
        self.put(f.EN,b'unknown input')
        with self.assertRaises(ValueError):d.run('apply',self.root,manifest)
        self.assertEqual((self.root/'config/ftbquests/quests/chapter.snbt').read_bytes(),self.old)

    def test_normalize_allows_missing_for_native_importer_apply_does_not(self):
        _,profile,_,_=self.prepare();manifest=self.profile(profile)
        (self.root/f.EN).unlink()
        self.assertEqual(d.run('normalize',self.root,manifest)['missingSkipped'],1)
        with self.assertRaisesRegex(ValueError,'Missing base'):d.run('apply',self.root,manifest)

    def test_output_is_separate_and_managed(self):
        overlay,profile,ownership,report=self.prepare()
        with self.assertRaisesRegex(ValueError,'separate'):f.write_output(self.root/'generated',self.root,overlay,profile,ownership,report)
        out=Path(self.temp.name)/'out';f.write_output(out,self.root,overlay,profile,ownership,report)
        self.assertFalse(f.load(out/'tools/atm9_ru_future/ownership.json')['isAuthorSource'])
        with self.assertRaisesRegex(ValueError,'fresh output'):f.write_output(out,self.root,overlay,profile,ownership,report)

    def test_non_display_path_and_jar_profiles_rejected(self):
        _,profile,_,_=self.prepare()
        for mutate in ['jar','gameplay','traversal']:
            bad=copy.deepcopy(profile)
            if mutate=='jar':bad['files'][0]['path']='mods/stock.jar'
            elif mutate=='traversal':bad['files'][0]['path']='config/ftbquests/quests/../oops.snbt'
            else:bad['files'][0]['edits'][0]['displayPath']=['tasks',0,'item']
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):d.load_manifest(self.profile(bad))

    def test_english_alias_insert_preserves_all_author_values(self):
        for raw in [b'{"old":"English"}\n',b'{\r\n  "old": "English"\r\n}\r\n',b'{}\n',b'\xef\xbb\xbf{\n}\n']:
            with self.subTest(raw=raw):
                original=json.loads(raw.decode('utf-8-sig'))
                out,r=f.append_english(raw,original,{'added':'A full English paragraph'})
                self.assertEqual(json.loads(out.decode('utf-8-sig')),{**original,'added':'A full English paragraph'})
                self.assertEqual(d.transform(out,r,False),raw)

    def test_cli_unsupported_new_locale_is_nonblocking_without_explicit_coverage_gate(self):
        self.files[f.EN]=b'{"new":["future typed value"]}\n';self.put(f.EN,self.files[f.EN]);self.lock=self.make_lock('2.0.0')
        lock=Path(self.temp.name)/'lock.json';lock.write_bytes(f.json_bytes(self.lock))
        common=[sys.executable,str(HERE/'atm9_ru_future.py'),'prepare','--source',str(self.root),'--source-lock',str(lock),
            '--out',str(Path(self.temp.name)/'out'),'--report',str(Path(self.temp.name)/'report.json')]
        done=subprocess.run(common,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertEqual(f.load(Path(self.temp.name)/'report.json')['status'],'SKIPPED_UNSUPPORTED_TRANSLATION_SOURCE')
        self.assertFalse((Path(self.temp.name)/'out').exists())
        strict=subprocess.run([*common,'--require-complete'],capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(strict.returncode,0)

    def test_new_author_locale_location_is_not_a_frozen_old_path_gate(self):
        self.files['kubejs/assets/newnative/lang/en_us.json']=self.files.pop(f.EN)
        (self.root/f.EN).unlink();self.put('kubejs/assets/newnative/lang/en_us.json',self.files['kubejs/assets/newnative/lang/en_us.json']);self.lock=self.make_lock('3.0.0')
        self.assertEqual(len(f.verify_source(self.root,self.lock)),3)
        with self.assertRaisesRegex(f.UnsupportedTranslationSource,'path changed'):self.prepare()


if __name__=='__main__':unittest.main(verbosity=2)
