"""Source-only ATM9 locale preparation: native RU > aligned community RU > reviewed fallback.

Fresh BASE hashes/JAR membership are checked independently of translation coverage.
No source tree is mutated. A new overlay/profile is emitted for the declared current
upstream lock; changed legacy display files safely remain native English.
"""
from __future__ import annotations
import argparse,base64,copy,hashlib,importlib.util,json,re,urllib.request,urllib.error,zipfile,io
from pathlib import Path,PurePosixPath
EN='kubejs/assets/kubejs/lang/en_us.json'
RU='kubejs/assets/kubejs/lang/ru_ru.json'
PREFIX='atm9.translation.inline.'
DATA=Path(__file__).with_suffix('')
KIND='atm9-reviewed-russian-fallbacks'
COMMUNITY='atm9-community-russian-source'
PROFILE='ftbquests-russian-display-localization'
ROOTS={'mods','config','kubejs','scripts','defaultconfigs','data','resourcepacks','shaderpacks','configureddefaults','packmenu','datapacks','resources'}

class UnsupportedTranslationSource(ValueError):pass

def pairs(rows):
 out={}
 for k,v in rows:
  if k in out:raise ValueError('Duplicate JSON key: '+k)
  out[k]=v
 return out

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs)
def sha(data):return hashlib.sha256(data).hexdigest()
def fp(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
def json_bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def normalized(value):return value.replace('\r\n','\\n').replace('\r','\\n').replace('\n','\\n')
def string_map(value):
 if not isinstance(value,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in value.items()):raise UnsupportedTranslationSource('Native ATM9 locale must be a JSON string map')
 return value

def safe(root,relative):
 rel=PurePosixPath(relative)
 if not relative or rel.is_absolute() or '\\' in relative or ':' in relative or any(x in {'','.', '..'} for x in rel.parts):raise ValueError('Unsafe resource path: '+relative)
 path=root.joinpath(*rel.parts)
 for p in [path,*path.parents]:
  if p==root.parent:break
  if p.is_symlink() or hasattr(p,'is_junction') and p.is_junction():raise ValueError('Filesystem links refused: '+relative)
 if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Path leaves source root')
 return path

def verify_source(root,lock):
 """Strict fresh-BASE preflight. Locale staleness cannot relax this check."""
 if (root/'saves').exists() or (root/'logs/latest.log').exists():raise ValueError('Only pristine source trees are accepted, never live instances')
 if lock.get('schemaVersion')!=1 or not isinstance(lock.get('pack',{}).get('version'),str):raise ValueError('Unsupported author lock')
 active=lock.get('files',[])
 if any(not r.get('included',True) for r in active):raise ValueError('Inactive row in active author lock')
 rows=[*active,*lock.get('overrides',[])]
 if lock.get('client'):rows.append(lock['client'])
 expected={};seen=set()
 for row in rows:
  rel=row['path']
  if rel.casefold() in seen:raise ValueError('Duplicate locked resource: '+rel)
  seen.add(rel.casefold());path=safe(root,rel)
  if not path.is_file() or path.stat().st_size!=row['sizeBytes'] or sha(path.read_bytes())!=row['sha256']:raise ValueError('Unknown/missing BASE resource: '+rel)
  expected[rel]=row
 expected_jars={r for r in expected if r.startswith('mods/') and r.endswith('.jar')}
 actual_jars={p.relative_to(root).as_posix() for p in (root/'mods').rglob('*.jar')}
 if actual_jars!=expected_jars:raise ValueError('Unexpected/missing BASE JAR membership')
 for name in ROOTS:
  for path in (root/name).rglob('*'):
   rel=path.relative_to(root).as_posix();safe(root,rel)
   if path.is_file() and rel not in expected:raise ValueError('Unexpected author content: '+rel)
 return expected

def bound_reference(record,source_rows):
 bindings=record.get('nativeReferenceBindings',[])
 return bool(bindings) and all(source_rows.get(x['path'],{}).get('sha256')==x['sha256'] for x in bindings)

def validate_community(document):
 if document.get('schemaVersion')!=1 or document.get('kind')!=COMMUNITY or document.get('isGeneratedOutput') is not False:raise ValueError('Unsupported/generated community provenance source')
 external_values={k:r['text'] for k,r in document.get('entries',{}).items()}
 string_map(external_values)
 if document.get('source',{}).get('valuesFingerprint')!=fp(external_values):raise ValueError('Community source values differ from captured provenance')
 if not document.get('source',{}).get('providerId'):raise ValueError('Community source has no provider identity')
 for key,record in document.get('entries',{}).items():
  if record.get('sourceValueFingerprint')!=fp(record['text']):raise ValueError('Community row differs from captured source: '+key)
  if record.get('englishFingerprint') is not None and not re.fullmatch('[0-9a-f]{64}',record['englishFingerprint']):raise ValueError('Invalid community English binding: '+key)
 return document

def merge(english,native_ru,community,manual,source_rows):
 if manual.get('schemaVersion')!=1 or manual.get('kind')!=KIND:raise ValueError('Unsupported reviewed fallback schema')
 validate_community(community)
 effective=dict(native_ru);owned={};queue=[];sources={};stale=[];native_keys=[];community_keys=[];stale_references=[]
 entries=manual.get('entries',{});external=community.get('entries',{});provider=community.get('source',{}).get('providerId')
 def external_for(key,english_value):
  rec=external.get(key)
  if not rec:return None
  aligned=rec.get('englishFingerprint')==fp(english_value) if english_value is not None else bound_reference(rec,source_rows)
  if not aligned:stale.append(key);return None
  return rec
 for key,en in english.items():
  record=entries.get(key);native=native_ru.get(key);ext=external_for(key,en)
  if native is not None and native.strip() and native!=en:
   effective[key]=native;native_keys.append(key);sources[key]='native-author';continue
  valid_manual=record is not None and record.get('englishFingerprint')==fp(en)
  reviewed_replacement=bool(valid_manual and ext and record.get('replacesReviewedCommunityFingerprint')==fp(ext['text']) and record.get('reviewedCommunityProviderId')==provider)
  if ext and ext['text'].strip() and not reviewed_replacement:
   effective[key]=normalized(ext['text']);community_keys.append(key);sources[key]='aligned-community';continue
  if valid_manual:
   value=record.get('text')
   if not isinstance(value,str) or record.get('decision') not in {'translated','preserve-brand','preserve-technical'}:raise ValueError('Invalid reviewed fallback: '+key)
   effective[key]=value;owned[key]={'englishFingerprint':fp(en),'generatedFingerprint':fp(value),'basis':record.get('basis','manual-review')};sources[key]='reviewed-fallback';continue
  # Native unchanged English stays native. No cached generated RU is promoted to author.
  if native is not None:effective[key]=native
  else:effective.pop(key,None)
  queue.append({'key':key,'reason':'changed-English-fallback-skipped' if record else 'new-or-untranslated-English','english':en,'englishFingerprint':fp(en)})
 # Existing source-reference-only translation has no English value; never invent one.
 for key,bindings in manual.get('nativeReferences',{}).items():
  if key in english:continue
  if not bound_reference({'nativeReferenceBindings':bindings},source_rows):
   stale_references.append(key);continue
  if key in native_ru:continue
  ext=external_for(key,None)
  fallback=manual.get('referenceOnlyFallbacks',{}).get(key)
  replace=bool(fallback and ext and fallback.get('replacesReviewedCommunityFingerprint')==fp(ext['text']) and fallback.get('reviewedCommunityProviderId')==provider)
  if fallback and (not ext or replace):
   if not isinstance(fallback.get('text'),str):raise ValueError('Invalid reviewed native-reference fallback: '+key)
   effective[key]=fallback['text'];sources[key]='reviewed-native-reference-fallback'
   owned[key]={'englishFingerprint':None,'nativeReferenceFingerprint':fp(bindings),'generatedFingerprint':fp(fallback['text']),'basis':'explicit-missing-English-current-native-context'}
  elif ext:
   effective[key]=normalized(ext['text']);sources[key]='community-bound-native-reference';community_keys.append(key)
 # Exact-English reuse aliases track the real source translation, not an old copy of ours.
 for key,record in entries.items():
  if key not in english or key not in effective or sources.get(key)=='native-author':continue
  if record.get('englishFingerprint')!=fp(english[key]):continue
  candidates={effective[k] for k in record.get('reuseFromNativeKeys',[]) if k in english and english[k]==english[key] and k in effective and sources.get(k) in {'native-author','aligned-community'}}
  if len(candidates)==1:
   effective[key]=candidates.pop();sources[key]='exact-English-source-reuse';owned.pop(key,None)
 # Preserve the already published1.1.1 formatting/order; new keys append deterministically.
 order=list(dict.fromkeys([*manual.get('outputOrder',[]),*english,*sorted(effective)]))
 effective={k:effective[k] for k in order if k in effective}
 return effective,{'ownedEntries':owned,'sources':sources,'refreshQueue':queue,'staleCommunityKeysSkipped':sorted(set(stale)),
  'removedManualKeys':sorted(set(entries)-set(english)),'staleNativeReferenceFallbacksSkipped':stale_references,
  'nativeAuthorKeys':native_keys,'alignedCommunityKeys':community_keys,'futureUpdateBlockedByTranslationStaleness':False}

def community_capture(raw,source,english,previous=None,*,provider_english=None,review_bindings=None):
 """RU-only files do not re-bless old values against changed English on refresh."""
 raw=string_map(raw)
 if previous:validate_community(previous)
 same_provider=previous and previous.get('source',{}).get('providerId')==source.get('providerId')
 old=previous.get('entries',{}) if same_provider else {};provider_english=provider_english or {};review_bindings=review_bindings or {};rows={};unaligned=[]
 for key,value in raw.items():
  rec={'text':value,'sourceValueFingerprint':fp(value)};prior=old.get(key,{})
  if key in english:
   current=fp(english[key]);alignment=None
   if key in provider_english and provider_english[key]==english[key]:alignment=current
   elif review_bindings.get(key)==current:alignment=current
   elif prior.get('englishFingerprint')==current:alignment=current
   rec['englishFingerprint']=alignment
   if alignment is None:unaligned.append(key)
  else:
   rec['englishFingerprint']=None
   # The exact native reference context, not the old RU wording, is the
   # alignment anchor for this missing-English edge case. A new author RU
   # value must still supersede ours while the bound native files are exact.
   if prior.get('nativeReferenceBindings'):rec['nativeReferenceBindings']=copy.deepcopy(prior['nativeReferenceBindings'])
  rows[key]=rec
 return {'schemaVersion':1,'kind':COMMUNITY,'source':{**source,'valuesFingerprint':fp(raw)},'entries':rows,'unalignedCurrentEnglishKeys':unaligned,'isGeneratedOutput':False}

def fetch_scriptora():
 api='https://api.github.com/repos/CurseMen/ATM9/releases/latest'
 def read(url,limit):
  req=urllib.request.Request(url,headers={'User-Agent':'LANMinecraft-ATM9-locale-preparation','Accept':'application/vnd.github+json'})
  with urllib.request.urlopen(req,timeout=25) as response:
   data=response.read(limit+1)
  if len(data)>limit:raise ValueError('Translation source exceeds bounded size')
  return data
 release=json.loads(read(api,1024*1024))
 if release.get('draft') or release.get('prerelease') or release.get('author',{}).get('id')!=76762668:raise ValueError('Unexpected translator release identity/type')
 assets=[a for a in release['assets'] if a['name']=='All.The.Mods.9.zip']
 if len(assets)!=1:raise ValueError('Missing/ambiguous official translation asset')
 asset=assets[0];url=asset['browser_download_url']
 if not url.startswith('https://github.com/CurseMen/ATM9/releases/download/'):raise ValueError('Unexpected translator download origin')
 raw=read(url,10*1024*1024)
 if len(raw)!=asset['size'] or asset.get('digest') and asset['digest']!='sha256:'+sha(raw):raise ValueError('Translator asset digest/size mismatch')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  paths=[i for i in z.infolist() if i.filename==RU]
  if len(paths)!=1 or paths[0].file_size>8*1024*1024:raise ValueError('Unexpected Russian resource in translator archive')
  resource=z.read(paths[0])
 value=string_map(json.loads(resource.decode('utf-8-sig'),object_pairs_hook=pairs))
 tag=release['tag_name']
 if not re.fullmatch(r'[A-Za-z0-9._+-]{1,64}',tag):raise ValueError('Unsupported translator release tag')
 # The existing1.0.8 tag predates LICENSE. Its identical resource is licensed
 # by the later author repository commit. Pin that commit AND compare its RU
 # bytes; do not silently attach a current license to different release text.
 commit=json.loads(read('https://api.github.com/repos/CurseMen/ATM9/commits/'+tag,1024*1024))['sha']
 if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Unexpected translator source commit')
 license_url='https://raw.githubusercontent.com/CurseMen/ATM9/'+commit+'/LICENSE'
 try:license_bytes=read(license_url,128*1024)
 except urllib.error.HTTPError as error:
  if error.code!=404:raise
  commit=json.loads(read('https://api.github.com/repos/CurseMen/ATM9/commits/HEAD',1024*1024))['sha']
  if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Unexpected translator licensed source commit')
  license_url='https://raw.githubusercontent.com/CurseMen/ATM9/'+commit+'/LICENSE';license_bytes=read(license_url,128*1024)
 repo_resource=read('https://raw.githubusercontent.com/CurseMen/ATM9/'+commit+'/'+RU,8*1024*1024)
 if repo_resource!=resource:raise ValueError('Translator archive differs from exact licensed repository resource; needs source review')
 if not license_bytes.lstrip().startswith(b'MIT License') or b'Permission is hereby granted' not in license_bytes:raise ValueError('Fresh translator license needs source review; retain verified prior cache')
 return value,{'providerId':'scriptora-atm9-ru','author':'Scriptora / CurseHell / CurseMen','repository':'https://github.com/CurseMen/ATM9','releaseUrl':release['html_url'],'releaseId':release['id'],'version':release['tag_name'],'publishedAtUtc':release['published_at'],'archiveSha256':sha(raw),'resourceSha256':sha(resource),'sourceUrl':url,'licenseSource':license_url,'licenseSha256':sha(license_bytes),'licensedRepoCommit':commit,'licensedRepoRussianMatchesArchive':True,'license':'MIT'}

def append_english(raw,values,add):
 add={k:v for k,v in add.items() if k not in values}
 if not add:return raw,None
 bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'';text=raw[len(bom):].decode('utf-8');closing=len(text.rstrip())-1
 if text[closing]!='}':raise UnsupportedTranslationSource('Unsupported English JSON ending')
 nl='\r\n' if '\r\n' in text else '\n';last=len(text[:closing].rstrip());insert=(',' if values else '')
 entries=(','+nl).join('  '+json.dumps(k)+': '+json.dumps(v,ensure_ascii=False) for k,v in sorted(add.items()))+nl
 edits=[]
 if insert:edits.append((len(bom)+len(text[:last].encode()),insert.encode()))
 edits.append((len(bom)+len(text[:closing].encode()),entries.encode('utf-8')))
 out=raw
 for offset,value in reversed(edits):out=out[:offset]+value+out[offset:]
 parsed=string_map(json.loads(out.decode('utf-8-sig'),object_pairs_hook=pairs))
 if any(parsed[k]!=v for k,v in values.items()) or set(parsed)-set(values)!=set(add):raise ValueError('English native values changed')
 delta=0;records=[]
 for offset,value in edits:
  records.append({'originalOffset':offset,'localizedOffset':offset+delta,'originalBase64':'','localizedBase64':base64.b64encode(value).decode()});delta+=len(value)
 row={'path':EN,'originalSha256':sha(raw),'originalSizeBytes':len(raw),'localizedSha256':sha(out),'localizedSizeBytes':len(out),'edits':records}
 return out,row

def retarget_display(source,version,english,legacy,alias_english,rows):
 selected=[];skipped=[];outputs={}
 for row in legacy['files']:
  if row['path']==EN:continue
  path=safe(source,row['path'])
  if not path.is_file() or sha(path.read_bytes())!=row['originalSha256']:
   skipped.append({'path':row['path'],'reason':'changed-or-removed-author-display-file'});continue
  used=set(re.findall(rb'atm9\.translation\.inline\.[0-9a-f]{24}',b''.join(base64.b64decode(e['localizedBase64']) for e in row['edits'])))
  used={v.decode() for v in used}
  if any(k not in alias_english or k in english and english[k]!=alias_english[k] for k in used):
   skipped.append({'path':row['path'],'reason':'native-English-alias-collision'});continue
  selected.append(copy.deepcopy(row))
 used={v.decode() for row in selected for v in re.findall(rb'atm9\.translation\.inline\.[0-9a-f]{24}',b''.join(base64.b64decode(e['localizedBase64']) for e in row['edits']))}
 required={k:alias_english[k] for k in sorted(used)};raw=safe(source,EN).read_bytes();new_en,enrow=append_english(raw,english,required)
 module_path=Path(__file__).with_name('atm9_ru_display.py');spec=importlib.util.spec_from_file_location('atm9_ru_display',module_path);display=importlib.util.module_from_spec(spec);spec.loader.exec_module(display)
 for row in selected:outputs[row['path']]=display.transform(safe(source,row['path']).read_bytes(),row,True)
 if enrow:outputs[EN]=new_en
 files=sorted([*selected,*([enrow] if enrow else [])],key=lambda x:x['path'])
 profile={'schemaVersion':2,'kind':PROFILE,'sourceVersion':version,'sourceLangSha256':sha(raw),'files':files,
  'proof':{'kind':'reuse-exact-reviewed-display-inputs','reviewedProfileFingerprint':fp(legacy),'priorNativeStructuralProof':legacy.get('nativeStructuralProof'),'selectedOriginalSnbtHashes':[{'path':r['path'],'sha256':r['originalSha256']} for r in selected],'newOrChangedSnbtNotRewritten':skipped}}
 return outputs,profile,{**english,**required},skipped

def quest_source_scope(source_rows,snapshot):
 """Unknown future chapters are report-only; no guessed AST/span rewrite."""
 current={p:r['sha256'] for p,r in source_rows.items() if p.startswith('config/ftbquests/quests/') and p.endswith('.snbt')}
 reviewed={r['path']:r['sha256'] for r in snapshot}
 return {'nativeSnbtFiles':len(current),'exactReviewedSnbtFiles':sum(reviewed.get(p)==h for p,h in current.items()),
  'changedPreviouslyReviewedFiles':sorted(p for p,h in current.items() if p in reviewed and reviewed[p]!=h),
  'addedUnreviewedFiles':sorted(set(current)-set(reviewed)),'removedReviewedFiles':sorted(set(reviewed)-set(current)),
  'unreviewedInlineTextLeftNative':True,'doesNotBlockPackUpdate':True}

def prepare(source,lock,manual,community,legacy,alias_english,quest_snapshot=None):
 rows=verify_source(source,lock)
 if EN not in rows:raise UnsupportedTranslationSource('Native English locale path changed; leave current author resources unchanged')
 raw=safe(source,EN).read_bytes()
 try:english=string_map(json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs))
 except (ValueError,UnicodeError) as error:raise UnsupportedTranslationSource(str(error)) from error
 try:native_ru=string_map(load(safe(source,RU))) if RU in rows else {}
 except (ValueError,UnicodeError) as error:raise UnsupportedTranslationSource('Native Russian locale: '+str(error)) from error
 overlay,profile,effective_en,skipped=retarget_display(source,lock['pack']['version'],english,legacy,alias_english,rows)
 effective_ru,report=merge(effective_en,native_ru,community,manual,rows);ru_bytes=json_bytes(effective_ru);overlay[RU]=ru_bytes
 if RU in rows:
  original_ru=safe(source,RU).read_bytes()
  if original_ru!=ru_bytes:
   profile['files'].append({'path':RU,'originalSha256':sha(original_ru),'originalSizeBytes':len(original_ru),'localizedSha256':sha(ru_bytes),'localizedSizeBytes':len(ru_bytes),'edits':[{'originalOffset':0,'localizedOffset':0,'originalBase64':base64.b64encode(original_ru).decode(),'localizedBase64':base64.b64encode(ru_bytes).decode()}]})
   profile['files'].sort(key=lambda r:r['path'])

 if quest_snapshot is None:quest_snapshot=load(DATA/'legacy-snbt-snapshot.json')
 report.update({'sourceVersion':lock['pack']['version'],'strictBaseRowsVerified':len(rows),'strictJarMembershipVerified':True,'sourceLockFingerprint':fp(lock),'russianKeys':len(effective_ru),'russianSha256':sha(ru_bytes),'displayProfileSchema':profile['schemaVersion'],'displayFiles':len(profile['files']),'skippedDisplayFiles':skipped,'nativeQuestDisplayReview':quest_source_scope(rows,quest_snapshot),'jarOrGameplayIdsChanged':False,'inputSourceWritten':False})
 ownership={'schemaVersion':1,'kind':KIND,'generatedRussianSha256':sha(ru_bytes),'upstreamRussianPresent':RU in rows,'upstreamRussianSha256':rows.get(RU,{}).get('sha256'),'communitySourceFingerprint':fp(community),'ownedEntries':report['ownedEntries'],'isAuthorSource':False}
 return overlay,profile,ownership,report

