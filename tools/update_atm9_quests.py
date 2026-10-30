"""Owner CLI: pin published ATM9, review a fresh author import, rehearse real restores.

Only refresh-provider accesses the network. Review emits data, never changes an
active source/lock or silently switches its schema1 publication validators.
"""
from __future__ import annotations
import argparse,copy,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
import atm9_ru_future as locale
import atm9_ru_display as display

KIND='atm9-published-quest-input-snapshot'
CONTENT_ROOTS=locale.ROOTS|{'launcher'}
HERE=Path(__file__).resolve().parent


def pin(root,relative):
    path=locale.safe(root,relative)
    return {'path':relative,'sizeBytes':path.stat().st_size,'sha256':locale.sha(path.read_bytes())}


def physical_root(path):
    extended=long_path(path)
    if extended.is_symlink() or hasattr(extended,'is_junction') and extended.is_junction():raise ValueError('Linked root refused')
    return extended.resolve(strict=True)


def canonical(path):
    value=str(long_path(path).resolve())
    return Path(value[4:]) if os.name=='nt' and value.startswith('\\\\?\\') else Path(value)


def long_path(path):
    value=os.path.abspath(path)
    return Path('\\\\?\\'+value) if os.name=='nt' and not value.startswith('\\\\?\\') else path


def content_paths(root):
    paths=set()
    for name in CONTENT_ROOTS:
        for path in (root/name).rglob('*'):
            relative=path.relative_to(root).as_posix();locale.safe(root,relative)
            if path.is_file():paths.add(relative)
    return paths


def source_controls(root):
    paths={'portable-pack.json'}
    for name in ['tools','library']:
        for path in (root/name).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                relative=path.relative_to(root).as_posix();locale.safe(root,relative);paths.add(relative)
    return paths


def native_inspect(kind,root):
    """Execute the actual current verifier and read its native profile, unmodified."""
    script=r'''
import sys,json
from pathlib import Path
root=Path(sys.argv[1]);kind=sys.argv[2];sys.path.insert(0,str(root/'tools'))
if kind=='original':
 import verify_upstream,portable_profile
 report=verify_upstream.verify(root);p=portable_profile.load(portable_profile.working_root(root))
 original=p['records'];support=p['document']['supportFiles'];files=[];lock='tools/portable-profile.json'
 if p.get('dynamic') is not None:
  profile=p['document']['questLocalization'];manifest=profile['manifestPath'];tool=profile['patchTool']
 else:
  profile=p['document']['localization'];manifest=profile['manifest']['path'];tool=profile['patchTool']['path']
else:
 import verify_modified
 report=verify_modified.verify(root);p=verify_modified.load_plan(root)
 original=p['originalBaseRows'];support=p['supportFiles'];files=p['files'];lock='tools/modified-lock.json'
 manifest=p['questLocalization']['manifestPath'];tool=p['questLocalization']['patchTool']
print(json.dumps({'report':report,'originalBaseRows':original,'supportFiles':support,'additionFiles':files,'publicationLock':lock,'manifestPath':manifest,'patchTool':tool},ensure_ascii=True))
'''
    done=subprocess.run([sys.executable,'-B','-c',script,str(root),kind],capture_output=True,text=True,encoding='utf-8')
    if done.returncode:raise ValueError('Native published verifier failed: '+done.stderr[-12000:])
    return json.loads(done.stdout)


def snapshot_published(kind,published):
    root=physical_root(published)
    if (root/'saves').exists() or (root/'logs/latest.log').exists():raise ValueError('Published source must not be a live instance')
    native=native_inspect(kind,root)
    upstream=locale.load(root/'tools/upstream-lock.json');rows=native['originalBaseRows']
    paths=content_paths(root)|{r['path'] for r in rows}
    controls=source_controls(root)
    return {'schemaVersion':1,'kind':KIND,'sourceKind':kind,'sourceVersion':upstream['pack']['version'],
        'upstreamLock':pin(root,'tools/upstream-lock.json'),'publicationLock':pin(root,native['publicationLock']),
        'localization':{'manifest':pin(root,native['manifestPath']),'patchTool':pin(root,native['patchTool'])},
        'content':[pin(root,p) for p in sorted(paths)],'sourceControls':[pin(root,p) for p in sorted(controls)],
        'originalBaseRows':rows,'supportFiles':native['supportFiles'],'additionFiles':native['additionFiles'],
        'nativeVerification':native['report'],'isAuthorTranslationSource':False}


