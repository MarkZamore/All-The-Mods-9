var checks = [];
function assertOk(ok, message) { if (!ok) throw new Error(message); }
function expectFailure(f, label) {
  var error = null; try { f(); } catch(e) { error = String(e); }
  assertOk(error !== null, label);
  assertOk(error.indexOf('ambiguous') < 0, 'Overload ambiguity cannot count as an expected guard failure: ' + label);
  assertOk(error.indexOf('Waypoint IO:') >= 0 || error.indexOf('Waypoint association:') >= 0 ||
    error.indexOf('Fixture path escaped root') >= 0, 'Unexpected failure type for ' + label + ': ' + error);
}
function run(name, f) { try { f(); checks.push({name:name,status:'PASS'}); } catch(e) { checks.push({name:name,status:'FAIL',error:String(e)}); } }
var io = createWaypointIo();
var marker = 'saves/IO/lanmc-waypoints-world.json';
run('native atomic JSON create/update readback',function(){
  io.writeJsonAtomic(marker,{value:1});assertOk(io.readJson(marker).value===1,'initial read');
  io.writeJsonAtomic(marker,{value:2});assertOk(io.readJson(marker).value===2,'updated read');
  assertOk(!io.file(marker+'.lanmc-waypoint-old').exists(),'backup left');
});
run('failed staged rename rolls original metadata back',function(){
  NativeBridge.failNextRename('.lanmc-waypoint-new');
  expectFailure(function(){io.writeJsonAtomic(marker,{value:3});},'rename should fail');
  assertOk(io.readJson(marker).value===2,'original not restored');
});
run('failed backup cleanup rolls original back without deleting replacement bytes',function(){
  NativeBridge.failNextDelete('.lanmc-waypoint-old');
  expectFailure(function(){io.writeJsonAtomic(marker,{value:4});},'cleanup should fail');
  assertOk(io.readJson(marker).value===2,'cleanup failure original not restored');
  assertOk(NativeBridge.countRetained('saves/IO')>=2,'replacement not retained');
});
run('process interruption after old rename recovers previous metadata and retains partial staged file',function(){
  var m='saves/Recovery/lanmc-waypoints-world.json';
  NativeBridge.writeTest(m+'.lanmc-waypoint-old','{"value":8}\n');
  NativeBridge.writeTest(m+'.lanmc-waypoint-new','{"partial":');
  assertOk(io.exists(m),'backup should count as existing metadata');
  assertOk(io.readJson(m).value===8,'old metadata not recovered');
  assertOk(!io.file(m+'.lanmc-waypoint-new').exists(),'stage not retained elsewhere');
  assertOk(NativeBridge.countRetained('saves/Recovery')===1,'partial data not retained');
});
run('completed commit with old backup preserves current and retains old metadata',function(){
  var m='saves/Committed/lanmc-waypoints-world.json';
  NativeBridge.writeTest(m,'{"value":9}\n');
  NativeBridge.writeTest(m+'.lanmc-waypoint-old','{"value":8}\n');
  assertOk(io.readJson(m).value===9,'committed data changed');
  assertOk(NativeBridge.countRetained('saves/Committed')===1,'old data not retained');
});
run('orphan partial first stage is retained before a new committed write',function(){
  var m='saves/Orphan/lanmc-waypoints-world.json';
  NativeBridge.writeTest(m+'.lanmc-waypoint-new','{bad');
  io.writeJsonAtomic(m,{value:10});assertOk(io.readJson(m).value===10,'new write failed');
  assertOk(NativeBridge.countRetained('saves/Orphan')===1,'partial orphan lost');
});
run('read-only and write paths refuse external and internal junctions',function(){
  expectFailure(function(){io.assertPath('alias/missing.json');},'external junction accepted');
  expectFailure(function(){io.mkdirs('alias/no-write');},'external junction mkdir accepted');
  expectFailure(function(){io.assertPath('internal-alias/missing.json');},'internal junction accepted');
  expectFailure(function(){io.relativeFile(NativeBridge.getFileFromPath('alias'));},'relative external alias accepted');
  expectFailure(function(){io.relativeFile(NativeBridge.getFileFromPath('internal-alias'));},'relative internal alias accepted');
});
run('dangling junction entry is refused even though File.exists is false',function(){
  assertOk(!NativeBridge.getFileFromPath('dangling').exists(),'fixture junction target must be absent');
  expectFailure(function(){io.assertPath('dangling/no-write');},'dangling junction path accepted');
  expectFailure(function(){io.mkdirs('dangling/no-write');},'dangling junction mkdir accepted');
  expectFailure(function(){io.assertPath('DaNgLiNg/no-write');},'case alias of dangling junction accepted');
  expectFailure(function(){io.relativeFile(NativeBridge.getFileFromPath('dangling/no-write'),true);},'missing dangling relative path accepted');
});
run('pure missing map paths are checked before creation and server roots remain existing-only',function(){
  var relative='journeymap/data/sp/NotYetCreated/deep';
  var missing=NativeBridge.getFileFromPath(relative);
  assertOk(!missing.exists(),'fixture target unexpectedly exists');
  expectFailure(function(){io.relativeFile(missing);},'missing server world root accepted by default');
  assertOk(io.relativeFile(missing,true)===relative,'safe missing map path refused');
  assertOk(!missing.exists(),'path validation created the map');
  expectFailure(function(){io.relativeFile(NativeBridge.getFileFromPath('alias/no-write/deep'),true);},'external missing target accepted');
  expectFailure(function(){io.relativeFile(NativeBridge.getFileFromPath('internal-alias/no-write/deep'),true);},'internal alias missing target accepted');
  expectFailure(function(){io.relativeFile(NativeBridge.getFileFromPath('../outside/no-write'),true);},'lexical escape missing target accepted');
  io.mkdirs(relative);
  assertOk(missing.isDirectory(),'policy could not create previously validated path');
});
run('unlistable existing parent refuses a new child before writes',function(){
  io.mkdirs('unlistable-parent');NativeBridge.failNextList('unlistable-parent');
  expectFailure(function(){io.mkdirs('unlistable-parent/no-write');},'unlistable parent accepted');
  assertOk(!NativeBridge.getFileFromPath('unlistable-parent/no-write').exists(),'unlistable parent was written');
});
run('unsafe lexical paths refuse before writes',function(){
  var values=['../escape','/escape','C:/escape','saves\\escape','saves//escape','saves/../escape'];
  for(var i=0;i<values.length;i++)(function(value){expectFailure(function(){io.mkdirs(value);},'unsafe '+value);})(values[i]);
});
run('rename refuses a collision and never copies or deletes source',function(){
  NativeBridge.writeTest('source-points/legit.json','{"payload":"KEEP"}');io.mkdirs('existing-archive');
  expectFailure(function(){io.rename('source-points','existing-archive');},'archive collision accepted');
  assertOk(NativeBridge.readTest('source-points/legit.json').indexOf('KEEP')>=0,'source data lost');
});
run('remove and atomic-write APIs refuse legitimate waypoint payloads',function(){
  NativeBridge.writeTest('journeymap/data/sp/Keep/waypoints/legit.json','{"payload":"KEEP"}');
  expectFailure(function(){io.removeFile('journeymap/data/sp/Keep/waypoints/legit.json');},'waypoint deletion allowed');
  expectFailure(function(){io.writeJsonAtomic('journeymap/data/sp/Keep/waypoints/legit.json',{bad:true});},'waypoint rewrite allowed');
  assertOk(NativeBridge.readTest('journeymap/data/sp/Keep/waypoints/legit.json').indexOf('KEEP')>=0,'waypoint changed');
});
run('native core same-name same-seed recreation/reopen/restoration preserves both waypoint sets and images',function(){
  var save='saves/Core',map='journeymap/data/sp/Core',w=save+'/lanmc-waypoints-world.json';
  NativeBridge.writeTest(save+'/level.seed.fixture','42');
  NativeBridge.writeTest(map+'/waypoints/legitA.json','{"payload":"A"}');
  NativeBridge.writeTest(map+'/DIM0/region.png','IMAGE');
  var policy=createWaypointGenerationPolicy(io);policy.bootstrap([{saveRoot:save,mapRoot:map}]);
  var a=io.readJson(w);assertOk(io.removeFile(w),'fixture generation removal');
  var b=policy.associate(save,map);assertOk(a.worldId!==b.worldId,'same seed reused id');
  assertOk(!io.file(map+'/waypoints').exists(),'A leaked to B');
  NativeBridge.writeTest(map+'/waypoints/legitB.json','{"payload":"B"}');
  policy.associate(save,map);assertOk(io.file(map+'/waypoints/legitB.json').exists(),'B lost on reopen');
  io.writeJsonAtomic(w,a);policy.associate(save,map);
  assertOk(io.file(map+'/waypoints/legitA.json').exists(),'A not restored');
  assertOk(!io.file(map+'/waypoints/legitB.json').exists(),'B leaked to A');
  assertOk(NativeBridge.readTest(map+'/DIM0/region.png')==='IMAGE','image moved or changed');
});
run('native committed-owner journal retry preserves legitimate new points',function(){
  var save='saves/PostCommit',map='journeymap/data/sp/PostCommit',w=save+'/lanmc-waypoints-world.json';
  NativeBridge.writeTest(save+'/level.seed.fixture','42');NativeBridge.writeTest(map+'/waypoints/legitA.json','{"payload":"A"}');
  var policy=createWaypointGenerationPolicy(io);policy.bootstrap([{saveRoot:save,mapRoot:map}]);io.removeFile(w);
  NativeBridge.failNextDelete('lanmc-waypoints-transition.json');
  expectFailure(function(){policy.associate(save,map);},'journal delete should fail');
  NativeBridge.writeTest(map+'/waypoints/new-after-commit.json','{"payload":"NEW"}');
  policy.associate(save,map);assertOk(io.file(map+'/waypoints/new-after-commit.json').exists(),'new point lost');
});
JSON.stringify({checks:checks.length,passed:checks.filter(function(x){return x.status==='PASS';}).length,cases:checks});
