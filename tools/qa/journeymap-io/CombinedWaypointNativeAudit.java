import dev.latvian.mods.rhino.*;import dev.latvian.mods.kubejs.util.ClassFilter;import java.nio.file.*;
public final class CombinedWaypointNativeAudit {
 public static void main(String[] args)throws Exception{
  Path base=Path.of(args[0]).toAbsolutePath().normalize();if(!base.toString().contains("artifacts"))throw new IllegalArgumentException("Artifact-only fixture");Files.createDirectories(base);WaypointIoNativeAudit.base=base;
  ClassFilter f=new ClassFilter();
 
 f.deny("java.lang");
f.allow("java.lang.Number");
f.allow("java.lang.String");
f.allow("java.lang.Character");
f.allow("java.lang.Byte");
f.allow("java.lang.Short");
f.allow("java.lang.Integer");
f.allow("java.lang.Long");
f.allow("java.lang.Float");
f.allow("java.lang.Double");
f.allow("java.lang.Boolean");
f.allow("java.lang.Runnable");
f.allow("java.lang.Iterable");
f.allow("java.lang.Comparable");
f.allow("java.lang.CharSequence");
f.allow("java.lang.Void");
f.allow("java.lang.Package");
f.allow("java.lang.Appendable");
f.allow("java.lang.AutoCloseable");
f.allow("java.lang.Comparable");
f.allow("java.lang.Iterable");
f.allow("java.lang.Object");
f.allow("java.lang.Runnable");
f.allow("java.lang.StringBuilder");
f.allow("java.math.BigInteger");
f.allow("java.math.BigDecimal");
f.deny("java.io");
f.allow("java.io.Closeable");
f.allow("java.io.Serializable");
f.deny("java.nio");
f.allow("java.nio.ByteOrder");
f.allow("java.util");
f.deny("java.util.jar");
f.deny("java.util.zip");
f.allow("it.unimi.dsi.fastutil");
f.allow("dev.latvian.mods.kubejs");
f.deny("dev.latvian.mods.kubejs.script");
f.deny("dev.latvian.mods.kubejs.mixin");
f.deny("dev.latvian.mods.kubejs.KubeJSPlugin");
f.deny("dev.latvian.mods.kubejs.util.KubeJSPlugins");
f.allow("net.minecraft");
f.allow("com.mojang.authlib.GameProfile");
f.allow("com.mojang.util.UUIDTypeAdapter");
f.allow("com.mojang.brigadier");
f.allow("com.mojang.blaze3d");
f.allow("dev.architectury");
f.deny("java.net");
f.deny("sun");
f.deny("com.sun");
f.deny("io.netty");
f.deny("org.objectweb.asm");
f.deny("org.spongepowered.asm");
f.deny("org.openjdk.nashorn");
f.deny("jdk.nashorn");
f.allow("mezz.jei");
  
  
  Context cx=Context.enter();cx.setClassShutter((name,kind)->kind!=2||f.isAllowed(name));ScriptableObject scope=cx.initStandardObjects();
  ScriptableObject.putProperty(scope,"NativeBridge",new NativeJavaClass(cx,scope,WaypointIoNativeAudit.NativeBridge.class),cx);
  ScriptableObject.putProperty(scope,"FileUtilsType",new NativeJavaClass(cx,scope,org.apache.commons.io.FileUtils.class),cx);
  ScriptableObject.putProperty(scope,"UuidType",new NativeJavaClass(cx,scope,java.util.UUID.class),cx);
  ScriptableObject.putProperty(scope,"MODE",args[5],cx);
  cx.evaluateString(scope,Files.readString(Path.of(args[1])),"explicit-platform-and-forge-models",1,null);
  cx.evaluateString(scope,Files.readString(Path.of(args[2])),"actual-combined-policy-IIFE",1,null);
  Object value=cx.evaluateString(scope,Files.readString(Path.of(args[3])),"combined-native-filesystem-cases",1,null);
  String text=cx.toString(value);Files.writeString(Path.of(args[4]),text+"\n");System.out.println(text);
 }
}
