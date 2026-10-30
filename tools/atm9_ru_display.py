"""Reversible exact-byte ATM9 display localization: legacy1.1.1 and explicit new profiles.

normalize: recover exact original author bytes before the unmodified author importer.
apply: apply only the pinned display spans after author restoration.
verify: require all pinned localized base resources, without writing.

New Russian language/notices are ordinary tracked support files, not normalized away.
"""
from pathlib import Path, PurePosixPath
import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile

KIND = 'ftbquests-russian-display-localization'
ENGLISH = 'kubejs/assets/kubejs/lang/en_us.json'
RUSSIAN = 'kubejs/assets/kubejs/lang/ru_ru.json'
DISPLAY = {'title', 'subtitle', 'description', 'hover'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_pairs(rows):
    value = {}
    for key, item in rows:
        if key in value:
            raise ValueError(f'Duplicate manifest key: {key}')
        value[key] = item
    return value


def load_manifest(path):
    manifest = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=strict_pairs)
    if manifest.get('schemaVersion') not in {1, 2} or manifest.get('kind') != KIND:
        raise ValueError('Unsupported quest-localization profile')
    files = manifest.get('files')
    if not isinstance(files, list) or (manifest['schemaVersion'] == 1 and (manifest.get('sourceVersion') != '1.1.1' or len(files) != 107)):
        raise ValueError('Expected exactly 107 approved base display resources')
    if manifest['schemaVersion'] == 2 and not re.fullmatch(r'[A-Za-z0-9._+-]{1,64}', manifest.get('sourceVersion','')):
        raise ValueError('Missing declared current author version')
    seen = set()
    for row in files:
        relative = row.get('path', '')
        parts = PurePosixPath(relative)
        if not relative or relative.casefold() in seen or parts.is_absolute() or '\\' in relative or ':' in relative or any(p in {'.','..'} for p in parts.parts):
            raise ValueError('Unsafe/duplicate quest-localization resource path')
        if relative != ENGLISH and not (manifest['schemaVersion'] == 2 and relative == RUSSIAN) and not (relative.startswith('config/ftbquests/quests/') and relative.endswith('.snbt')):
            raise ValueError('Quest localization cannot modify this base resource')
        seen.add(relative.casefold())
        for prefix in ['original','localized']:
            if not re.fullmatch('[0-9a-f]{64}', row.get(prefix+'Sha256','')) or type(row.get(prefix+'SizeBytes')) is not int or not 0 < row[prefix+'SizeBytes'] < 8*1024*1024:
                raise ValueError('Invalid pinned resource hash/size')
        edits = row.get('edits')
        if not isinstance(edits,list) or not edits:
            raise ValueError('Missing exact localization byte spans')
        previous_original_end = previous_localized_end = -1
        delta = 0
        for edit in edits:
            a, b = edit.get('originalOffset'), edit.get('localizedOffset')
            if type(a) is not int or type(b) is not int or min(a,b)<0:
                raise ValueError('Invalid exact span offset')
            original = base64.b64decode(edit['originalBase64'],validate=True)
            localized = base64.b64decode(edit['localizedBase64'],validate=True)
            if relative == ENGLISH and original:
                raise ValueError('English localization may only append exact aliases')
            if a < previous_original_end or b < previous_localized_end or b != a+delta or not (original or localized):
                raise ValueError('Overlapping or inconsistent localization spans')
            if a+len(original)>row['originalSizeBytes'] or b+len(localized)>row['localizedSizeBytes']:
                raise ValueError('Localization span exceeds pinned resource')
            if relative == RUSSIAN:
                if len(edits) != 1 or a != 0 or b != 0 or len(original) != row['originalSizeBytes'] or len(localized) != row['localizedSizeBytes']:
                    raise ValueError('Russian BASE table must be a complete exact reversible JSON resource')
                for raw in (original,localized):
                    value = json.loads(raw.decode('utf-8-sig'),object_pairs_hook=strict_pairs)
                    if not isinstance(value,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in value.items()):
                        raise ValueError('Russian BASE overlay is not a native string table')
            if relative not in {ENGLISH,RUSSIAN}:
                field_path = edit.get('displayPath',[])
                field = next((p for p in reversed(field_path) if isinstance(p,str)), '')
                if field not in DISPLAY:
                    raise ValueError('Quest localization span is not a declared human-display field')
            previous_original_end, previous_localized_end = a+len(original),b+len(localized)
            delta += len(localized)-len(original)
        if row['originalSizeBytes']+delta != row['localizedSizeBytes']:
            raise ValueError('Localization byte-size delta differs from profile')
    if ENGLISH not in seen and manifest['schemaVersion'] == 1:
        raise ValueError('Missing original English-language append profile')
    return files


