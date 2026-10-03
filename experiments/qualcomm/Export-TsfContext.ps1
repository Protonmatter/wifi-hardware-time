#requires -Version 5.1
<# Offline saved-ETL context extraction. Never opens a device or starts a trace.
Output contains PRIVATE driver messages/identifiers; keep it outside publication.
Exit 0 extraction complete; 1 rejected input/I/O. Output creation is exclusive. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$EtlPath,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][int[]]$ReportOrdinals,
    [Parameter(Mandatory=$true)][string]$OutputPath,
    [ValidateRange(0,20)][int]$ContextMilliseconds=2
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$stream=$null;$writer=$null
try {
    if((Get-Item -LiteralPath $EtlPath).Length -gt 32MB){throw 'ETL exceeds reviewed 32 MiB bound.'}
    if(@($ReportOrdinals | Where-Object {$_ -lt 1 -or $_ -gt 1000}).Count -or @($ReportOrdinals | Select-Object -Unique).Count -ne $ReportOrdinals.Count){throw 'Invalid or duplicate report ordinal.'}
    $rows=New-Object 'System.Collections.Generic.List[object]'
    $targets=New-Object 'System.Collections.Generic.List[object]'
    $ordinal=0;$count=0
    foreach($record in (Get-WinEvent -Path $EtlPath -Oldest -ErrorAction Stop)){
        $count++;if($count -gt 100000){throw 'Event count exceeds extraction bound.'}
        if($record.ProviderId -ne [Guid]'bb6f5b93-635c-47be-816f-e895e77064a8'){continue}
        $xml=[xml]$record.ToXml();$message=[string]$xml.Event.EventData.Data.InnerText
        if($message.Length -gt 8192){throw 'Unexpected message width.'}
        $time=$record.TimeCreated.ToUniversalTime()
        $row=[pscustomobject]@{ordinal=$count;event_id=$record.Id;thread_id=$record.ThreadId;utc=$time.ToString('o');message=$message}
        $rows.Add($row)
        if($message -cmatch '^OL: receive WMI_VDEV_TSF_REPORT_EVENTID'){
            $ordinal++
            if($ordinal -in $ReportOrdinals){$targets.Add([pscustomobject]@{report_ordinal=$ordinal;event_ordinal=$count;utc=$time.ToString('o')})}
        }
    }
    if($targets.Count -ne $ReportOrdinals.Count){throw 'Requested report ordinal not found.'}
    $selected=New-Object 'System.Collections.Generic.List[object]'
    foreach($row in $rows){
        $time=[DateTimeOffset]::Parse($row.utc)
        foreach($target in $targets){
            if([Math]::Abs(($time-[DateTimeOffset]::Parse($target.utc)).TotalMilliseconds) -le $ContextMilliseconds){$selected.Add($row);break}
        }
    }
    $result=[pscustomobject]@{schema='tsf-context/v1';etl_sha256=(Get-FileHash -LiteralPath $EtlPath).Hash.ToLowerInvariant();report_count=$ordinal;context_ms=$ContextMilliseconds;targets=@($targets.ToArray());events=@($selected.ToArray());private_request_sent=$false}
    $json=ConvertTo-Json -InputObject $result -Depth 6
    $stream=[IO.File]::Open([IO.Path]::GetFullPath($OutputPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $writer=New-Object IO.StreamWriter($stream,(New-Object Text.UTF8Encoding($false)))
    $writer.WriteLine($json);$writer.Flush()
    [pscustomobject]@{TotalReports=$ordinal;SelectedReports=$targets.Count;ContextEvents=$selected.Count;OutputIsPrivate=$true} | ConvertTo-Json
} catch {Write-Error $_ -ErrorAction Continue;exit 1}
finally {if($null -ne $writer){$writer.Dispose()}elseif($null -ne $stream){$stream.Dispose()}}
exit 0
