// Standalone actual Rhino/JM public API test; no game boot or store mutation.
var checks = [];
function check(label, value) { if (!value) throw new Error(label); checks.push(label); }
function fixture(name, type) {
  return NativeWaypoint.fromString(JSON.stringify({id:'fixture_'+name, name:name, x:1,y:64,z:2,
    r:255,g:255,b:255,enable:true,type:type,origin:'journeymap', dimensions:['minecraft:overworld'],persistent:true}));
}
// Conservative parser supports only the exact native default full date/time pattern.
// Date is presentation data, not a native creation timestamp. No renamed point proof.
function oldNativeDeath(point, birth, prefix, clockTrusted, whitelisted) {
  if (!clockTrusted || whitelisted || !point.isDeathPoint()) return false;
  var name = String(point.getName());
  if (name.indexOf(prefix+' ') !== 0) return false;
  var text = name.substring(prefix.length+1);
  if (!/^\d{2}:\d{2}:\d{2} \d{2}-\d{2}-\d{4}$/.test(text)) return false;
  var fmt = new NativeDateFormat('HH:mm:ss MM-dd-yyyy');
  fmt.setTimeZone(NativeTimeZone.getTimeZone('UTC'));
  fmt.setLenient(false);
  var pos = new NativeParsePosition(0);
  var date = fmt.parse(text, pos);
  if (date === null || pos.getIndex() !== text.length || String(fmt.format(date)) !== text) return false;
  return date.getTime()+999 < birth;
}
var birth = Date.UTC(2026,10,2,12,0,0,500);
var old = fixture('Death 11:59:56 11-02-2026','Death');
check('actual-native-gson-point-isDeath',old.isDeathPoint());
check('actual-native-name-public-getter',String(old.getName())==='Death 11:59:56 11-02-2026');
check('older-than-birth-full-second',oldNativeDeath(old,birth,'Death',true,false));
check('current-same-second-conservative',!oldNativeDeath(fixture('Death 12:00:00 11-02-2026','Death'),birth,'Death',true,false));
check('new-current-death-preserved',!oldNativeDeath(fixture('Death 12:00:01 11-02-2026','Death'),birth,'Death',true,false));
check('non-death-preserved',!oldNativeDeath(fixture('Death 11:59:56 11-02-2026','Normal'),birth,'Death',true,false));
check('renamed-unknown-preserved',!oldNativeDeath(fixture('My old death','Death'),birth,'Death',true,false));
check('custom-format-preserved',!oldNativeDeath(fixture('Death 11:59 02/11/2026','Death'),birth,'Death',true,false));
check('invalid-date-preserved',!oldNativeDeath(fixture('Death 11:59:56 02-31-2026','Death'),birth,'Death',true,false));
check('trailing-input-preserved',!oldNativeDeath(fixture('Death 11:59:56 11-02-2026 extra','Death'),birth,'Death',true,false));
check('whitelisted-legacy-preserved',!oldNativeDeath(old,birth,'Death',true,true));
check('untrusted-clock-preserved',!oldNativeDeath(old,birth,'Death',false,false));
check('other-language-preserved',!oldNativeDeath(fixture('Смерть 11:59:56 11-02-2026','Death'),birth,'Death',true,false));
// Native enum store constructor initializes only its local Guava caches.
// Nonpersistent fixture ensures remove never resolves a Minecraft file path.
var store = NativeWaypointStore.INSTANCE;
old.setPersistent(false);
store.add(old);
check('actual-native-store-add-get',String(store.get(String(old.getId())).getName())===String(old.getName()));
check('actual-native-store-collection',store.getAll().size()===1);
store.remove(old,false);
check('actual-native-store-remove-nonpersistent',store.getAll().size()===0);
JSON.stringify({status:'PASS',checks:checks,scope:'Actual Rhino evaluator + native JM Waypoint public parser/getters, isolated native WaypointStore enum/cache add/getAll/remove(nonpersistent,false), Java SimpleDateFormat. No game bootstrap, no file archive/delete/persistent-store path or lifecycle/runtime PASS.'});