def validate_snapshot(published,snapshot,*,allow_missing_binary=None):
    if snapshot.get('schemaVersion')!=1 or snapshot.get('kind')!=KIND or snapshot.get('sourceKind') not in {'original','modified'} or snapshot.get('isAuthorTranslationSource') is not False:
        raise ValueError('Unsupported published profile/support snapshot')
    root=physical_root(published);seen=set()
    for row in [*snapshot['content'],*snapshot['sourceControls']]:
        relative=row['path']
        if relative.casefold() in seen:continue
        seen.add(relative.casefold());path=locale.safe(root,relative)
        if relative==allow_missing_binary and not path.exists():continue
        if not path.is_file() or path.stat().st_size!=row['sizeBytes'] or locale.sha(path.read_bytes())!=row['sha256']:raise ValueError('Published snapshot pin mismatch: '+relative)
    expected={r['path'] for r in snapshot['content'] if r['path'].split('/')[0] in CONTENT_ROOTS}
    if allow_missing_binary:expected.discard(allow_missing_binary)
    if content_paths(root)!=expected:raise ValueError('Unknown or missing published content; no files may be silently dropped')
    controls={r['path'] for r in snapshot['sourceControls']}
    if source_controls(root)!=controls:raise ValueError('Unknown or missing published source tools/metadata')
    for key in ['upstreamLock','publicationLock']:
        if snapshot[key]!=pin(root,snapshot[key]['path']):raise ValueError('Published '+key+' binding differs')
    for row in snapshot['localization'].values():
        if row!=pin(root,row['path']):raise ValueError('Published localization pin differs')
    return root


def check_output(output,*inputs):
    if output.is_symlink() or hasattr(output,'is_junction') and output.is_junction():raise ValueError('Linked output refused')
    out=canonical(output)
    for value in inputs:
        source=canonical(value)
        if out==source or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Output must be separate from every input tree')
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be a fresh empty directory')
    return out


def tools_pins():
    paths=[HERE/'atm9_ru_future.py',HERE/'atm9_ru_display.py',HERE/'atm9_quest_profile.py',HERE/'atm9_quest_restore.py',Path(__file__).resolve()]
    paths.extend(p for p in (HERE/'atm9_ru_future').rglob('*') if p.is_file())
    return [pin(HERE,p.relative_to(HERE).as_posix()) for p in sorted(paths,key=lambda p:p.relative_to(HERE).as_posix())]


