"""Read exact installed/cache JARs; run small native public-API probes, not Minecraft.

Supply --java (Java17), --javac (JDK17+), --libraries, --versions, --mods and --out.
No network, game launch, target attach, source JAR modification, or live data IO.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess

HERE=Path(__file__).resolve().parent
PINS={
    'journeymap-1.20.1-5.10.3-forge.jar':'8b2679b7b4881e0aa430fd24345ea446de919faf8a45bd2a71d37c7e8ff6ae1e',
    'rhino-forge-2001.2.3-build.10.jar':'fed2211429301bf043864183cab9ab8e92d4cc4dbb9e488ce6c75217c54584a6',
}
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def invoke(command,out,cwd):
    r=subprocess.run(command,capture_output=True,cwd=cwd,timeout=45)
    out.write_bytes(r.stdout+r.stderr)
    if r.returncode:raise ValueError('Probe command failed; inspect '+str(out))
    return r.stdout.decode('utf-8')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['java','javac','libraries','versions','mods','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name in ['java','javac','libraries','versions','mods','out']:setattr(a,name,getattr(a,name).resolve())
    a.out.mkdir(parents=True,exist_ok=True)
    for name,expected in PINS.items():
        if digest(a.mods/name)!=expected:raise ValueError('Native JAR pin mismatch: '+name)
    base=a.libraries/'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar'
    patch=a.libraries/'net/minecraftforge/forge/1.20.1-47.4.0/forge-1.20.1-47.4.0-client.jar'
    universal=a.libraries/'net/minecraftforge/forge/1.20.1-47.4.0/forge-1.20.1-47.4.0-universal.jar'
    if digest(base)!='e2e940fe7ca0a9fba5a5c11ad2cf3e2f7df91bbf51d12af22cdde7af18adc344':raise ValueError('Minecraft SRG pin mismatch')
    if digest(patch)!='010adc332f19b05fb24383954ec7a88694666216e480a6824ff0cbc4740c3c66':raise ValueError('Forge patched-client pin mismatch')
    libraries=[]
    for version in ['1.20.1-forge-47.4.0','1.20.1']:
        metadata=json.loads((a.versions/version/(version+'.json')).read_text(encoding='utf-8'))
        for row in metadata['libraries']:
            rel=row.get('downloads',{}).get('artifact',{}).get('path')
            if rel and (a.libraries/rel).is_file():libraries.append(a.libraries/rel)
    for name in ['fmlcore','fmlloader','javafmllanguage','mclanguage','lowcodelanguage']:
        libraries+=list((a.libraries/'net/minecraftforge'/name/'1.20.1-47.4.0').glob('*.jar'))
    classes=a.out/'classes';classes.mkdir(exist_ok=True)
    cp=list(dict.fromkeys([classes,patch,base,universal]+[a.mods/name for name in PINS]+libraries))
    cptext=';'.join(str(x.resolve()) for x in cp)
    sources=[HERE/'NativeWaypointProbe.java',HERE/'NativeLifecycleAliasProbe.java',HERE/'NativeLifecycleModelProbe.java']
    invoke([str(a.javac),'--release','17','-encoding','UTF-8','-cp',cptext,'-d',str(classes)]+[str(x) for x in sources],a.out/'compile.log',a.out)
    records=[]
    for name,mainclass,extra in [('public-api','NativeWaypointProbe',[str(HERE/'native-waypoint-probe.js')]),('aliases','NativeLifecycleAliasProbe',[]),('lifecycle-model','NativeLifecycleModelProbe',[str(HERE/'candidate/waypoint_forge1201_lifecycle.js'),str(HERE/'candidate/test_waypoint_lifecycle.js')])]:
        args=['-Xms16m','-Xmx128m','-Djava.awt.headless=true','-Dfile.encoding=UTF-8','-cp',cptext,mainclass]+extra
        argfile=a.out/(name+'-args.txt');argfile.write_text('\n'.join('"'+x.replace('\\','/').replace('"','\\"')+'"' for x in args)+'\n',encoding='utf-8')
        log=a.out/(name+'.log');text=invoke([str(a.java),'@'+str(argfile)],log,a.out)
        record=json.loads(next(line for line in text.splitlines() if line.startswith('{')))
        records.append({'kind':name,'result':record,'logSha256':digest(log)})
    result={'status':'PASS_LIMITED_NATIVE_FIXTURE_ONLY','noMinecraftBootstrapOrAttach':True,'noPersistentWaypointIO':True,'records':records}
    (a.out/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PASS: native public parser/cache and exact alias probes; no game or persistent waypoint IO.')
if __name__=='__main__':main()
