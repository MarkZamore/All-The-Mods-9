import dev.latvian.mods.rhino.*;
import dev.latvian.mods.kubejs.util.ClassFilter;
import java.io.*;import java.nio.file.*;
public final class WaypointIoNativeAudit {
 static Path base;static String failRename="",failDelete="",failList="";
 // BuiltinKubeJSPlugin registers all three accept-all type wrappers. Omitting
 // them lets raw Rhino choose Path/String overloads that are ambiguous in game.
 // String uses the actual native factory; Path/File mirror UtilsJS's verified
 // bytecode because loading UtilsJS itself requires the complete Minecraft.
 // verifyFilePath is lexical, just as in KubeJS; the production IO adds its
 // separate real-path/junction checks. No wrapper relaxes the fixture root.
 static void registerBuiltinPathWrappers(Context cx){
  cx.getTypeWrappers().registerSimple(String.class,String::valueOf);
  cx.getTypeWrappers().registerSimple(Path.class,WaypointIoNativeAudit::fixtureGetPath);
  cx.getTypeWrappers().registerSimple(File.class,WaypointIoNativeAudit::fixtureGetFile);
 }
 static Path fixtureGetPath(Object value){
  try{
   if(value==null||value.toString().isEmpty())return null;
   Path path=value instanceof Path p?p:base.resolve(value.toString());
   if(!path.normalize().toAbsolutePath().startsWith(base))throw new IOException("Outside fixture game directory");
   return path;
  }catch(Exception refused){return null;}
 }
 static File fixtureGetFile(Object value){
  Path path=fixtureGetPath(value instanceof File f?f.toPath():value);
  return path==null?null:path.toFile();
 }
 public static final class GuardedFile extends File {
  GuardedFile(String path){super(path);}
  @Override public boolean renameTo(File target){if(!failRename.isEmpty()&&getPath().contains(failRename)){failRename="";return false;}return super.renameTo(target);}
  @Override public File[] listFiles(){if(!failList.isEmpty()&&getPath().endsWith(failList)){failList="";return null;}return super.listFiles();}
  @Override public boolean delete(){if(!failDelete.isEmpty()&&getPath().endsWith(failDelete)){failDelete="";return false;}return super.delete();}
 }
 public static final class NativeBridge {
  public static File getFileFromPath(Object value){String text=value.toString();Path p=Path.of(text);if(!p.isAbsolute())p=base.resolve(p);p=p.toAbsolutePath().normalize();if(!p.startsWith(base))throw new IllegalArgumentException("Fixture path escaped root");return new GuardedFile(p.toString());}
  public static void failNextRename(String text){failRename=text;}
  public static void failNextDelete(String text){failDelete=text;}
  public static void failNextList(String text){failList=text;}
  public static void writeTest(String relative,String text)throws Exception{Path p=getFileFromPath(relative).toPath();Files.createDirectories(p.getParent());Files.writeString(p,text);}
  public static String readTest(String relative)throws Exception{return Files.readString(getFileFromPath(relative).toPath());}
  public static int countRetained(String relative)throws Exception{try(var s=Files.list(getFileFromPath(relative).toPath())){return(int)s.filter(p->p.getFileName().toString().contains(".retained-")).count();}}
  public static void swapSavesJunction()throws Exception{
   Path current=base.resolve("saves"), parked=base.resolve("saves-before-retarget"), replacement=base.resolve("replacement-saves");
   Path fixture=base.getParent().toRealPath();
   if(!current.getParent().equals(base)||!parked.getParent().equals(base)||!replacement.getParent().equals(base)
     ||!current.toRealPath().startsWith(fixture)||!replacement.toRealPath().startsWith(fixture)||Files.exists(parked))
    throw new IllegalStateException("Refuse to move unverified private fixture aliases");
   // Rename only the two owned junction entries; no recursive move/delete.
   Files.move(current,parked);Files.move(replacement,current);
  }
 }
 public static void main(String[] args)throws Exception{
  base=Path.of(args[0]).toAbsolutePath().normalize();if(!base.toString().contains("artifacts"))throw new IllegalArgumentException("Artifact-only fixture");Files.createDirectories(base);
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
  
  Context cx=Context.enter();registerBuiltinPathWrappers(cx);cx.setClassShutter((name,kind)->kind!=2||f.isAllowed(name));ScriptableObject scope=cx.initStandardObjects();
  ScriptableObject.putProperty(scope,"NativeBridge",new NativeJavaClass(cx,scope,NativeBridge.class),cx);
  ScriptableObject.putProperty(scope,"FileUtilsType",new NativeJavaClass(cx,scope,org.apache.commons.io.FileUtils.class),cx);
  ScriptableObject.putProperty(scope,"UuidType",new NativeJavaClass(cx,scope,java.util.UUID.class),cx);
  cx.evaluateString(scope,"var Java={loadClass:function(name){if(name==='dev.latvian.mods.kubejs.util.UtilsJS')return NativeBridge;if(name==='org.apache.commons.io.FileUtils')return FileUtilsType;if(name==='java.util.UUID')return UuidType;throw new Error('Unexpected class '+name)}};","guarded-platform-binding",1,null);
  cx.evaluateString(scope,Files.readString(Path.of(args[1])),"actual-waypoint-io-adapter",1,null);
  cx.evaluateString(scope,Files.readString(Path.of(args[2])),"actual-waypoint-generation-core",1,null);
  Object value=cx.evaluateString(scope,Files.readString(Path.of(args[3])),"native-filesystem-cases",1,null);
  String result=cx.toString(value);Files.writeString(Path.of(args[4]),result+"\n");System.out.println(result);
 }
}