def stage_author(published,snapshot,output):
    """Recover pristine current author bytes from an exact managed publication.

    Every known non-author file is verified first and listed as excluded. This
    never treats existing managed RU/notices/additions as original author data.
    A new pack version still needs its own real fresh author import/new lock.
    """
    root=validate_snapshot(published,snapshot)
    upstream=locale.load(root/snapshot['upstreamLock']['path'])
    rows=[*upstream['files'],*upstream['overrides']]+([upstream['client']] if upstream.get('client') else [])
    if locale.fp(rows)!=locale.fp(snapshot['originalBaseRows']):raise ValueError('Snapshot BASE rows differ from its exact upstream lock')
    indexed={r['path']:r for r in rows}
    spans=display.load_manifest(root/snapshot['localization']['manifest']['path']);profiles={r['path']:r for r in spans}
    for row in spans:
        native=indexed.get(row['path'])
        if not native or row['originalSha256']!=native['sha256'] or row['originalSizeBytes']!=native['sizeBytes']:raise ValueError('Published display input differs from author BASE')
    derived={}
    for row in rows:
        raw=locale.safe(root,row['path']).read_bytes()
        if len(raw)==row['sizeBytes'] and locale.sha(raw)==row['sha256']:continue
        profile=profiles.get(row['path'])
        if profile is None:raise ValueError('Non-display BASE replacement refused: '+row['path'])
        original=display.transform(raw,profile,False)
        if len(original)!=row['sizeBytes'] or locale.sha(original)!=row['sha256']:raise ValueError('Cannot reconstruct exact native author row')
        derived[row['path']]=original
    # No mkdir/copy until the whole source and all reconstructed outputs passed.
    out=check_output(output,root);out.mkdir(parents=True);target_root=long_path(out)
    for row in rows:
        path=locale.safe(target_root,row['path']);path.parent.mkdir(parents=True,exist_ok=True)
        if row['path'] in derived:path.write_bytes(derived[row['path']])
        else:shutil.copyfile(locale.safe(root,row['path']),path)
    lock_copy=target_root/'tools/upstream-lock.json';lock_copy.parent.mkdir(parents=True,exist_ok=True);lock_copy.write_bytes((root/snapshot['upstreamLock']['path']).read_bytes())
    locale.verify_source(target_root,upstream)
    known_excluded=[r for r in snapshot['content'] if r['path'] not in indexed]
    result={'status':'PRISTINE_AUTHOR_STAGED','sourceVersion':upstream['pack']['version'],'strictBaseRowsVerified':len(rows),
        'reversedDisplayRows':len(derived),'knownNonAuthorFilesExcluded':known_excluded,
        'nativeRussianPresent':locale.RU in indexed,'managedRussianPromotedToAuthor':False,
        'publishedSourceWritten':False,'upstreamLockSha256':snapshot['upstreamLock']['sha256']}
    (target_root/'tools/atm9-quest-author-stage.json').write_bytes(locale.json_bytes(result));return result


