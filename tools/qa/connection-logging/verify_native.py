"""Reproduce bounded file/console routing with exact native libraries, no game."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def xml(element):
    return element.tag, tuple(sorted(element.attrib.items())), tuple(xml(c) for c in element)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libraries', type=Path, required=True, help='Maven libraries root used by the native Forge client')
    parser.add_argument('--java', type=Path, required=True, help='Java17 executable')
    parser.add_argument('--javac', type=Path, required=True, help='JDK17+ compiler; compiled with --release17')
    parser.add_argument('--work', type=Path, required=True, help='New private QA output directory outside pack runtime')
    args = parser.parse_args()
    pack = HERE.parents[2]
    before = HERE / 'before-log4j2.xml'
    candidate = pack / 'config/log4j2.xml'
    assert sha(before) == '6752b55f7a2ede24cef57d8bab70cfeec8f471f7adb72b6fb13b46853151c65d'
    assert sha(candidate) == '0ffbfcfc73ca1695b6a068c453c67a00dcc6fb774219bef3b6fcbdef863856d5'
    old = ET.parse(before).getroot()
    new = ET.parse(candidate).getroot()
    loggers = new.find('Loggers')
    added = [c for c in loggers if c.tag == 'Logger' and c.get('name') == 'net.minecraft.network.Connection']
    assert len(added) == 1 and added[0].attrib == {'level': 'DEBUG', 'name': 'net.minecraft.network.Connection'}
    loggers.remove(added[0])
    assert xml(old) == xml(new), 'Unrelated semantic logging policy changed'
    jars = []
    document = json.loads((HERE / 'native-libraries.json').read_text(encoding='utf-8'))
    assert len(document['libraries']) == 95
    for row in document['libraries']:
        name = PurePosixPath(row['path'])
        assert not name.is_absolute() and '..' not in name.parts and '\\' not in row['path']
        path = args.libraries.resolve() / row['path']
        assert path.is_file() and sha(path) == row['sha256'], row['path']
        jars.append(str(path))
    version = subprocess.run([str(args.java.resolve()), '-version'], text=True, capture_output=True, check=True)
    assert 'version "17.' in version.stderr + version.stdout, 'Run the actual Java17 target'
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    classes = work / 'classes'
    classes.mkdir()
    compile_result = subprocess.run([str(args.javac.resolve()), '--release', '17', '-cp', os.pathsep.join(jars), '-d', str(classes), str(HERE / 'ConnectionLogRoutingProbe.java')], capture_output=True, text=True)
    assert compile_result.returncode == 0, compile_result.stderr
    runs = []
    for mode, config, expected in [('before', before, False), ('candidate', candidate, True)]:
        folder = work / mode
        (folder / 'config').mkdir(parents=True)
        shutil.copyfile(config, folder / 'config/log4j2.xml')
        result = subprocess.run([str(args.java.resolve()), '-Dlog4j.configurationFile=config/log4j2.xml', '-cp', os.pathsep.join([str(classes), *jars]), 'ConnectionLogRoutingProbe', str(expected).lower()], cwd=folder, text=True, capture_output=True)
        stdout = result.stdout + result.stderr
        (folder / 'console.log').write_text(stdout, encoding='utf-8')
        assert result.returncode == 0 and 'PASS private-native-Log4j-routing' in stdout, stdout[-4000:]
        assert 'PRIVATE_CONNECTION_DEBUG_SENTINEL' not in stdout, 'DEBUG leaked into Console'
        assert 'ERROR StatusLogger' not in stdout and '%minecraftFormatting' not in stdout and 'mainEx' not in stdout, 'Native layout plugin did not resolve'
        file = folder / 'logs/latest.log'
        runs.append({'mode': mode, 'exitCode': result.returncode, 'consoleDebugAbsent': True, 'nativeLayoutResolved': True, 'fileBytes': file.stat().st_size, 'fileSha256': sha(file)})
    report = {'status': 'PASS', 'gameStarted': False, 'syntheticRoutingOnly': True, 'actualNativeLibraries': 95,
              'sameProductionRelativeJvmArgument': True, 'onlyConnectionDebugAdded': True, 'rootAndUnrelatedLevelsUnchanged': True,
              'candidateConfigurationSha256': sha(candidate), 'runs': runs}
    (work / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
