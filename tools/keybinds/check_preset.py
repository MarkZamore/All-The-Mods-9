"""Validate the key-only general layout. Does not claim all GUI red pairs vanish.

Native GUI/companion rows retain their captured values. Independent world
bindings must be physical-unique with NONE; no modifier-family multiplexing.
"""
from pathlib import Path
import hashlib,itertools,json,re,sys
from conflict_model import native_same
HERE=Path(__file__).resolve().parent
PACK=HERE.parent.parent
LINE=re.compile(r"^key_(?P<name>[^:]+):(?P<key>[^:]+)(?::(?P<modifier>SHIFT|CONTROL|ALT))?$")

def read(text):
    result={}
    for raw in text.splitlines():
        line=raw.split('  #',1)[0].strip()
        if not line or line.startswith('#'):continue
        m=LINE.fullmatch(line)
        if not m:raise ValueError('Not a key-only row: '+line)
        if m['name'] in result:raise ValueError('Duplicate mapping: '+m['name'])
        result[m['name']]=m['key']+(':'+m['modifier'] if m['modifier'] else '')
    return result

def check():
    stock=json.loads((HERE/'stock.json').read_text(encoding='utf-8'))
    rows=read((PACK/'launcher/controls-preset.txt').read_text(encoding='utf-8'))
    expected={r['id']:r for r in stock['rows']}
    if set(rows)!=set(expected):raise ValueError('Mapping namespace changed without stock update')
    if '--skip-jar-check' not in sys.argv:
        jars={p.name:p for p in (PACK/'mods').glob('*.jar')}
        if set(jars)!=set(stock['sourceJars']):raise ValueError('Source JAR set changed')
        for name,path in jars.items():
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            if digest.hexdigest()!=stock['sourceJars'][name]:raise ValueError('Source JAR SHA changed: '+name)
    world=[]
    for name,row in expected.items():
        value=rows[name]
        if row['role'] in ('native-gui','native-companion','vanilla') and value!=row['nativeValue']:
            raise ValueError('Captured native GUI/companion/vanilla value changed: '+name)
        if row['role']=='unbound' and value!='key.keyboard.unknown':
            raise ValueError('New binding requires an explicit reviewed stock role: '+name)
        if row['role'] in ('world-primary','vanilla') and value!='key.keyboard.unknown':
            if ':' in value:raise ValueError('Independent world modifier chord: '+name)
            world.append((name,('UNIVERSAL','NONE',value)))
    for (a,av),(b,bv) in itertools.combinations(world,2):
        if native_same(av,bv) or native_same(bv,av):raise ValueError('Independent world conflict: '+a+'/'+b)
    for name,value in stock['requiredCore'].items():
        if rows[name]!=value:raise ValueError('Required general action changed: '+name)
    active=sum(v!='key.keyboard.unknown' for v in rows.values())
    print(f'{len(rows)} names;{active} enabled/{len(rows)-active} unbound;{len(world)} independentworldinputs;0independentworldconflicts')
    print('Native GUI/companion sharing is retained; this is not 0globalControls-screenredpairs or fullgame/restartPASS.')
    return True

if __name__=='__main__':check()