def review(fresh,lock_path,published,snapshot,community_path,output,*,inputs_lock=None):
    old=validate_snapshot(published,snapshot);fresh=physical_root(fresh)
    upstream=locale.load(lock_path);base=locale.verify_source(fresh,upstream)
    cache=locale.validate_community(locale.load(community_path))
    inputs={'schemaVersion':1,'kind':'atm9-quest-review-inputs','upstreamLockSha256':locale.sha(lock_path.read_bytes()),
        'publishedSnapshotFingerprint':locale.fp(snapshot),'communityCacheSha256':locale.sha(community_path.read_bytes()),'toolchain':tools_pins()}
    if inputs_lock is not None and inputs_lock!=inputs:raise ValueError('Pinned review inputs differ; refresh/import requires a new explicit owner review')
    data=HERE/'atm9_ru_future'
    skipped_reason=None
    try:overlay,profile,ownership,report=locale.prepare(fresh,upstream,locale.load(data/'manual.json'),cache,locale.load(data/'legacy-1.1.1-manifest.json'),locale.load(data/'legacy-alias-english.json'))
    except locale.UnsupportedTranslationSource as error:
        skipped_reason=str(error);overlay={}
        profile={'schemaVersion':2,'kind':locale.PROFILE,'sourceVersion':upstream['pack']['version'],'files':[],
            'proof':{'kind':'no-resource-changes-unsupported-locale','reason':skipped_reason}}
        ownership={'schemaVersion':1,'kind':locale.KIND,'isAuthorSource':False,'ownedEntries':{}}
        report={'status':'SKIPPED_UNSUPPORTED_TRANSLATION_SOURCE','reason':skipped_reason,'refreshQueue':[],
            'strictBaseRowsVerified':len(base),'strictJarMembershipVerified':True,'sourceWritten':False}
    known={r['path']:r for r in snapshot['content']}
    same_author=snapshot['upstreamLock']['sha256']==inputs['upstreamLockSha256']
    same_payload=all(p in known and known[p]['sha256']==locale.sha(v) and known[p]['sizeBytes']==len(v) for p,v in overlay.items())
    # Preserve frozen schema1 pins for current published bytes. The dynamic
    # schema2 is a separate future review artifact, not a stealth validator swap.
    reuse=same_author and same_payload
    replacements=[{'path':r['path'],'originalSha256':r['originalSha256'],'originalSizeBytes':r['originalSizeBytes'],
        'sha256':r['localizedSha256'],'sizeBytes':r['localizedSizeBytes'],'kind':'quest-localization',
        'reason':'Reviewed native locale/display-only ATM9 translation; no gameplay or JAR replacement'} for r in profile['files']]
    changes=[]
    for path,value in sorted(overlay.items()):
        after={'path':path,'sizeBytes':len(value),'sha256':locale.sha(value)}
        before=known.get(path)
        changes.append({'path':path,'previousPublished':before,'freshAuthor':base.get(path),
            'candidate':after,'sameAsPublished':before is not None and all(before[k]==after[k] for k in ['sizeBytes','sha256'])})
    updates={'schemaVersion':1,'kind':'atm9-quest-localization-owner-review','sourceKind':snapshot['sourceKind'],
        'sourceVersion':upstream['pack']['version'],'upstreamLockSha256':inputs['upstreamLockSha256'],
        'mode':'reuse-frozen-current-publication-profile' if reuse else 'new-profile-requires-explicit-owner-data-integration',
        'keepPublishedLocalizationPins':copy.deepcopy(snapshot['localization']) if reuse else None,
        'dynamicReviewProfile':{'path':'overlay/tools/atm9_ru_future/generated-profile.json','sha256':locale.sha(locale.json_bytes(profile))},
        'proposedDynamicQuestLocalization':None if reuse else {'schemaVersion':2,'kind':'atm9-native-locale-display',
            'sourceVersion':upstream['pack']['version'],'upstreamLockSha256':inputs['upstreamLockSha256'],
            'russianRole':'base' if locale.RU in base else 'support' if locale.RU in overlay else 'absent',
            'manifestPath':'tools/atm9_ru_future/generated-profile.json',
            'manifestSha256':locale.sha(locale.json_bytes(profile)),'patchTool':'tools/atm9_ru_display.py',
            'patchToolSha256':locale.sha((HERE/'atm9_ru_display.py').read_bytes())},
        'applyBaseReplacementUpdates':not reuse,
        'baseReplacements':replacements,'russianIsNativeBase':locale.RU in base,
        'russianSupportPin':None if locale.RU in base or locale.RU not in overlay else {'path':locale.RU,'sizeBytes':len(overlay[locale.RU]),'sha256':locale.sha(overlay[locale.RU])},
        'removePriorManagedRussianSupportRow':locale.RU in base or skipped_reason is not None,
        'translationSkippedReason':skipped_reason,
        'preserveAllOtherPublishedSupportPins':[r for r in snapshot['supportFiles'] if r['path']!=locale.RU],
        'retainAdditionalJarsOnlyAfterSeparateModCompatibilityReview':snapshot['additionFiles'],
        'payloadChanges':changes,'requiresExplicitOwnerDataIntegration':not reuse,
        'profileReaderContract':'atm9-native-locale-display/schema2',
        'instructions':['Review every changed payload pin and native display/source report before publishing.',
            'For identical current payload preserve the existing8be48/9ebb paths, bytes, validators and locks.',
            'For a future author import update exact upstream/platform/BASE identity independently of translation coverage.',
            'If accepting schema2, select the supported opt-in descriptor and reviewed data pins, binding every original row to new BASE; never authorize general JAR replacement.',
            'Update only explicit locale/display/support pins and source toolchain inputs. Preserve gameplay IDs/progress and other support policies.',
            'Commit pinned provider cache/manual/tool inputs; CI restore uses those bytes and must not call refresh-provider.',
            'Run native formatter/locale tests for changed external text and normal pack compatibility acceptance; staleness alone uses native English.']}
    out=check_output(output,fresh,old);out.mkdir(parents=True)
    locale.write_output(out/'overlay',fresh,overlay,profile,ownership,report)
    (out/'review-inputs.json').write_bytes(locale.json_bytes(inputs));(out/'required-lock-updates.json').write_bytes(locale.json_bytes(updates))
    (out/'published-profile-snapshot.json').write_bytes(locale.json_bytes(snapshot))
    # The preservation copy lets the current owner compare byte-exact pins;
    # it is never named as an active replacement lock.
    if reuse:
        p=out/'preserved-current';p.mkdir()
        for row in [snapshot['publicationLock'],*snapshot['localization'].values()]:
            target=p/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(locale.safe(old,row['path']).read_bytes())
    result={'status':'REVIEW_CANDIDATE_READY','mode':updates['mode'],'sourceKind':snapshot['sourceKind'],'sourceVersion':upstream['pack']['version'],
        'payloadResources':len(overlay),'baseDisplayRows':len(profile['files']),'changedPublishedPayloadResources':sum(not r['sameAsPublished'] for r in changes),
        'refreshQueueCount':len(report['refreshQueue']),'publishedSourceWritten':False,'freshAuthorSourceWritten':False,
        'networkAccess':False,'existingPublicationValidatorsChanged':False,'translationSkippedReason':skipped_reason,'inputsFingerprint':locale.fp(inputs)}
    (out/'review-result.json').write_bytes(locale.json_bytes(result));return result


