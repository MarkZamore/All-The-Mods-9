import com.google.gson.*;
import com.memorysettings.config.CommonConfiguration;
import dev.latvian.mods.rhino.*;
import net.minecraftforge.fml.loading.FMLPaths;
import java.nio.file.*;
import java.util.*;

public class NativeMemory59Probe {
  static Context cx; static Scriptable scope;
  public static class JavaBinding {
    public Object loadClass(String name) throws Exception {
      if (!name.equals("com.memorysettings.config.CommonConfiguration")) throw new AssertionError(name);
      return new NativeJavaClass(cx, scope, Class.forName(name));
    }
  }
  static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
  public static void main(String[] args) throws Exception {
    Path pack=Path.of(args[0]).toAbsolutePath();
    Path fixture=Path.of("").toAbsolutePath();
    check(!Files.exists(fixture.resolve("mods")) && !Files.exists(fixture.resolve("portable-pack.json")),"Use fresh separate fixture");
    Files.createDirectories(fixture.resolve("config"));
    check(!Files.exists(fixture.resolve("config/memorysettings.json")),"Fixture already has a config file");
    Files.copy(pack.resolve("config/memorysettings.json"),fixture.resolve("config/memorysettings.json"));
    FMLPaths.loadAbsolutePaths(fixture);
    var memory = CommonConfiguration.config.getCommonConfig();
    memory.maximumClient=55555; memory.minimumClient=7001; memory.warningTolerance=73;
    memory.howtolink="https://example.invalid/synthetic-personal-choice"; memory.disableWarnings=false;
    var before=memory.serialize(); byte[] original=Files.readAllBytes(Path.of("config/memorysettings.json"));
    cx=Context.enter(); scope=cx.initStandardObjects();
    ScriptableObject.putProperty(scope,"Java",Context.javaToJS(cx,new JavaBinding(),scope),cx);
    String script=Files.readString(pack.resolve("kubejs/client_scripts/lanmc_memory_warning_policy.js"));
    cx.evaluateString(scope,script,"lanmc_memory_warning_policy.js",1,null);
    var after=memory.serialize(); var changed=new TreeSet<String>();
    check(before.keySet().equals(after.keySet()),"Field set changed");
    for(var key:before.keySet())if(!before.get(key).equals(after.get(key)))changed.add(key);
    check(changed.equals(Set.of("disableWarnings"))&&memory.disableWarnings,"Unrelated native field changed: "+changed);
    check(Arrays.equals(original,Files.readAllBytes(Path.of("config/memorysettings.json"))),"Personal JSON rewritten");
    cx.evaluateString(scope,script,"repeat-policy.js",1,null);
    check(after.equals(memory.serialize()),"Not idempotent");
    System.out.println("{\"status\":\"PASS\",\"actualRhino2001\":true,\"actualMemorySettings59AndCupboard27\":true,\"changedNativeFields\":[\"disableWarnings\"],\"personalJSONBytesUnchanged\":true,\"idempotent\":true,\"limit\":\"Standalone native API/Rhino only; no client run\"}");
  }
}
