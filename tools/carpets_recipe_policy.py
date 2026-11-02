"""Prepare/verify one exact source-owned recipe correction; never runs in the launcher."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import zipfile

AUTHOR_ENTRY = 'data/alchemistry/recipes/dissolver/carpets.json'
OVERRIDE = 'kubejs/data/alchemistry/recipes/dissolver/carpets.json'
RECEIPT = 'tools/carpets-recipe-policy.json'
AUTHOR_SHA = '8b46cb2a3fe70fd29c418281ab29ab79de4211eb39289c79edd758f4505bb71c'
OVERRIDE_SHA = '05a82fcfb14da81ad397e342192b4f7dec0528156b0f4116cfc1f4aa68f009d4'
LEGACY = b'"tag": "minecraft:carpets"'
CORRECT = b'"tag": "minecraft:wool_carpets"'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe(pack, relative):
    pack = Path(pack).resolve()
    result = pack / relative
    require(result.resolve().is_relative_to(pack), 'Recipe path escaped source pack')
    current = result
    while current != pack.parent:
        if current.exists() or current.is_symlink():
            require(not current.is_symlink() and not getattr(current.lstat(), 'st_file_attributes', 0) & 0x400,
                    'Linked recipe source paths are refused')
        if current == pack:
            break
        current = current.parent
    return result


def outputs(pack):
    """Read the actual author bytes and compute exactly one approved replacement."""
    pack = Path(pack).resolve()
    jars = sorted(safe(pack, 'mods').glob('alchemistry-*.jar'))
    require(len(jars) == 1, 'Exactly one author Alchemistry JAR is required')
    jar = safe(pack, jars[0].relative_to(pack).as_posix())
    with zipfile.ZipFile(jar) as archive:
        require(AUTHOR_ENTRY in archive.namelist(), 'Author carpets recipe is missing; review/retire this policy')
        raw = archive.read(AUTHOR_ENTRY)
    require(len(raw) == 639 and hashlib.sha256(raw).hexdigest() == AUTHOR_SHA,
            'Author carpets recipe changed or was fixed: review and retire/rebase the known override; do not mask new author data')
    require(raw.count(LEGACY) == 1, 'Expected single legacy ingredient tag')
    replacement = raw.replace(LEGACY, CORRECT, 1)
    before = json.loads(raw); after = json.loads(replacement)
    expected = copy.deepcopy(before); expected['input']['ingredient']['tag'] = 'minecraft:wool_carpets'
    require(before['type'] == 'alchemistry:dissolver' and before['input']['ingredient'] == {'tag': 'minecraft:carpets'}
            and before['input']['count'] == 1 and after == expected,
            'Recipe correction must change only input.ingredient.tag')
    require(len(replacement) == 644 and hashlib.sha256(replacement).hexdigest() == OVERRIDE_SHA,
            'Recipe override bytes differ from the approved single edit')
    owned = safe(pack, 'launcher/pack-owned.txt').read_text(encoding='utf-8-sig').splitlines()
    require(any(line.strip() in {'kubejs/**', 'kubejs/data/**', 'kubejs/data/alchemistry/**', OVERRIDE} for line in owned),
            'The recipe override must be explicitly source-owned')
    receipt = {'schemaVersion': 1, 'kind': 'same-id-alchemistry-carpet-tag-correction',
               'recipeId': 'alchemistry:dissolver/carpets',
               'sourceJar': {'path': jar.relative_to(pack).as_posix(), 'sizeBytes': jar.stat().st_size, 'sha256': sha(jar)},
               'authorRecipe': {'entry': AUTHOR_ENTRY, 'sizeBytes': len(raw), 'sha256': AUTHOR_SHA},
               'override': {'path': OVERRIDE, 'sizeBytes': len(replacement), 'sha256': OVERRIDE_SHA},
               'onlyChangedJsonPointer': '/input/ingredient/tag',
               'oldTag': 'minecraft:carpets', 'newTag': 'minecraft:wool_carpets',
               'authorChangedOrFixedPolicy': 'Fail before publication; review and retire/rebase only this known owned override, preserving newer author data.'}
    return replacement, (json.dumps(receipt, indent=2) + '\n').encode('utf-8'), receipt


def verify(pack):
    replacement, receipt, value = outputs(pack)
    require(safe(pack, OVERRIDE).is_file() and safe(pack, OVERRIDE).read_bytes() == replacement,
            'Known same-ID carpets override is absent or changed')
    require(safe(pack, RECEIPT).is_file() and safe(pack, RECEIPT).read_bytes() == receipt,
            'Carpets source receipt is absent/stale; prepare and review the source update')
    return value


def prepare(pack):
    pack = Path(pack).resolve()
    for marker in ('.portable-instance.json', '.portable-pack-sync.json', 'portable-pack-source.json'):
        require(not safe(pack, marker).exists(), 'Use an independent source checkout, not an installed/live pack')
    replacement, receipt, value = outputs(pack)
    target = safe(pack, OVERRIDE)
    require(not target.exists() or target.read_bytes() == replacement,
            'Unknown existing recipe override is preserved; review explicitly before replacement')
    changed = []
    for name, raw in ((OVERRIDE, replacement), (RECEIPT, receipt)):
        path = safe(pack, name)
        if not path.exists() or path.read_bytes() != raw:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw); changed.append(name)
    verify(pack)
    return {'changed': changed, 'policy': value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'verify'))
    parser.add_argument('--pack', required=True, type=Path)
    args = parser.parse_args()
    try:
        value = prepare(args.pack) if args.operation == 'prepare' else verify(args.pack)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, 'error: ' + str(error) + '\n')
    print(json.dumps(value, indent=2))


if __name__ == '__main__': main()
