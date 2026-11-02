import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.NativeJavaClass;
import dev.latvian.mods.rhino.Scriptable;
import dev.latvian.mods.rhino.ScriptableObject;
import java.nio.file.Files;
import java.nio.file.Path;

/** Artifact-only actual Rhino/native JM public-method probe. No world/store paths. */
public final class NativeWaypointProbe {
  public static void main(String[] args) throws Exception {
    Context cx = Context.enter();
    Scriptable scope = cx.initStandardObjects();
    Class<?> waypoint = Class.forName("journeymap.client.waypoint.Waypoint");
    ScriptableObject.putProperty(scope, "NativeWaypoint", new NativeJavaClass(cx, scope, waypoint), cx);
    Class<?> store = Class.forName("journeymap.client.waypoint.WaypointStore");
    ScriptableObject.putProperty(scope, "NativeWaypointStore", new NativeJavaClass(cx, scope, store), cx);
    ScriptableObject.putProperty(scope, "NativeDateFormat", new NativeJavaClass(cx, scope, java.text.SimpleDateFormat.class), cx);
    ScriptableObject.putProperty(scope, "NativeParsePosition", new NativeJavaClass(cx, scope, java.text.ParsePosition.class), cx);
    ScriptableObject.putProperty(scope, "NativeTimeZone", new NativeJavaClass(cx, scope, java.util.TimeZone.class), cx);
    Object result = cx.evaluateString(scope, Files.readString(Path.of(args[0])), "native-waypoint-probe", 1, null);
    System.out.println(cx.toString(result));
  }
}
