// Synthetic lifecycle dispatcher on actual Rhino. Native aliases are a separate
// pinned probe. No claim this model posts a real Forge event or runs Minecraft.
var lifecycleChecks=[];
function lifecycleCheck(label,value){if(!value)throw new Error(label);lifecycleChecks.push(label);}
function installLifecycleModel(options){
  var callbacks={},postInit=null,associateCalls=0,bootstrapCalls=0,nativeSelections=0,warnings=[];
  var global={}, readySave={exists:function(){return true;},isDirectory:function(){return true;},getName:function(){return 'Actual-folder';}};
  var io={file:function(){return {exists:function(){return options.noSaves!==true;},isDirectory:function(){return options.savesIsFile!==true;},listFiles:function(){return options.nullListing ? null : [readySave];}};},
    exists:function(){return true;},assertPath:function(p){if(options.pathFailure)throw new Error('unsafe path');},
    relativeFile:function(f){return f.path;}};
  var server={getWorldPath:function(){return {toFile:function(){return {path:options.unexpectedSave?'elsewhere/s': 'saves/Actual-folder'};}};}};
  var mc={hasSingleplayerServer:function(){return options.multiplayer!==true;},getSingleplayerServer:function(){return server;}};
  var bindings={Platform:{isClientEnvironment:function(){return true;},isLoaded:function(){return true;}},
    StartupEvents:{postInit:function(fn){postInit=fn;}},ForgeEvents:{onEvent:function(name,fn){callbacks[name]=fn;}},
    Java:{loadClass:function(name){
      if(name==='net.minecraft.client.Minecraft')return {getInstance:function(){return mc;}};
      if(name==='net.minecraft.world.level.storage.LevelResource')return {ROOT:{}};
      if(name==='journeymap.client.io.FileHandler')return {getJMWorldDir:function(){throw new Error('Mutating native wrapper must not be called');},getJMWorldDirForWorldId:function(mc,id){if(id!=='native-id')throw new Error('Native ID was changed');nativeSelections++;return {path: options.selectedMap || 'journeymap/data/sp/Actual~folder_exact-id'};}};
      if(name==='journeymap.client.JourneymapClient')return {getInstance:function(){return {getCurrentWorldId:function(){return 'native-id';}};}};
      throw new Error('unexpected class '+name);
    }},console:{warn:function(m){warnings.push(m);}},global:global,
    createWaypointIo:function(){return io;},createWaypointGenerationPolicy:function(){return {
      bootstrap:function(){bootstrapCalls++;if(options.bootstrapFailure)throw new Error('bootstrap failure');},
      associate:function(save,map){associateCalls++;return {saveRoot:save,mapRoot:map};}};}};
  // Model loader supplied by the Java harness in a fresh child scope.
  runLifecycle(bindings);
  return {boot:function(){postInit();},login:function(){callbacks['net.minecraftforge.client.event.ClientPlayerNetworkEvent$LoggingIn']({});},
    calls:function(){return associateCalls;},selections:function(){return nativeSelections;},context:function(){return global.lanmcWaypointGeneration;},warnings:function(){return warnings.length;}};
}
var m=installLifecycleModel({});m.boot();m.login();
lifecycleCheck('native-selected-map-used-without-manual-fallback',m.calls()===1 && m.context().mapRoot==='journeymap/data/sp/Actual~folder_exact-id');
m=installLifecycleModel({bootstrapFailure:true});m.boot();m.login();
lifecycleCheck('bootstrap-failure-login-does-not-associate',m.calls()===0 && m.selections()===0 && m.context()===null && m.warnings()===2);
m=installLifecycleModel({});m.login();lifecycleCheck('login-before-bootstrap-preserves',m.calls()===0 && m.selections()===0 && m.context()===null);
m=installLifecycleModel({multiplayer:true});m.boot();m.login();lifecycleCheck('remote-multiplayer-untouched',m.calls()===0 && m.selections()===0);
m=installLifecycleModel({unexpectedSave:true});m.boot();m.login();lifecycleCheck('unexpected-save-root-refused',m.calls()===0 && m.selections()===0);
m=installLifecycleModel({selectedMap:'journeymap/data/mp/remote'});m.boot();m.login();lifecycleCheck('unexpected-map-root-refused',m.calls()===0);
m=installLifecycleModel({pathFailure:true});m.boot();m.login();lifecycleCheck('path-bootstrap-failure-preserves',m.calls()===0 && m.selections()===0);
m=installLifecycleModel({nullListing:true});m.boot();m.login();lifecycleCheck('existing-saves-null-listing-preserves',m.calls()===0 && m.selections()===0 && m.context()===null);
m=installLifecycleModel({savesIsFile:true});m.boot();m.login();lifecycleCheck('saves-is-file-preserves',m.calls()===0 && m.selections()===0 && m.context()===null);
m=installLifecycleModel({noSaves:true});m.boot();m.login();lifecycleCheck('absent-saves-boot-then-new-world-associates',m.calls()===1);
JSON.stringify({status:'PASS',checks:lifecycleChecks,scope:'Synthetic dispatcher/policy/IO model on actual Rhino only; no Forge event, native IO, world, or game runtime PASS.'});
