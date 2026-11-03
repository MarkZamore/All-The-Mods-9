// Concatenate after the reviewed core and IO adapter in ONE startup script.
// Exact target: Minecraft 1.20.1, Forge 47.4.0, KubeJS 2001.6.5-build.16,
// JourneyMap 5.10.3. LoggingIn is synchronous before its next mapping tick.
if (Platform.isClientEnvironment() && Platform.isLoaded('journeymap')) {
  (function () {
    var io = null;
    var policy = null;
    var ready = false;
    var Minecraft = null;
    var LevelResource = null;
    var FileHandler = null;
    var JourneyMapClient = null;
    var jmRoot = 'journeymap/data/sp/';
    StartupEvents.postInit(function () {
      ready = false;
      try {
        Minecraft = Java.loadClass('net.minecraft.client.Minecraft');
        var nativeSaves = Minecraft.getInstance().getLevelSource().getBaseDir().toFile();
        io = createWaypointIo({nativeSavesRootFile: nativeSaves});
        policy = createWaypointGenerationPolicy(io);
        LevelResource = Java.loadClass('net.minecraft.world.level.storage.LevelResource');
        FileHandler = Java.loadClass('journeymap.client.io.FileHandler');
        JourneyMapClient = Java.loadClass('journeymap.client.JourneymapClient');
        var root = io.file('saves');
        var files = null;
        if (root.exists()) {
          if (!root.isDirectory()) throw new Error('Saves path is not a directory');
          files = root.listFiles();
          if (files === null) throw new Error('Existing saves could not be enumerated');
        }
        var saves = [];
        if (files) {
          for (var i = 0; i < files.length; i++) {
            if (!files[i].isDirectory()) continue;
            var folder = String(files[i].getName());
            var saveRoot = 'saves/' + folder;
            io.assertPath(saveRoot);
            if (!io.exists(saveRoot + '/level.dat') && !io.exists(saveRoot + '/level.dat_old')) continue;
            saves.push({saveRoot: saveRoot, mapRoot: jmRoot + folder});
          }
        }
        policy.bootstrap(saves);
        ready = true;
      } catch (error) {
        console.warn('Waypoint association bootstrap failed; existing waypoints are preserved: ' + error);
      }
    });
    ForgeEvents.onEvent('net.minecraftforge.client.event.ClientPlayerNetworkEvent$LoggingIn', function () {
      global.lanmcWaypointGeneration = null;
      if (!ready || !policy || !io) {
        console.warn('Waypoint association is not ready; existing waypoints are preserved');
        return;
      }
      try {
        var mc = Minecraft.getInstance();
        if (!mc.hasSingleplayerServer()) return;
        var server = mc.getSingleplayerServer();
        if (server === null) throw new Error('Missing integrated server');
        var saveRoot = String(io.relativeFile(server.getWorldPath(LevelResource.ROOT).toFile()));
        if (!/^saves\/[^/]+$/.test(saveRoot)) throw new Error('Unexpected world directory');
        io.assertPath(saveRoot);
        io.assertPath('journeymap/data/sp');
        // Native selection includes actual folder, legacy fallback and current
        // world ID suffix. No manual display-name or seed reconstruction.
        var worldId = JourneyMapClient.getInstance().getCurrentWorldId();
        var mapRoot = String(io.relativeFile(FileHandler.getJMWorldDirForWorldId(mc, worldId), true));
        if (!/^journeymap\/data\/sp\/[^/]+$/.test(mapRoot)) throw new Error('Unexpected JourneyMap directory');
        io.assertPath(mapRoot);
        global.lanmcWaypointGeneration = policy.associate(saveRoot, mapRoot);
      } catch (error) {
        console.warn('Waypoint association skipped; existing waypoints are preserved: ' + error);
      }
    });
  })();
}
