#requires -Version 5.1
<#
.SYNOPSIS
Extract numeric pre-aggregation FTM delta logs from a saved qualified capture.
.DESCRIPTION
Offline only; no elevation, network, private device or register operation.
Output is local evidence, not automatically approved for publication.
Exit 0: completed; exit 1: rejected evidence or I/O. Existing output is never replaced.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RunDirectory,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$stream=$null;$writer=$null
try {
    . (Join-Path $PSScriptRoot 'FtmDeltaLog.ps1')
    $root=(Resolve-Path -LiteralPath $RunDirectory -ErrorAction Stop).Path
    $trace=Join-Path $root 'ftm.etl'
    $previewPath=Join-Path $root 'driver-preview.json'
    $healthPath=Join-Path $root 'trace-health.jsonl'
    $preview=Get-Content -LiteralPath $previewPath -Raw | ConvertFrom-Json
    $expected='ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'
    if($preview.driver_sha256 -cne $expected){throw 'Saved driver preview is not the qualified build.'}
    $health=@(Get-Content -LiteralPath $healthPath | ForEach-Object {$_ | ConvertFrom-Json})
    if($health.Count -lt 2 -or $health[0].kind -ne 'header' -or $health[-1].kind -ne 'summary'){
        throw 'Missing trace-health header/summary.'
    }
    if($health[0].events_lost -ne 0 -or $health[0].buffers_lost -ne 0 -or
       $health[-1].process_status -ne 0 -or $health[-1].close_status -ne 0){throw 'Trace loss or failed decode.'}
    $provider=[Guid]'bb6f5b93-635c-47be-816f-e895e77064a8'
    $events=New-Object 'System.Collections.Generic.List[object]'
    $providerCount=0
    foreach($record in (Get-WinEvent -Path $trace -Oldest -ErrorAction Stop)){
        if($record.ProviderId -ne $provider){continue}
        $providerCount++
        if($record.Id -notin @(1,19)){continue}
        $xml=[xml]$record.ToXml()
        $text=[string]$xml.Event.EventData.Data.InnerText
        $parsed=ConvertFrom-FtmDeltaLogLine -Text $text
        if($null -ne $parsed){
            $events.Add([pscustomobject]@{field=$parsed.field;value=$parsed.value;ordinal=$providerCount;
                thread_id=[long]$xml.Event.System.Execution.ThreadID})
        }
    }
    if($providerCount -ne $health[-1].wlan_events){throw 'Independent provider-event count differs from native decode.'}
    if($events.Count -eq 0){throw 'No recognized delta evidence; do not emit empty success.'}
    $output=[pscustomobject]@{schema='qcom-ftm-deltas/v1';driver_sha256=$expected;
        etl_sha256=(Get-FileHash -LiteralPath $trace -Algorithm SHA256).Hash.ToLowerInvariant();
        preview_sha256=(Get-FileHash -LiteralPath $previewPath -Algorithm SHA256).Hash.ToLowerInvariant();
        trace_health_sha256=(Get-FileHash -LiteralPath $healthPath -Algorithm SHA256).Hash.ToLowerInvariant();
        trace_events_lost=0;trace_buffers_lost=0;provider_events=$providerCount;events=@($events.ToArray())}
    $json=$output | ConvertTo-Json -Depth 6
    $stream=[IO.File]::Open([IO.Path]::GetFullPath($OutputPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $writer=New-Object IO.StreamWriter($stream,(New-Object Text.UTF8Encoding($false)))
    $writer.WriteLine($json);$writer.Flush()
    [pscustomobject]@{NumericEvents=$events.Count;ProviderEvents=$providerCount;PrivateRequestSent=$false} | ConvertTo-Json
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    exit 1
} finally {
    if($null -ne $writer){$writer.Dispose()}elseif($null -ne $stream){$stream.Dispose()}
}
exit 0