def resource(root,relative):
    path = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink() or (hasattr(current,'is_junction') and current.is_junction()):
            raise ValueError(f'Filesystem links are not accepted: {relative}')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Localization resource leaves the pack root')
    return path


def transform(data,row,forward):
    src,dst = ('original','localized') if forward else ('localized','original')
    if len(data)!=row[src+'SizeBytes'] or digest(data)!=row[src+'Sha256']:
        raise ValueError(f'Unknown {src} input: {row["path"]}')
    output = data
    for edit in reversed(row['edits']):
        offset = edit[src+'Offset']
        expected = base64.b64decode(edit[src+'Base64'],validate=True)
        replacement = base64.b64decode(edit[dst+'Base64'],validate=True)
        if output[offset:offset+len(expected)] != expected:
            raise ValueError(f'Exact localization span mismatch: {row["path"]}')
        output = output[:offset]+replacement+output[offset+len(expected):]
    if len(output)!=row[dst+'SizeBytes'] or digest(output)!=row[dst+'Sha256']:
        raise ValueError(f'Reconstructed {dst} hash mismatch: {row["path"]}')
    return output


def run(mode,root,manifest_path):
    root = root.resolve(strict=True)
    files = load_manifest(manifest_path)
    plans,missing,unchanged = [],[],0
    # Global preflight includes output reconstruction. No resource is written
    # until every existing input is identified and every planned output is pinned.
    for row in files:
        path = resource(root,row['path'])
        if not path.exists():
            if mode=='normalize':
                missing.append(row['path'])
                continue
            raise ValueError(f'Missing base resource: {row["path"]}')
        if not path.is_file():
            raise ValueError(f'Base resource is not a regular file: {row["path"]}')
        size = path.stat().st_size
        if size not in {row['originalSizeBytes'],row['localizedSizeBytes']}:
            raise ValueError(f'Unknown base resource size: {row["path"]}')
        data = path.read_bytes()
        sha = digest(data)
        if sha==row['originalSha256'] and len(data)==row['originalSizeBytes']:
            state='original'
        elif sha==row['localizedSha256'] and len(data)==row['localizedSizeBytes']:
            state='localized'
        else:
            raise ValueError(f'Unknown base resource hash: {row["path"]}')
        if mode=='verify':
            if state!='localized': raise ValueError(f'Base display resource is not localized: {row["path"]}')
            unchanged += 1
        elif (mode=='normalize' and state=='localized') or (mode=='apply' and state=='original'):
            plans.append((path,data,transform(data,row,mode=='apply')))
        else:
            unchanged += 1
    for path,before,after in plans:
        if path.read_bytes()!=before:
            raise ValueError('A base resource changed after localization preflight')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb',dir=path.parent,prefix='.ql-',delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(after)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary,path)
        finally:
            if temporary is not None and temporary.exists(): temporary.unlink()
    return {'status':'PASS','mode':mode,'profile':KIND,'baseResources':len(files),'changed':len(plans),'unchanged':unchanged,'missingSkipped':len(missing)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['normalize','apply','verify'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,default=Path(__file__).with_suffix('')/'manifest.json')
    args=parser.parse_args()
    try:
        print(json.dumps(run(args.mode,args.root,args.manifest),sort_keys=True))
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exception:
        print(json.dumps({'status':'FAIL','mode':args.mode,'error':str(exception)},sort_keys=True),file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__': main()
