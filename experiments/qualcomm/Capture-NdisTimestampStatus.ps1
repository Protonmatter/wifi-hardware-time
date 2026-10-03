#requires -Version 5.1
#requires -RunAsAdministrator
<#
.SYNOPSIS
Capture bounded NDIS Request diagnostics around two documented capability queries.
.DESCRIPTION
Exact adapter GUID/index/version targeting, pinned existing native executables.
One unique ETW session, Request keyword only, at most 8 MiB. No packet capture,
private IOCTL, timestamp configuration, adapter reset or clock change. Output is
local evidence and can contain identifiers/kernel request pointers: never publish.
Exit 0: acquisition and cleanup completed (not necessarily conclusive); 1: failure.
If externally interrupted, use logman stop <session.json SessionName> -ets.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$InterfaceIndex,
    [Parameter(Mandatory=$true)][Guid]$ExpectedInterfaceGuid,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$session='WifiNdisStatus-'+[Guid]::NewGuid().ToString('N')
$attempted=$false;$cleanup=$false;$exitCode=1;$failure=$null
$output=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $output){throw 'Output directory must not already exist.'}
$null=New-Item -ItemType Directory -Path $output

function Invoke-BoundedChild {
    param([string]$File,[string[]]$Arguments,[string]$Label,[int]$TimeoutMs=10000)
    if(@($Arguments | Where-Object {$_ -match '["\r\n]'}).Count){throw 'Unsupported argument character.'}
    $quoted=@($Arguments | ForEach-Object {'"'+$_+'"'}) -join ' '
    $child=Start-Process -FilePath $File -ArgumentList $quoted -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $output ($Label+'.stdout.txt')) `
        -RedirectStandardError (Join-Path $output ($Label+'.stderr.txt'))
    try {
        $null=$child.Handle # Cache the handle before exit for Windows PowerShell 5.1.
        if(-not $child.WaitForExit($TimeoutMs)){
            try {$child.Kill()} catch {if(-not $child.HasExited){throw}}
            if(-not $child.WaitForExit(2000)){throw ('Child termination unconfirmed: '+$Label)}
            throw ('Child timeout: '+$Label)
        }
        $child.Refresh()
        if($child.ExitCode -ne 0){throw ('Child failed: '+$Label+' exit '+$child.ExitCode)}
        [pscustomobject]@{ProcessId=$child.Id;ExitCode=$child.ExitCode} | ConvertTo-Json |
            Set-Content -LiteralPath (Join-Path $output ($Label+'.process.json')) -Encoding UTF8
    } finally {$child.Dispose()}
}

function Get-ExactAdapter {
    $items=@(Get-NetAdapter -IncludeHidden | Where-Object {$_.ifIndex -eq $InterfaceIndex})
    if($items.Count -ne 1){throw 'Adapter index is not unique.'}
    $item=$items[0]
    if([Guid]$item.InterfaceGuid -ne $ExpectedInterfaceGuid -or $item.Status -ne 'Up' -or
       $item.DriverVersion -ne '1.0.4374.1300' -or $item.InterfaceDescription -notlike '*Qualcomm*7800*'){
        throw 'Adapter identity/state/build differs from approved target.'
    }
    if(-not $item.DriverName.StartsWith('\SystemRoot\',[StringComparison]::OrdinalIgnoreCase)){
        throw 'Unexpected installed driver path form.'
    }
    $driverPath=Join-Path $env:SystemRoot $item.DriverName.Substring(12)
    if((Get-FileHash -LiteralPath $driverPath).Hash -ne 'CA884CE1A22113194F3C467F36ABC39AFB0C137E5A7A8E2697420438B21E4115'){
        throw 'Installed driver hash mismatch.'
    }
    return $item
}

try {
    $before=Get-ExactAdapter
    $probe=Join-Path $repo 'artifacts/native_caps.exe'
    $decoder=Join-Path $repo 'artifacts/decode_tsf_etl.exe'
    if((Get-FileHash -LiteralPath $probe).Hash -ne '53970033DD327B68D465F7569DA020DF0A119061BDE8D8A25B955E5CAD3A2712' -or
       (Get-FileHash -LiteralPath $decoder).Hash -ne 'EEF943146FCAFC7D7CB00285E0C4D02345FE528AF23AE5C6586D6BAB14F43BC7'){
        throw 'Native executable provenance mismatch.'
    }
    $provider=Get-WinEvent -ListProvider Microsoft-Windows-NDIS
    if($provider.Id -ne [Guid]'cdead503-17f5-4a3e-b7ae-df8cc2902eb9'){throw 'Unexpected provider identity.'}
    $event=@($provider.Events | Where-Object {$_.Id -eq 10101 -and $_.Version -eq 0})
    if($event.Count -ne 1 -or $event[0].Template -notmatch 'name="CompleteRequest"' -or
       $event[0].Template -notmatch 'name="Status"' -or $event[0].Template -notmatch 'name="Oid"'){
        throw 'Expected completion event schema unavailable.'
    }
    [pscustomobject]@{SessionName=$session;InterfaceIndex=$InterfaceIndex;InterfaceGuid=$ExpectedInterfaceGuid;
        DriverVersion=$before.DriverVersion;Provider=$provider.Id;Keyword='0x1';Level=5} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'session.json') -Encoding UTF8
    $etl=Join-Path $output 'ndis.etl'
    $logman=Join-Path $env:SystemRoot 'System32/logman.exe'
    $attempted=$true
    Invoke-BoundedChild -File $logman -Arguments @('start',$session,'-p','{cdead503-17f5-4a3e-b7ae-df8cc2902eb9}','0x1','5','-o',$etl,'-f','bin','-max','8','-ets') -Label 'trace-start'
    $start=[DateTime]::UtcNow.ToString('o')
    Invoke-BoundedChild -File $probe -Arguments @([string]$InterfaceIndex) -Label 'capabilities'
    $finish=[DateTime]::UtcNow.ToString('o')
    [pscustomobject]@{StartUtc=$start;FinishUtc=$finish;Queries=2} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $output 'query-window.json') -Encoding UTF8
    $null=Get-ExactAdapter
    $exitCode=0
} catch {$failure=$_.Exception.Message}
finally {
    if($attempted){
        try {Invoke-BoundedChild -File $logman -Arguments @('stop',$session,'-ets') -Label 'trace-stop';$cleanup=$true}
        catch {$exitCode=1;$failure='Trace cleanup failed; use session.json to stop the exact session.'}
    }
}
if($exitCode -eq 0){
    try {
        Invoke-BoundedChild -File $decoder -Arguments @($etl) -Label 'trace-health'
        $health=@(Get-Content -LiteralPath (Join-Path $output 'trace-health.stdout.txt') | ForEach-Object {$_ | ConvertFrom-Json})
        if($health.Count -ne 2 -or $health[0].kind -ne 'header' -or $health[-1].kind -ne 'summary' -or
           $health[0].events_lost -ne 0 -or $health[0].buffers_lost -ne 0 -or
           $health[-1].process_status -ne 0 -or $health[-1].close_status -ne 0){throw 'Trace health/loss check failed.'}
        $null=Get-ExactAdapter
    } catch {$exitCode=1;$failure=$_.Exception.Message}
}
[pscustomobject]@{AcquisitionCompleted=($exitCode -eq 0);TraceCleanupSucceeded=$cleanup;
    Error=$failure;PrivateRequestSent=$false;RawStatusConclusion='Requires offline event correlation'} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'result.json') -Encoding UTF8
exit $exitCode
