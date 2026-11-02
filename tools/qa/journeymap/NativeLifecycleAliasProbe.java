import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.NativeJavaClass;
import dev.latvian.mods.rhino.Scriptable;
import dev.latvian.mods.rhino.ScriptableObject;
import dev.latvian.mods.rhino.mod.util.MinecraftRemapper;
import java.io.InputStream;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.GZIPInputStream;
import com.google.gson.Gson;

/** Native mapping/public API fixture only: no server allocation or game boot. */
public final class NativeLifecycleAliasProbe {
  static Class<?> cls(String name) throws Exception {
    return Class.forName(name, false, NativeLifecycleAliasProbe.class.getClassLoader());
  }
  static void method(Map<String,Object> checks, MinecraftRemapper remapper, String owner, String nativeName, String expected, Class<?>... parameters) throws Exception {
    Class<?> c=cls(owner);
    String actual=remapper.getMappedMethod(c,c.getMethod(nativeName,parameters));
    if (!expected.equals(actual)) throw new AssertionError(owner+"."+nativeName+" -> "+actual);
    checks.put(owner+"."+nativeName,actual);
  }
  public static void main(String[] args) throws Exception {
    MinecraftRemapper remapper;
    try (InputStream raw=NativeLifecycleAliasProbe.class.getClassLoader().getResourceAsStream("mm.jsmappings");
         InputStream in=new GZIPInputStream(raw)) { remapper=MinecraftRemapper.load(in,false); }
    Map<String,Object> checks=new LinkedHashMap<>();
    method(checks,remapper,"net.minecraft.server.MinecraftServer","m_129843_","getWorldPath",cls("net.minecraft.world.level.storage.LevelResource"));
    method(checks,remapper,"net.minecraft.server.MinecraftServer","m_129910_","getWorldData");
    method(checks,remapper,"net.minecraft.world.level.storage.WorldData","m_5462_","getLevelName");
    method(checks,remapper,"net.minecraft.world.level.storage.LevelStorageSource$LevelStorageAccess","m_78277_","getLevelId");
    method(checks,remapper,"net.minecraft.client.Minecraft","m_91087_","getInstance");
    method(checks,remapper,"net.minecraft.client.Minecraft","m_91091_","hasSingleplayerServer");
    method(checks,remapper,"net.minecraft.client.Minecraft","m_91092_","getSingleplayerServer");
    checks.put("native-public-FileHandler.getJMWorldDir",cls("journeymap.client.io.FileHandler").getMethod("getJMWorldDir",cls("net.minecraft.client.Minecraft")).getReturnType().getName());
    checks.put("native-public-FileHandler.getJMWorldDirForWorldId",cls("journeymap.client.io.FileHandler").getMethod("getJMWorldDirForWorldId",cls("net.minecraft.client.Minecraft"),String.class).getReturnType().getName());
    Class<?> levelResource=cls("net.minecraft.world.level.storage.LevelResource");
    String root=remapper.getMappedField(levelResource,levelResource.getField("f_78182_"));
    if (!root.equals("ROOT")) throw new AssertionError(root);
    checks.put("LevelResource.f_78182_",root);
    checks.put("IntegratedServer-is-MinecraftServer",cls("net.minecraft.server.MinecraftServer").isAssignableFrom(cls("net.minecraft.client.server.IntegratedServer")));
    Class<?> jm=cls("journeymap.client.JourneymapClient");
    checks.put("native-public-JourneymapClient.getInstance",jm.getMethod("getInstance").getReturnType().getName());
    checks.put("native-public-JourneymapClient.getCurrentWorldId",jm.getMethod("getCurrentWorldId").getReturnType().getName());
    Context cx=Context.enter(); cx.setRemapper(remapper); Scriptable scope=cx.initStandardObjects();
    ScriptableObject.putProperty(scope,"LevelResource",new NativeJavaClass(cx,scope,levelResource),cx);
    Object result=cx.evaluateString(scope,"String(LevelResource.ROOT.getId())", "native-mojmap-alias-probe",1,null);
    if (!".".equals(cx.toString(result))) throw new AssertionError(result);
    checks.put("actualRhino-LevelResource.ROOT.getId",cx.toString(result));
    ScriptableObject.putProperty(scope,"CommonConstants",new NativeJavaClass(cx,scope,cls("journeymap.common.CommonConstants")),cx);
    result=cx.evaluateString(scope,"String(CommonConstants.getSafeString('Новый мир: two','~'))", "native-map-root-safe-name",1,null);
    if (!"Новый мир~ two".equals(cx.toString(result))) throw new AssertionError(result);
    checks.put("actualRhino-native-safe-name",cx.toString(result));
    ScriptableObject.putProperty(scope,"JavaString",new NativeJavaClass(cx,scope,String.class),cx);
    result=cx.evaluateString(scope,"['','plain-id','id:-12','a b','ЖЮ漢字','ab__12','!!!'].every(function(id){return id.replace(/\\W+/g,'~')===String(new JavaString(id).replaceAll('\\\\W+','~'));})", "native-id-suffix-sanitize",1,null);
    if (!"true".equals(cx.toString(result))) throw new AssertionError(result);
    checks.put("actualRhino-id-suffix-equivalent-to-Java-replaceAll",true);
    checks.put("status","PASS_NATIVE_MAPPING_AND_SAFE_STATIC_ALIAS_ONLY");
    System.out.println(new Gson().toJson(checks));
  }
}
