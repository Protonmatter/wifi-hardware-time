import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.util.*;
public class TraceAtlasQuts extends GhidraScript {
 public void run() throws Exception {
  if(currentProgram==null || !"14c4575859dc92200cd22d5c9f4c22a4d626d76f9ed837908c1d010296eae4e0".equalsIgnoreCase(currentProgram.getExecutableSHA256()) || currentProgram.getImageBase().getOffset()!=0x400000L)throw new IllegalArgumentException("Exact QPSTServer 496 image required");
  if(getScriptArgs().length<1 || getScriptArgs().length>2 || (getScriptArgs().length==2 && !"--apply".equals(getScriptArgs()[1])))throw new IllegalArgumentException("Usage: NEW_PRIVATE_OUTPUT_DIRECTORY [--apply]");
  if(getScriptArgs().length==1){println("Would inspect selected QPSTServer 496 references; use --apply to create output files");return;}
  Path out=Paths.get(getScriptArgs()[0]);Files.createDirectory(out);
  DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);
  Set<String> done=new HashSet<>();StringBuilder refs=new StringBuilder();
  try {
   for(String method:new String[]{"CAtlasQutsRequest","AddQpstConnection","RemoveQpstConnection","IsUsingQUTS","IsQpstConnectionExits","Start","Stop"}){
    String s="CAtlasQutsRequest::"+method+" is called.";
    var addr=currentProgram.getMemory().findBytes(currentProgram.getMinAddress(),s.getBytes(java.nio.charset.StandardCharsets.US_ASCII),null,true,monitor);
    if(addr==null){refs.append(s).append("\tmissing-string\n");continue;}
    ReferenceIterator rs=currentProgram.getReferenceManager().getReferencesTo(addr);
    if(!rs.hasNext())refs.append(s).append("\t").append(addr).append("\tno-reference\n");
    while(rs.hasNext()){
     Reference r=rs.next();Function f=getFunctionContaining(r.getFromAddress());
     refs.append(s).append("\t").append(addr).append("\t").append(r.getFromAddress()).append("\t").append(f==null?"no-function":f.getEntryPoint()).append("\n");
     if(f==null || !done.add(f.getEntryPoint().toString()))continue;
     var result=dec.decompileFunction(f,40,monitor);
     String code=result.decompileCompleted()?result.getDecompiledFunction().getC():result.getErrorMessage();
     Files.writeString(out.resolve(f.getEntryPoint()+".c"),code);
    }
   }
   Files.writeString(out.resolve("references.tsv"),refs.toString());
  } finally {dec.dispose();}
 }
}
