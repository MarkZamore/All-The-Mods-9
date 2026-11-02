import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.ScriptableObject;
import java.nio.file.Files;
import java.nio.file.Path;
/** Synthetic dispatch bindings on actual Rhino; no Forge event or game boot. */
public final class NativeLifecycleModelProbe {
 public static void main(String[] args) throws Exception {
  Context cx=Context.enter();
  {
   var scope=cx.initStandardObjects();
   ScriptableObject.putProperty(scope,"lifecycleSource",Files.readString(Path.of(args[0])),cx);
   cx.evaluateString(scope,"function runLifecycle(b){var Platform=b.Platform,StartupEvents=b.StartupEvents,ForgeEvents=b.ForgeEvents,Java=b.Java,console=b.console,global=b.global,createWaypointIo=b.createWaypointIo,createWaypointGenerationPolicy=b.createWaypointGenerationPolicy;eval(String(lifecycleSource));}","explicit-model-bindings",1,null);
   Object result=cx.evaluateString(scope,Files.readString(Path.of(args[1])),"lifecycle-model",1,null);
   System.out.println(cx.toString(result));
  }
 }
}
