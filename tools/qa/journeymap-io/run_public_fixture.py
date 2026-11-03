"""Reproduce the bounded Windows/Rhino waypoint IO fixture, without starting Minecraft."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True, help='JDK 17 home containing bin/java.exe and javac.exe')
    parser.add_argument('--mods', type=Path, required=True, help='Directory containing the pinned KubeJS and Rhino JARs')
    parser.add_argument('--libraries', type=Path, required=True, help='Minecraft shared libraries directory')
    parser.add_argument('--out', type=Path, required=True, help='New empty output directory below an artifacts directory')
    args = parser.parse_args()
    require(os.name == 'nt', 'This fixture explicitly tests Windows junction behavior.')
    source = Path(__file__).resolve().parent
    pins = json.loads((source / 'fixture-pins.json').read_text(encoding='utf-8'))
    for name, expected in pins['sources'].items():
        require(sha(source / name) == expected, 'Fixture source changed: ' + name)
    output = args.out.resolve()
    require('artifacts' in output.parts, 'Output must be inside an explicit artifacts directory.')
    require(not output.exists() or (output.is_dir() and not any(output.iterdir())), 'Output directory must be new or empty.')
    java = args.jdk.resolve() / 'bin/java.exe'
    javac = args.jdk.resolve() / 'bin/javac.exe'
    require(java.is_file() and javac.is_file(), 'JDK executables are missing.')
    flags = {'creationflags': subprocess.CREATE_NO_WINDOW}
    version = subprocess.run([str(java), '-version'], capture_output=True, text=True, check=True, **flags)
    version_text = version.stdout + version.stderr
    require('version "17.' in version_text, 'The actual runtime must be JDK 17.')
    jars = []
    for item in pins['jars']:
        base = args.mods if item['root'] == 'mods' else args.libraries
        jar = (base / item['path']).resolve()
        require(jar.is_file() and sha(jar) == item['sha256'], 'Pinned dependency is missing or changed: ' + item['path'])
        jars.append(jar)
    output.mkdir(parents=True, exist_ok=True)
    classes = output / 'classes'; classes.mkdir()
    game = output / 'game'; outside = output / 'outside'; dangling = output / 'dangling-target'
    for directory in (game, outside, dangling):
        directory.mkdir()
    (game / 'internal-target').mkdir()
    (outside / 'sentinel.txt').write_text('OUTSIDE-PRIVATE-FIXTURE-KEEP', encoding='utf-8')
    def ps_quote(path):
        return "'" + str(path).replace("'", "''") + "'"
    powershell = shutil.which('pwsh') or shutil.which('powershell')
    require(powershell, 'PowerShell is required to create native Windows junction fixtures.')
    # Every target was resolved and checked below this new empty output folder.
    # One shell creates the junctions and removes only the empty private target.
    setup = '\n'.join([
        "$ErrorActionPreference = 'Stop'",
        'New-Item -ItemType Junction -Path ' + ps_quote(game / 'alias') + ' -Target ' + ps_quote(outside) + ' | Out-Null',
        'New-Item -ItemType Junction -Path ' + ps_quote(game / 'internal-alias') + ' -Target ' + ps_quote(game / 'internal-target') + ' | Out-Null',
        'New-Item -ItemType Junction -Path ' + ps_quote(game / 'dangling') + ' -Target ' + ps_quote(dangling) + ' | Out-Null',
        'if (@(Get-ChildItem -LiteralPath ' + ps_quote(dangling) + ' -Force).Count -ne 0) { throw "Private target not empty" }',
        'Remove-Item -LiteralPath ' + ps_quote(dangling),
    ])
    subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-Command', setup], check=True, capture_output=True, text=True, **flags)
    classpath = ';'.join([str(classes)] + [str(p) for p in jars])
    subprocess.run([str(javac), '--release', '17', '-cp', classpath, '-d', str(classes),
                    str(source / 'WaypointIoNativeAudit.java'), str(source / 'CombinedWaypointNativeAudit.java')],
                   check=True, capture_output=True, text=True, **flags)
    result = output / 'result.json'
    completed = subprocess.run([str(java), '-Xmx128m', '-cp', classpath, 'WaypointIoNativeAudit', str(game),
                                str(source / 'waypoint_io_adapter.js'), str(source / 'waypoint_generation_core.js'),
                                str(source / 'native_io_cases.js'), str(result)], check=True, capture_output=True, text=True, timeout=60, **flags)
    data = json.loads(result.read_text(encoding='utf-8'))
    require(data['checks'] == 15 and data['passed'] == 15, 'Native fixture assertions failed; inspect private result.json.')
    require(not dangling.exists(), 'The dangling outside target was created.')
    require(sorted(p.name for p in outside.iterdir()) == ['sentinel.txt'], 'The external fixture target was changed.')
    combined_results = []
    for mode, expected_checks in [('positive', 6), ('bootstrap-failure', 1), ('trusted-junction', 9)]:
        target = output / ('combined-' + mode)
        combined_result = output / ('combined-' + mode + '.json')
        if mode == 'trusted-junction':
            target.mkdir()
            native_saves = output / 'trusted-native-saves'; native_saves.mkdir()
            (native_saves / 'Combined').mkdir()
            replacement_saves = output / 'replacement-native-saves'; replacement_saves.mkdir()
            setup = '\n'.join([
                "$ErrorActionPreference = 'Stop'",
                'New-Item -ItemType Junction -Path ' + ps_quote(target / 'saves') + ' -Target ' + ps_quote(native_saves) + ' | Out-Null',
                'New-Item -ItemType Junction -Path ' + ps_quote(target / 'replacement-saves') + ' -Target ' + ps_quote(replacement_saves) + ' | Out-Null',
                'New-Item -ItemType Junction -Path ' + ps_quote(native_saves / 'Combined/nested-alias') + ' -Target ' + ps_quote(outside) + ' | Out-Null',
            ])
            subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-Command', setup], check=True, capture_output=True, text=True, **flags)
        subprocess.run([str(java), '-Xmx128m', '-cp', classpath, 'CombinedWaypointNativeAudit', str(target),
                        str(source / 'combined_models.js'), str(source / 'lanmc_journeymap_waypoint_policy.js'),
                        str(source / 'combined_cases.js'), str(combined_result), mode],
                       check=True, capture_output=True, text=True, timeout=60, **flags)
        combined = json.loads(combined_result.read_text(encoding='utf-8'))
        require(len(combined['checks']) == expected_checks and combined['passed'] == expected_checks,
                'Combined-script fixture assertions failed: ' + mode)
        combined_results.append({'mode': mode, 'checks': expected_checks, 'resultSha256': sha(combined_result)})
    require(sorted(p.name for p in outside.iterdir()) == ['sentinel.txt'], 'Nested junction target was changed.')
    require(not any(replacement_saves.iterdir()), 'Retargeted saves root was changed.')
    print(json.dumps({'status': 'PASS', 'nativeIoChecks': 15, 'combinedChecks': 16, 'resultSha256': sha(result),
                      'combinedResults': combined_results,
                      'scope': pins['scope'], 'gameStarted': False}))


if __name__ == '__main__':
    main()
