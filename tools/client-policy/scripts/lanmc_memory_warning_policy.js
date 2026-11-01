// priority: 1000
// Keep the launcher's chosen heap without Memory Settings' upper-memory panel.
// KubeJS loads this before Memory Settings' initial game-menu check. This
// changes one loaded option and never rewrites the player's memorysettings.json.
(() => {
  const Configuration = Java.loadClass('com.memorysettings.config.CommonConfiguration')
  Configuration.config.getCommonConfig().disableWarnings = true
})()
