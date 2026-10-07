#requires -Version 7.4
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[string]$Pattern='Quts|AtlasApplication|AtlasPort')
$ErrorActionPreference='Stop'
if([IO.Path]::GetExtension($Path) -ne '.tlb'){throw 'Supply an extracted .tlb, not an executable or COM server'}
if((Get-Item -LiteralPath $Path).Length -gt 8388608){throw 'Type library exceeds 8 MiB bound'}
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class TypeLibraryData {
 [DllImport("oleaut32.dll", CharSet=CharSet.Unicode, PreserveSig=false)]
 private static extern void LoadTypeLibEx(string file, int regkind, out ITypeLib lib);
 public static object[] Read(string file, string pattern) {
  ITypeLib lib; LoadTypeLibEx(file, 2, out lib); // REGKIND_NONE; extracted .tlb only.
  var rows=new List<object>();
  try { for(int i=0;i<lib.GetTypeInfoCount();i++) {
   ITypeInfo info;lib.GetTypeInfo(i,out info);IntPtr attr=IntPtr.Zero;
   try { string name,doc,help;int ctx;info.GetDocumentation(-1,out name,out doc,out ctx,out help);
    if(!System.Text.RegularExpressions.Regex.IsMatch(name,pattern,System.Text.RegularExpressions.RegexOptions.IgnoreCase))continue;
    info.GetTypeAttr(out attr);var t=Marshal.PtrToStructure<TYPEATTR>(attr);var methods=new List<object>();
    for(int n=0;n<t.cFuncs;n++) { IntPtr fp;info.GetFuncDesc(n,out fp);
     try{var f=Marshal.PtrToStructure<FUNCDESC>(fp);var names=new string[64];int got;info.GetNames(f.memid,names,names.Length,out got);
      var args=new List<object>();for(int j=0;j<f.cParams;j++){var el=Marshal.PtrToStructure<ELEMDESC>(IntPtr.Add(f.lprgelemdescParam,j*Marshal.SizeOf<ELEMDESC>()));args.Add(new {name=j+1<got?names[j+1]:null,type=el.tdesc.vt,flags=el.desc.paramdesc.wParamFlags.ToString()});}
      methods.Add(new{name=got>0?names[0]:null,id=f.memid,offset=f.oVft,call=f.invkind.ToString(),parameters=args});
     }finally{info.ReleaseFuncDesc(fp);}
    }
    rows.Add(new{name,guid=t.guid,kind=t.typekind.ToString(),methods});
   }finally{if(attr!=IntPtr.Zero)info.ReleaseTypeAttr(attr);Marshal.ReleaseComObject(info);}
  }}finally{Marshal.ReleaseComObject(lib);}return rows.ToArray();
 }
}
'@
[TypeLibraryData]::Read((Resolve-Path -LiteralPath $Path).ProviderPath,$Pattern) | ConvertTo-Json -Depth 10
