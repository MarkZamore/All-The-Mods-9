"""Verify a reviewed pack-owned JourneyMap waypoint policy at source publication.

This module never runs in the launcher and never reads a personal game directory.
The existing source client-policy template stage restores the missing owned script.
Unknown author JARs require a reviewed receipt change instead of automatic rebasing.
"""
from pathlib import Path
import argparse
import hashlib
import json

RECEIPT = 'tools/journeymap-waypoints-policy.json'
SCRIPT = 'kubejs/startup_scripts/lanmc_journeymap_waypoint_policy.js'
TEMPLATE = 'tools/client-policy/scripts/lanmc_journeymap_waypoint_policy.js'
NATIVE_IDS = {'journeymap', 'kubejs', 'rhino'}
PLATFORM = {'minecraftVersion': '1.20.1', 'loader': {'type': 'forge', 'version': '47.4.0'}}


def require(value, message):
    if not value:
        raise ValueError(message)


def safe(pack, relative):
    require(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative
            and all(part not in {'', '.', '..'} for part in relative.split('/')), 'Unsafe waypoint source path')
    result = pack
    for part in relative.split('/'):
        result /= part
        if result.exists() or result.is_symlink():
            require(not result.is_symlink() and not getattr(result.lstat(), 'st_file_attributes', 0) & 0x400,
                    'Linked waypoint source paths are refused')
    require(result.resolve().is_relative_to(pack), 'Waypoint source path escaped pack')
    return result


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pinned(pack, row):
    require(isinstance(row, dict) and isinstance(row.get('sizeBytes'), int)
            and not isinstance(row['sizeBytes'], bool) and row['sizeBytes'] >= 0
            and isinstance(row.get('sha256'), str) and len(row['sha256']) == 64
            and all(c in '0123456789abcdef' for c in row['sha256']), 'Invalid waypoint source pin')
    path = safe(pack, row.get('path'))
    require(path.is_file() and path.stat().st_size == row['sizeBytes'] and sha(path) == row['sha256'],
            'Reviewed waypoint source/native JAR changed or is missing: ' + row['path'])


def verify(pack):
    pack = Path(pack).resolve()
    receipt = json.loads(safe(pack, RECEIPT).read_text(encoding='utf-8-sig'))
    require(receipt.get('schemaVersion') == 1 and receipt.get('kind') == 'pack-owned-waypoint-generation-association',
            'Unsupported waypoint policy receipt')
    portable = json.loads(safe(pack, 'portable-pack.json').read_text(encoding='utf-8-sig'))
    require(receipt.get('platform') == PLATFORM
            and {key: portable.get(key) for key in PLATFORM} == PLATFORM,
            'Reviewed waypoint Minecraft/loader platform changed; native lifecycle review is required')
    script = receipt.get('script')
    require(isinstance(script, dict) and script.get('path') == SCRIPT and script.get('template') == TEMPLATE,
            'Unexpected waypoint policy script/template')
    pinned(pack, script)
    pinned(pack, {**script, 'path': TEMPLATE})
    native = receipt.get('nativeModules')
    require(isinstance(native, list) and len(native) == 3
            and {row.get('modId') for row in native} == NATIVE_IDS, 'Waypoint native module set changed')
    for row in native:
        require(row.get('path', '').startswith('mods/') and row['path'].endswith('.jar'), 'Invalid waypoint native JAR path')
        pinned(pack, row)
    ownership = {line.strip() for line in safe(pack, 'launcher/pack-owned.txt').read_text(encoding='utf-8-sig').splitlines()}
    require('kubejs/**' in ownership or SCRIPT in ownership, 'Waypoint script lacks declarative pack ownership')
    client_policy = json.loads(safe(pack, 'tools/client-policy/policy.json').read_text(encoding='utf-8-sig'))
    expected = {'path': SCRIPT, 'template': 'scripts/lanmc_journeymap_waypoint_policy.js',
                'sizeBytes': script['sizeBytes'], 'sha256': script['sha256']}
    require(expected in client_policy.get('scripts', []), 'Waypoint source template is not in the actual restore stage')
    return {'status': 'PASS_SOURCE_ONLY', 'script': script, 'nativeModules': native,
            'personalFilesTouched': False, 'runtimeOrWorldAcceptanceClaimed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().pack), indent=2))
