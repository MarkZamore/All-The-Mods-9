function check(ok,message){if(!ok)throw new Error(message);}
var result={mode:String(MODE),checks:[],scope:'Actual combined IIFE/core/IO executes on native Rhino/File/Path/CommonsIO. Platform, Forge callbacks, Minecraft server and JourneyMap path selection are explicit models.'};
function run(name,f){try{f();result.checks.push({name:name,status:'PASS'});}catch(e){result.checks.push({name:name,status:'FAIL',error:String(e)});}}
if(String(MODE)==='positive'||String(MODE)==='trusted-junction'){
 run('combined startup bootstrap adopts existing legitimate waypoints',function(){
  check(startupCallbacks.length===1&&loginCallbacks.length===1,'event registration');startupCallbacks[0]();
  var marker=JSON.parse(NativeBridge.readTest(model.saveRoot+'/lanmc-waypoints-world.json'));
  check(marker.birthMillis===0&&!marker.legacyEligible,'existing marker ownership');
  check(NativeBridge.getFileFromPath(model.mapRoot+'/waypoints/legitA.json').exists(),'A lost during bootstrap');
 });
 var oldWorld=JSON.parse(NativeBridge.readTest(model.saveRoot+'/lanmc-waypoints-world.json'));
 run('combined LoggingIn associates existing world before next mapping tick model',function(){
  loginCallbacks[0]();check(global.lanmcWaypointGeneration!==null,'not associated');
  check(global.lanmcWaypointGeneration.worldId===oldWorld.worldId,'existing UUID changed');
 });
 var newWorld;
 run('combined same-name same-seed recreation archives old points',function(){
  check(NativeBridge.getFileFromPath(model.saveRoot+'/lanmc-waypoints-world.json').delete(),'fixture generation marker removal');
  loginCallbacks[0]();newWorld=global.lanmcWaypointGeneration;
  check(newWorld!==null&&newWorld.worldId!==oldWorld.worldId,'new UUID missing');
  check(!NativeBridge.getFileFromPath(model.mapRoot+'/waypoints').exists(),'oldpoints leaked into new generation');
  check(NativeBridge.readTest(model.mapRoot+'/DIM0/region.png')==='IMAGE','images changed');
 });
 run('combined same-UUID reopen keeps new legitimate points',function(){
  NativeBridge.writeTest(model.mapRoot+'/waypoints/legitB.json','{"payload":"B"}');
  loginCallbacks[0]();check(global.lanmcWaypointGeneration.worldId===newWorld.worldId,'reopen UUID changed');
  check(NativeBridge.getFileFromPath(model.mapRoot+'/waypoints/legitB.json').exists(),'newpoint lost');
 });
 run('combined restored old-UUID world recovers old points and archives new set',function(){
  NativeBridge.writeTest(model.saveRoot+'/lanmc-waypoints-world.json',JSON.stringify(oldWorld));loginCallbacks[0]();
  check(global.lanmcWaypointGeneration.worldId===oldWorld.worldId,'old UUID not restored');
  check(NativeBridge.getFileFromPath(model.mapRoot+'/waypoints/legitA.json').exists(),'oldpoint not restored');
  check(!NativeBridge.getFileFromPath(model.mapRoot+'/waypoints/legitB.json').exists(),'newpoint leaked into oldworld');
  var owner=JSON.parse(NativeBridge.readTest(model.mapRoot+'/lanmc-waypoints-owner.json'));
  check(NativeBridge.getFileFromPath('local/lanmc-waypoint-archives/v1/'+owner.slotId+'/'+newWorld.worldId+'/waypoints/legitB.json').exists(),'newpoint not retained in archive');
  check(warnings.length===0,'unexpected warning '+warnings.join(';'));
 });
 run('combined pure resolver accepts a missing map only after guarded validation',function(){
  model.saveRoot='saves/NewMissingMap';model.mapRoot='journeymap/data/sp/NewMissingMap';
  NativeBridge.writeTest(model.saveRoot+'/level.dat','SYNTHETIC-SAME-SEED-42');
  check(!NativeBridge.getFileFromPath(model.mapRoot).exists(),'map existed before resolver');
  loginCallbacks[0]();
  check(global.lanmcWaypointGeneration!==null,'missing map not associated');
  check(NativeBridge.getFileFromPath(model.mapRoot+'/lanmc-waypoints-owner.json').isFile(),'validated map owner missing');
  check(!NativeBridge.getFileFromPath(model.mapRoot+'/waypoints').exists(),'unexpected waypoint payload created');
  check(warnings.length===0,'unexpected missing-map warning '+warnings.join(';'));
 });
 if(String(MODE)==='trusted-junction'){
  var secure=createWaypointIo({nativeSavesRootFile:NativeBridge.getFileFromPath('saves')});
  var refused=function(f){var error=null;try{f();}catch(e){error=String(e);}check(error!==null&&error.indexOf('Waypoint IO:')>=0&&error.indexOf('ambiguous')<0,'expected an exact path guard refusal, got '+error);};
  run('authoritative saves junction accepts lexical and canonical world paths',function(){
   var f=NativeBridge.getFileFromPath(model.saveRoot);
   check(secure.relativeFile(f)===model.saveRoot,'lexical world path refused');
   check(secure.relativeFile(f.toPath().toRealPath().toFile())===model.saveRoot,'canonical native world path refused');
   check(secure.readJson(model.saveRoot+'/lanmc-waypoints-world.json').schemaVersion===1,'owned metadata unavailable through saves junction');
  });
  run('nested junction remains refused under the trusted saves root',function(){
   refused(function(){secure.assertPath('saves/Combined/nested-alias/no-write');});
   refused(function(){secure.mkdirs('saves/Combined/nested-alias/no-write');});
   check(!NativeBridge.getFileFromPath('saves/Combined/nested-alias/no-write').exists(),'nested target was written');
  });
  run('a trusted saves junction retarget is refused before IO',function(){
   NativeBridge.swapSavesJunction();
   refused(function(){secure.assertPath('saves/no-write');});
   refused(function(){secure.mkdirs('saves/no-write');});
   check(!NativeBridge.getFileFromPath('saves/no-write').exists(),'retargeted root was written');
  });
 }
}else if(String(MODE)==='bootstrap-failure'){
 run('existing saves enumeration failure leaves policy unready',function(){
  NativeBridge.failNextList('saves');startupCallbacks[0]();loginCallbacks[0]();
  check(global.lanmcWaypointGeneration===null,'failed bootstrap marked ready');
  check(!NativeBridge.getFileFromPath(model.saveRoot+'/lanmc-waypoints-world.json').exists(),'failed bootstrap created worldUUID');
  check(!NativeBridge.getFileFromPath(model.mapRoot+'/lanmc-waypoints-owner.json').exists(),'failed bootstrap changed owner');
  check(NativeBridge.getFileFromPath(model.mapRoot+'/waypoints/legitA.json').exists(),'failed bootstrap moved legitimatepoints');
  check(warnings.length>=2,'missing bounded diagnostics');
 });
}else throw new Error('Unexpected mode');
result.passed=result.checks.filter(function(x){return x.status==='PASS';}).length;JSON.stringify(result);
