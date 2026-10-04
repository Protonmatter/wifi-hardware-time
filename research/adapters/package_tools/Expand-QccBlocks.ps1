# File-only investigation helper. Never loads the inspected assembly or deserializes its objects.
# The embedded package decoding parameter stays in memory and is not emitted.
#requires -Version 7.4
[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$OutputDirectory,[switch]$Apply)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$resolved=(Resolve-Path -LiteralPath $Path).ProviderPath
if((Get-Item -LiteralPath $resolved).Length -gt 536870912){throw 'Package exceeds 512 MiB bound'}
if(-not $Apply -or -not $PSCmdlet.ShouldProcess($OutputDirectory,'Decode package into new private files')){
    [ordered]@{status='WouldDecode';input_sha256=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()} | ConvertTo-Json
    return
}
$bytes=[IO.File]::ReadAllBytes($resolved)
$stream=[IO.MemoryStream]::new($bytes,$false)
$pe=[System.Reflection.PortableExecutable.PEReader]::new($stream)
$md=[System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader($pe)
$key=$null
foreach($th in $md.TypeDefinitions){
    $t=$md.GetTypeDefinition($th)
    if($md.GetString($t.Name) -ne 'QCCParameters'){continue}
    foreach($mh in $t.GetMethods()){
        $m=$md.GetMethodDefinition($mh)
        if($md.GetString($m.Name) -ne '.cctor'){continue}
        $il=[System.Reflection.Metadata.PEReaderExtensions]::GetMethodBody($pe,$m.RelativeVirtualAddress).GetILBytes()
        for($i=0;$i+10 -le $il.Length;$i++){
            if($il[$i] -ne 0x72 -or $il[$i+5] -ne 0x80){continue}
            $ft=[BitConverter]::ToInt32($il,$i+6)
            if(($ft -band 0xFF000000) -ne 0x04000000){continue}
            $fh=[System.Reflection.Metadata.Ecma335.MetadataTokens]::FieldDefinitionHandle($ft -band 0xFFFFFF)
            if($md.GetString($md.GetFieldDefinition($fh).Name) -ne 'defaultyek'){continue}
            $st=[BitConverter]::ToInt32($il,$i+1)
            if(($st -band 0xFF000000) -ne 0x70000000){throw 'Unexpected string token'}
            $key=[Text.Encoding]::UTF8.GetBytes($md.GetUserString([System.Reflection.Metadata.Ecma335.MetadataTokens]::UserStringHandle($st -band 0xFFFFFF)))
        }
    }
}
if($null -eq $key -or $key.Length -ne 32){throw 'Expected package decoding parameter absent'}
$start=($pe.PEHeaders.SectionHeaders | ForEach-Object {$_.PointerToRawData+$_.SizeOfRawData} | Measure-Object -Maximum).Maximum
$pe.Dispose();$stream.Dispose()
function U32([int]$o){[BitConverter]::ToUInt32($bytes,$o)}
function I64([int]$o){[BitConverter]::ToInt64($bytes,$o)}
if((U32 $start) -ne 0x2b434351 -or [BitConverter]::ToUInt16($bytes,$start+6) -ne 32){throw 'Invalid QCC header'}
if($bytes[$start+10] -ne 1 -or $bytes[$start+12] -ne 2){throw 'Unsupported package encoding'}
$count=U32 ($start+16)
if($count -lt 1 -or $count -gt 10000){throw 'Invalid block count'}
$index=I64 ($start+20)
$cipher=$start+32
if([BitConverter]::ToUInt16($bytes,$start+8) -ne 72 -or (U32 $cipher) -ne 0x2b434351 -or $bytes[$cipher+4] -ne 0 -or $bytes[$cipher+5] -ne 16 -or $bytes[$cipher+6] -ne 1){throw 'Unsupported cipher descriptor'}
$iv=[byte[]]$bytes[($cipher+40)..($cipher+55)]
$aes=[Security.Cryptography.Aes]::Create();$aes.Mode='CBC';$aes.Padding='PKCS7';$aes.Key=$key;$aes.IV=$iv
$out=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $out){throw 'Output directory already exists'}
[IO.Directory]::CreateDirectory($out) | Out-Null
$rows=[Collections.Generic.List[object]]::new();$offset=$cipher+72;$totalExpanded=0L
try {
for($b=0;$b -lt $count;$b++){
    if($offset+32 -gt $bytes.Length -or (U32 $offset) -ne 0x2b434351){throw "Invalid block at $offset"}
    $id=U32 ($offset+4);$kind=$bytes[$offset+8];$payload=I64 ($offset+16);$size=I64 ($offset+24)
    if($payload -lt 0 -or $size -lt 0 -or $size -gt 536870912 -or $offset+32+$payload -gt $bytes.Length){throw 'Invalid block extent'}
    $totalExpanded+=$size
    if($totalExpanded -gt 1073741824){throw 'Expanded package exceeds 1 GiB bound'}
    $dec=$aes.CreateDecryptor()
    try {$plain=$dec.TransformFinalBlock($bytes,$offset+32,$payload)}finally{$dec.Dispose()}
    $compressed=[IO.MemoryStream]::new($plain,$false)
    $gz=[IO.Compression.GZipStream]::new($compressed,[IO.Compression.CompressionMode]::Decompress)
    $file=Join-Path $out ('block-{0:d4}-type-{1}.bin' -f $id,$kind)
    $target=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try{
        $buffer=[byte[]]::new(65536);$written=0L
        while(($n=$gz.Read($buffer,0,$buffer.Length)) -gt 0){$written+=$n;if($written -gt $size){throw 'Expanded size exceeded'};$target.Write($buffer,0,$n)}
        if($written -ne $size){throw 'Expanded size mismatch'}
    }finally{$target.Dispose();$gz.Dispose();$compressed.Dispose()}
    $rows.Add([ordered]@{id=$id;type=$kind;file=[IO.Path]::GetFileName($file);offset=$offset;payload_bytes=$payload;bytes=$size;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()})
    $offset+=32+$payload
}
}finally{$aes.Dispose();[Array]::Clear($key,0,$key.Length)}
if($rows[-1].type -ne 255 -or $rows[-1].offset-$start -ne $index){throw 'Missing or misplaced index'}
$indexBytes=[IO.File]::ReadAllBytes((Join-Path $out $rows[-1].file))
if($indexBytes.Length -ne $rows.Count*8 -or [BitConverter]::ToUInt64($indexBytes,0) -ne 0x2b4343512b434351){throw 'Invalid index length/magic'}
for($i=0;$i -lt $rows.Count-1;$i++){
    if([BitConverter]::ToInt64($indexBytes,($i+1)*8) -ne $rows[$i].offset-$start){throw 'Index does not match block offsets'}
}
[ordered]@{schema='wht/qcc-static-extraction-v1';input_sha256=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant();overlay_offset=$start;index_offset=$index;declared_block_count=$count;end_offset=$offset;blocks=$rows;scope='Static byte decoding only; no vendor assembly loading or object deserialization'} | ConvertTo-Json -Depth 7