def rehearse(published,snapshot,output,cache,*,exercise_missing_binary=False):
    root=validate_snapshot(published,snapshot);out=check_output(output,root)
    if cache.is_symlink() or hasattr(cache,'is_junction') and cache.is_junction():raise ValueError('Linked restore cache refused')
    cache=cache.resolve()
    if cache==canonical(root) or cache.is_relative_to(canonical(root)) or cache==out or cache.is_relative_to(out):raise ValueError('Restore cache must be separate from source and fixture')
    out.mkdir(parents=True);fixture=long_path(out/'source');fixture.mkdir()
    for row in [*snapshot['content'],*snapshot['sourceControls']]:
        source=locale.safe(root,row['path']);target=locale.safe(fixture,row['path']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    validate_snapshot(fixture,snapshot)
    missing=None
    if exercise_missing_binary:
        eligible=[r for r in snapshot['originalBaseRows'] if r['path'].startswith('mods/') and r['path'].endswith('.jar')]
        missing=min(eligible,key=lambda r:r['sizeBytes']);folder=cache/('upstream/locked' if snapshot['sourceKind']=='modified' else 'locked');folder.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(locale.safe(fixture,missing['path']),folder/missing['sha256']);locale.safe(fixture,missing['path']).unlink()
        validate_snapshot(fixture,snapshot,allow_missing_binary=missing['path'])
    results=[]
    for number in [1,2]:
        kind=snapshot['sourceKind'];tool='tools/prepare_pack.py' if kind=='original' else 'tools/restore_modified.py'
        command=[sys.executable,'-B',str(fixture/tool),'--pack',str(fixture),'--cache',str(long_path(cache))]
        if kind=='original':command.append('--restore-locked-files')
        else:command.extend(['--report',str(out/f'run-{number}-native.json')])
        done=subprocess.run(command,cwd=fixture,capture_output=True,text=True,encoding='utf-8')
        (out/f'run-{number}.stdout.log').write_text(done.stdout,encoding='utf-8');(out/f'run-{number}.stderr.log').write_text(done.stderr,encoding='utf-8')
        if done.returncode:raise ValueError('Actual '+kind+' wrapper failed; see fixture logs: '+done.stderr[-4000:])
        if kind=='original':
            report=json.loads(done.stdout.strip().splitlines()[-1]);(out/f'run-{number}-native.json').write_bytes(locale.json_bytes(report))
        else:report=locale.load(out/f'run-{number}-native.json')
        validate_snapshot(fixture,snapshot)
        results.append({'run':number,'exitCode':done.returncode,'nativeReport':report,'allPublishedContentAndControlsByteExact':True})
    report={'status':'PASS','sourceKind':snapshot['sourceKind'],'actualCurrentWrapperRuns':2,'missingBaseJarExercised':missing,
        'recoveredFromExactPinnedCache':missing is not None,'runs':results,'activeSourceWritten':False,
        'publishedLocalizationPinsUnchanged':snapshot['localization'],'allPublishedRowsExactAfterEachRun':True,
        'runtimeAcceptanceClaimed':False}
    (out/'rehearsal-result.json').write_bytes(locale.json_bytes(report));return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('snapshot-published');p.add_argument('--kind',choices=['original','modified'],required=True);p.add_argument('--published',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('review');p.add_argument('--fresh-author',type=Path,required=True);p.add_argument('--upstream-lock',type=Path,required=True);p.add_argument('--published',type=Path,required=True);p.add_argument('--published-snapshot',type=Path,required=True);p.add_argument('--community-cache',type=Path,required=True);p.add_argument('--inputs-lock',type=Path);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('stage-author');p.add_argument('--published',type=Path,required=True);p.add_argument('--published-snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('rehearse');p.add_argument('--published',type=Path,required=True);p.add_argument('--published-snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--exercise-missing-base-jar',action='store_true')
    p=sub.add_parser('refresh-provider');p.add_argument('--fresh-author',type=Path,required=True);p.add_argument('--upstream-lock',type=Path,required=True);p.add_argument('--previous-cache',type=Path,required=True);p.add_argument('--provider-english',type=Path);p.add_argument('--review-bindings',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--require-fresh',action='store_true')
    args=parser.parse_args()
    if args.mode=='snapshot-published':
        doc=snapshot_published(args.kind,args.published)
        if args.out.resolve().is_relative_to(args.published.resolve()):raise ValueError('Snapshot must not overwrite published source')
        args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(locale.json_bytes(doc));result={'status':'PUBLISHED_INPUTS_PINNED','kind':args.kind,'contentFiles':len(doc['content']),'sourceControlFiles':len(doc['sourceControls']),'sha256':locale.sha(args.out.read_bytes())}
    elif args.mode=='stage-author':
        report=stage_author(args.published,locale.load(args.published_snapshot),args.out)
        result={k:report[k] for k in ['status','sourceVersion','strictBaseRowsVerified','reversedDisplayRows','nativeRussianPresent','managedRussianPromotedToAuthor']}
    elif args.mode=='review':result=review(args.fresh_author,args.upstream_lock,args.published,locale.load(args.published_snapshot),args.community_cache,args.out,inputs_lock=locale.load(args.inputs_lock) if args.inputs_lock else None)
    elif args.mode=='rehearse':
        report=rehearse(args.published,locale.load(args.published_snapshot),args.out,args.cache,exercise_missing_binary=args.exercise_missing_base_jar)
        result={k:report[k] for k in ['status','sourceKind','actualCurrentWrapperRuns','allPublishedRowsExactAfterEachRun']}
    else:
        fresh=physical_root(args.fresh_author);locale.verify_source(fresh,locale.load(args.upstream_lock));english=locale.string_map(locale.load(fresh/locale.EN));previous=locale.validate_community(locale.load(args.previous_cache))
        try:
            raw,source=locale.fetch_scriptora();doc=locale.community_capture(raw,source,english,previous,provider_english=locale.load(args.provider_english) if args.provider_english else None,review_bindings=locale.load(args.review_bindings) if args.review_bindings else None);result={'status':'PROVIDER_EXPLICITLY_REFRESHED','source':source,'unalignedKeys':doc['unalignedCurrentEnglishKeys']}
        except (OSError,ValueError,KeyError,zipfile.BadZipFile) as error:
            if args.require_fresh:raise
            doc=previous;result={'status':'PROVIDER_UNAVAILABLE_REUSED_VERIFIED_SOURCE','reason':str(error),'translationStalenessBlocksPackUpdate':False}
        for target in [args.out,args.report]:
            if target.resolve().is_relative_to(fresh):raise ValueError('Provider output must not overwrite pristine author source')
            target.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(locale.json_bytes(doc));args.report.write_bytes(locale.json_bytes(result))
    print(json.dumps(result,ensure_ascii=True,sort_keys=True))


if __name__=='__main__':main()
