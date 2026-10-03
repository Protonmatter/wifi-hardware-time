#requires -Version 5.1
<# Offline only. Export named payloads for strict joining with native raw-QPC metadata.
Output is private local evidence. No arbitrary messages or packet bytes are exported.
Exit 0 complete; 1 failure. Existing output is never replaced. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$EtlPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$stream=$null;$writer=$null
try {
    $providers=@('cdead503-17f5-4a3e-b7ae-df8cc2902eb9','209754d0-15cd-42dd-a9b9-d1b38a606c08')
    $counts=@{};$rows=New-Object 'System.Collections.Generic.List[object]'
    foreach($record in (Get-WinEvent -Path $EtlPath -Oldest -ErrorAction Stop)){
        $provider=([Guid]$record.ProviderId).ToString('D')
        if($provider -notin $providers){continue}
        if(-not $counts.ContainsKey($provider)){$counts[$provider]=0}
        $counts[$provider]++
        $fields=@{}
        if($provider -eq $providers[0]){
            $xml=[xml]$record.ToXml()
            $nodes=$xml.SelectNodes('//*[local-name()="EventData"]/*[local-name()="Data"]')
            foreach($node in $nodes){
                $name=$node.GetAttribute('Name')
                if($fields.ContainsKey($name)){throw 'Duplicate named field.'}
                $fields[$name]=[string]$node.InnerText
            }
        }
        $activity=if($null -eq $record.ActivityId){[Guid]::Empty.ToString('D')}else{([Guid]$record.ActivityId).ToString('D')}
        $rows.Add([pscustomobject]@{provider=$provider;id=[int]$record.Id;version=[int]$record.Version;
            pid=[int]$record.ProcessId;tid=[int]$record.ThreadId;activity_id=$activity;
            provider_sequence=$counts[$provider];data=$fields})
    }
    $json=ConvertTo-Json -InputObject @($rows.ToArray()) -Depth 6
    $stream=[IO.File]::Open([IO.Path]::GetFullPath($OutputPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $writer=New-Object IO.StreamWriter($stream,(New-Object Text.UTF8Encoding($false)))
    $writer.WriteLine($json);$writer.Flush()
    [pscustomobject]@{ExportedEvents=$rows.Count;PrivateOperation=$false} | ConvertTo-Json
} catch {Write-Error $_ -ErrorAction Continue;exit 1}
finally {if($null -ne $writer){$writer.Dispose()}elseif($null -ne $stream){$stream.Dispose()}}
exit 0