def write_output(output,source,overlay,profile,ownership,report):
 if output.is_symlink() or hasattr(output,'is_junction') and output.is_junction():raise ValueError('Linked output refused')
 output=output.resolve();source=source.resolve()
 if output==source or output.is_relative_to(source) or source.is_relative_to(output):raise ValueError('Output must be separate from pristine source')
 if output.exists() and any(output.iterdir()):raise ValueError('Use a fresh output directory; previous generated output is not author input')
 output.mkdir(parents=True,exist_ok=True)
 for rel,data in {**overlay,'tools/atm9_ru_future/generated-profile.json':json_bytes(profile),'tools/atm9_ru_future/ownership.json':json_bytes(ownership),'tools/atm9_ru_future/report.json':json_bytes(report)}.items():
  path=safe(output,rel);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
 p=sub.add_parser('prepare');p.add_argument('--source',type=Path,required=True);p.add_argument('--source-lock',type=Path,required=True);p.add_argument('--manual',type=Path,default=DATA/'manual.json');p.add_argument('--community',type=Path,default=DATA/'community-source.json');p.add_argument('--legacy',type=Path,default=DATA/'legacy-1.1.1-manifest.json');p.add_argument('--aliases',type=Path,default=DATA/'legacy-alias-english.json');p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--require-complete',action='store_true')
 p=sub.add_parser('refresh-community');p.add_argument('--english',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);p.add_argument('--provider-english',type=Path);p.add_argument('--review-bindings',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--require-fresh',action='store_true')
 args=parser.parse_args()
 if args.mode=='prepare' and args.report.resolve().is_relative_to(args.source.resolve()):raise ValueError('Report must not overwrite pristine source')
 if args.mode=='refresh-community' and args.out.resolve()==args.english.resolve():raise ValueError('Community output cannot overwrite English input')
 if args.mode=='refresh-community':
  previous=validate_community(load(args.previous));english=string_map(load(args.english))
  try:
   raw,source=fetch_scriptora();document=community_capture(raw,source,english,previous,provider_english=load(args.provider_english) if args.provider_english else None,review_bindings=load(args.review_bindings) if args.review_bindings else None);report={'status':'REFRESHED','source':source,'unalignedKeys':document['unalignedCurrentEnglishKeys']}
  except (OSError,ValueError,KeyError,zipfile.BadZipFile) as error:
   if args.require_fresh:raise
   document=previous;report={'status':'PROVIDER_UNAVAILABLE_REUSED_VERIFIED_SOURCE','reason':str(error),'futureUpdateBlocked':False}
  args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(json_bytes(document))
 else:
  try:
   overlay,profile,ownership,report=prepare(args.source.resolve(strict=True),load(args.source_lock),load(args.manual),load(args.community),load(args.legacy),load(args.aliases))
   if args.require_complete and report['refreshQueue']:raise ValueError('Explicit current-release coverage gate failed')
   write_output(args.out,args.source,overlay,profile,ownership,report);report={**report,'status':'PREPARED_PRIVATE_OVERLAY'}
  except UnsupportedTranslationSource as error:
   if args.require_complete:raise
   report={'status':'SKIPPED_UNSUPPORTED_TRANSLATION_SOURCE','reason':str(error),'futureUpdateBlocked':False,'sourceWritten':False}
 args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_bytes(json_bytes(report));print(json.dumps({**{k:report[k] for k in ['status','sourceVersion','strictBaseRowsVerified','russianKeys','russianSha256','displayFiles','futureUpdateBlockedByTranslationStaleness'] if k in report},'refreshQueueCount':len(report.get('refreshQueue',[])),'staleCommunityCount':len(report.get('staleCommunityKeysSkipped',[]))},ensure_ascii=True))
if __name__=='__main__':main()
