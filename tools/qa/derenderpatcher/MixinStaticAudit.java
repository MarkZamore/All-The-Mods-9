import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

public class MixinStaticAudit {
    static final Map<String,ClassNode> cache=new HashMap<>();
    static final Map<String,String> providers=new HashMap<>();
    static List<Path> jars;
    static ClassNode cls(String name) throws Exception {
        if(cache.containsKey(name))return cache.get(name);
        for(Path jar:jars)try(ZipFile z=new ZipFile(jar.toFile())){
            ZipEntry e=z.getEntry(name+".class");if(e==null)continue;
            ClassNode n=new ClassNode();new ClassReader(z.getInputStream(e)).accept(n,ClassReader.SKIP_FRAMES);
            cache.put(name,n);providers.put(name,jar.getFileName().toString());return n;
        }
        return null;
    }
    static Map<String,Object> vals(AnnotationNode n){Map<String,Object> r=new LinkedHashMap<>();if(n.values!=null)for(int i=0;i<n.values.size();i+=2)r.put((String)n.values.get(i),n.values.get(i+1));return r;}
    static List<AnnotationNode> anns(List<AnnotationNode>a,List<AnnotationNode>b){List<AnnotationNode> r=new ArrayList<>();if(a!=null)r.addAll(a);if(b!=null)r.addAll(b);return r;}
    static List<String> strings(Object x){if(x==null)return List.of();if(x instanceof List<?> l)return l.stream().map(v->v instanceof Type t?t.getInternalName():v.toString()).toList();return List.of(x.toString());}
    static String nm(String selector){int sem=selector.indexOf(';');if(selector.startsWith("L")&&sem>=0)selector=selector.substring(sem+1);int p=selector.indexOf('(');return p<0?selector:selector.substring(0,p);}
    static String desc(String selector){int p=selector.indexOf('(');return p<0?null:selector.substring(p);}
    static List<MethodNode> selected(ClassNode n,List<String> selectors){List<MethodNode> r=new ArrayList<>();for(MethodNode m:n.methods)for(String s:selectors)if(m.name.equals(nm(s))&&(desc(s)==null||m.desc.equals(desc(s)))){r.add(m);break;}return r;}
    static FieldNode field(ClassNode n,String name,String desc,Set<String> seen)throws Exception{if(n==null||!seen.add(n.name))return null;for(FieldNode f:n.fields)if(f.name.equals(name)&&(desc==null||f.desc.equals(desc)))return f;return n.superName==null?null:field(cls(n.superName),name,desc,seen);}
    static MethodNode method(ClassNode n,String name,String desc,Set<String>seen)throws Exception{if(n==null||!seen.add(n.name))return null;for(MethodNode m:n.methods)if(m.name.equals(name)&&m.desc.equals(desc))return m;for(String p:n.interfaces){MethodNode m=method(cls(p),name,desc,seen);if(m!=null)return m;}return n.superName==null?null:method(cls(n.superName),name,desc,seen);}
    static int matches(List<MethodNode> methods,AnnotationNode at){Map<String,Object> v=vals(at);String kind=(String)v.get("value"),target=(String)v.get("target");if(target==null)return -1;target=target.replace(" ","");int semi=target.indexOf(';');if(!target.startsWith("L")||semi<0)return -2;String owner=target.substring(1,semi),member=target.substring(semi+1);int count=0;
        for(MethodNode m:methods)for(AbstractInsnNode i:m.instructions){if(kind.equals("INVOKE")&&i instanceof MethodInsnNode z&&z.owner.equals(owner)&&(z.name+z.desc).equals(member))count++;if(kind.equals("FIELD")&&i instanceof FieldInsnNode z&&z.owner.equals(owner)&&(z.name+":"+z.desc).equals(member))count++;}return count;}
    static Object norm(Object x){if(x instanceof Type t)return t.getDescriptor();if(x instanceof AnnotationNode a){Map<String,Object> r=new LinkedHashMap<>();r.put("annotationType",a.desc);vals(a).forEach((k,v)->r.put(k,norm(v)));return r;}if(x instanceof List<?>l)return l.stream().map(MixinStaticAudit::norm).toList();if(x instanceof String[]a)return Arrays.asList(a);return x;}
    static String json(Object x){if(x==null)return "null";if(x instanceof Boolean||x instanceof Number)return x.toString();if(x instanceof Map<?,?>m){List<String>s=new ArrayList<>();m.forEach((k,v)->s.add(json(k.toString())+":"+json(v)));return "{"+String.join(",",s)+"}";}if(x instanceof Iterable<?>l){List<String>s=new ArrayList<>();l.forEach(v->s.add(json(v)));return "["+String.join(",",s)+"]";}return "\""+x.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";}
    public static void main(String[]args)throws Exception{
        Path patch=Path.of(args[0]);jars=Files.readAllLines(Path.of(args[1])).stream().filter(s->!s.isBlank()).map(Path::of).toList();List<Object> rows=new ArrayList<>();
        try(ZipFile z=new ZipFile(patch.toFile())){for(ZipEntry e:Collections.list(z.entries())){if(!e.getName().startsWith("com/derenderpatcher/mixins/")||!e.getName().endsWith(".class"))continue;ClassNode m=new ClassNode();new ClassReader(z.getInputStream(e)).accept(m,ClassReader.SKIP_FRAMES);AnnotationNode mix=anns(m.visibleAnnotations,m.invisibleAnnotations).stream().filter(a->a.desc.endsWith("/Mixin;")).findFirst().orElse(null);if(mix==null)continue;
            Map<String,Object> mv=vals(mix);List<String> targets=new ArrayList<>(strings(mv.get("value")));targets.addAll(strings(mv.get("targets")));for(String t:targets){ClassNode n=cls(t);Map<String,Object> row=new LinkedHashMap<>();row.put("mixin",m.name);row.put("target",t);row.put("targetFound",n!=null);row.put("targetProvider",providers.get(t));List<Object> members=new ArrayList<>();row.put("members",members);rows.add(row);if(n==null)continue;
                for(FieldNode f:m.fields)for(AnnotationNode a:anns(f.visibleAnnotations,f.invisibleAnnotations))if(a.desc.endsWith("/Shadow;"))members.add(Map.of("kind","shadowField","name",f.name,"descriptor",f.desc,"found",field(n,f.name,f.desc,new HashSet<>())!=null));
                for(MethodNode h:m.methods)for(AnnotationNode a:anns(h.visibleAnnotations,h.invisibleAnnotations)){
                    if(a.desc.endsWith("/Shadow;"))members.add(Map.of("kind","shadowMethod","name",h.name,"descriptor",h.desc,"found",method(n,h.name,h.desc,new HashSet<>())!=null));
                    if(a.desc.endsWith("/Accessor;")){String f=(String)vals(a).get("value");String d=Type.getReturnType(h.desc).getDescriptor();members.add(Map.of("kind","accessor","handler",h.name,"field",f,"descriptor",d,"found",field(n,f,d,new HashSet<>())!=null));}
                    if(a.desc.endsWith("/Invoker;")){String name=(String)vals(a).get("value");members.add(Map.of("kind","invoker","handler",h.name,"method",name,"descriptor",h.desc,"found",method(n,name,h.desc,new HashSet<>())!=null));}
                    if(!a.desc.startsWith("Lorg/spongepowered/asm/mixin/injection/"))continue;
                    Map<String,Object> av=vals(a);List<String> selectors=strings(av.get("method"));if(selectors.isEmpty())continue;List<MethodNode> selected=selected(n,selectors);Map<String,Object> ir=new LinkedHashMap<>();members.add(ir);ir.put("kind","injection");ir.put("handler",h.name);ir.put("annotation",a.desc);ir.put("selectors",selectors);ir.put("selectedMethods",selected.stream().map(q->q.name+q.desc).toList());ir.put("require",av.getOrDefault("require",1));ir.put("methodFound",!selected.isEmpty());List<Object> sites=new ArrayList<>();ir.put("sites",sites);Object ats=av.get("at");List<?> atlist=ats instanceof List<?> l?l:ats==null?List.of():List.of(ats);for(Object at:atlist)if(at instanceof AnnotationNode an){Map<String,Object> st=new LinkedHashMap<>();st.put("at",norm(an));st.put("matchingUntransformedInstructions",matches(selected,an));sites.add(st);}
                }
            }
        }}
        Map<String,Object> refs=new TreeMap<>();
        try(ZipFile z=new ZipFile(patch.toFile())){for(ZipEntry e:Collections.list(z.entries())){if(!e.getName().endsWith(".class"))continue;ClassNode n=new ClassNode();new ClassReader(z.getInputStream(e)).accept(n,ClassReader.SKIP_FRAMES);for(MethodNode m:n.methods)for(AbstractInsnNode in:m.instructions){String owner,name,desc,kind;if(in instanceof MethodInsnNode x){owner=x.owner;name=x.name;desc=x.desc;kind="method";}else if(in instanceof FieldInsnNode x){owner=x.owner;name=x.name;desc=x.desc;kind="field";}else continue;if(!(owner.startsWith("com/brandon3055/")||owner.startsWith("codechicken/")||owner.startsWith("net/irisshaders/")||owner.startsWith("me/jellysquid/")))continue;boolean found=kind.equals("method")?method(cls(owner),name,desc,new HashSet<>())!=null:field(cls(owner),name,desc,new HashSet<>())!=null;refs.put(owner+":"+kind+":"+name+desc,Map.of("owner",owner,"kind",kind,"name",name,"descriptor",desc,"found",found));}}}
        Files.writeString(Path.of(args[2]),json(Map.of("scope","Static exact class/member/caller-site inspection only; no Mixin application/gameplay/visual PASS","mixins",rows,"externalModMemberReferences",refs.values()))+"\n");System.out.println("Audited "+rows.size()+" mixin targets and "+refs.size()+" direct external-mod member references; report written");
    }
}
