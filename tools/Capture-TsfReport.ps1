#requires -Version 5.1
#requires -RunAsAdministrator
<#
.SYNOPSIS
Capture 1-12 exact-build Qualcomm TSF reads with a temporary ETW session.
.DESCRIPTION
Requires an explicitly selected Up interface, administrator privileges, Python,
and the qualified driver. Validates in preview mode before starting ETW.
Uses a 4 MB circular trace for one sample or 32 MB for multiple samples;
spaces requests by at least 250 ms and stops the session in finally. Does not enable
continuous TSF reporting, reset counters, or change the driver debug level.
IncludeCapabilityChecks also reads standard timestamp capabilities and cached
BSS/device-service information. It requires artifacts/native_caps.exe and
artifacts/cached_beacon.exe compiled for this machine; see docs/OPERATIONS.md.
Exit 0 means request/collection completed, not that firmware delivery is proven.
Exit 1 means failure. If interrupted externally, stop the session named in
session.json with: logman stop <SessionName> -ets
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$InterfaceIndex,
    [ValidateRange(1,12)][int]$SampleCount = 1,
    [switch]$IncludeCapabilityChecks
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sessionName = 'WifiTime-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$outputDir = Join-Path $repoRoot ('artifacts/' + $sessionName)
$started = $false
$exitResult = 0
$maxMB = if ($SampleCount -eq 1) { 4 } else { 32 }
$baseline = $null
try {
    $python = (Get-Command python -ErrorAction Stop).Source
    New-Item -ItemType Directory -Path $outputDir -Force -ErrorAction Stop | Out-Null
    [pscustomobject]@{SessionName=$sessionName;StartedUtc=[DateTime]::UtcNow.ToString('o');InterfaceIndex=$InterfaceIndex;MaxMB=$maxMB;SampleCount=$SampleCount} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'session.json') -Encoding UTF8
    $probe = Join-Path $PSScriptRoot 'qualcomm_probe.py'
    & $python $probe --if-index $InterfaceIndex --command tsf_read_value --output (Join-Path $outputDir 'preview.json')
    if ($LASTEXITCODE -ne 0) { throw 'Driver/interface validation failed.' }
    $selected = @(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.ifIndex -eq $InterfaceIndex})
    if ($selected.Count -ne 1) { throw 'Selected adapter is missing or ambiguous.' }
    $baseline = $selected[0]
    if ($baseline.Status -ne 'Up') { throw 'Selected adapter is not Up.' }
    $baseline | Select-Object Name,Status,ifIndex,DriverVersion | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $outputDir 'adapter-before.json') -Encoding UTF8
    if ($IncludeCapabilityChecks) {
        $nativeCaps = Join-Path $repoRoot 'artifacts/native_caps.exe'
        $cachedBeacon = Join-Path $repoRoot 'artifacts/cached_beacon.exe'
        if (-not (Test-Path -LiteralPath $nativeCaps -PathType Leaf) -or
            -not (Test-Path -LiteralPath $cachedBeacon -PathType Leaf)) {
            throw 'Build artifacts/native_caps.exe and artifacts/cached_beacon.exe before requesting capability checks.'
        }
        & $python (Join-Path $PSScriptRoot 'probe_timestamp_caps.py') --if-index $InterfaceIndex |
            Set-Content -LiteralPath (Join-Path $outputDir 'timestamp-capabilities.json') -Encoding UTF8
        if ($LASTEXITCODE -ne 0) { throw 'Timestamp capability probe failed.' }
        & $nativeCaps $InterfaceIndex |
            Set-Content -LiteralPath (Join-Path $outputDir 'native-capabilities.txt') -Encoding UTF8
        if ($LASTEXITCODE -ne 0) { throw 'Native capability probe failed.' }
        & $cachedBeacon $baseline.InterfaceGuid |
            Set-Content -LiteralPath (Join-Path $outputDir 'cached-beacon.json') -Encoding UTF8
        if ($LASTEXITCODE -ne 0) { throw 'Cached BSS/device-service probe failed.' }
    }
    & logman start $sessionName -p '{bb6f5b93-635c-47be-816f-e895e77064a8}' 0x2000000000000010 0xff -o (Join-Path $outputDir 'tsf.etl') -f bincirc -max $maxMB -ets |
        Set-Content -LiteralPath (Join-Path $outputDir 'trace-start.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'ETW could not start; no TSF request sent.' }
    $started = $true
    for ($sample = 1; $sample -le $SampleCount; $sample++) {
        $requestName = if ($SampleCount -eq 1) { 'request.json' } else { 'request-{0:D3}.json' -f $sample }
        & $python $probe --if-index $InterfaceIndex --command tsf_read_value --execute --output (Join-Path $outputDir $requestName)
        if ($LASTEXITCODE -ne 0) { throw ('TSF probe failed; inspect ' + $requestName + ' if present.') }
        $request = Get-Content -LiteralPath (Join-Path $outputDir $requestName) -Raw | ConvertFrom-Json
        if (-not $request.success -or -not $request.handle_closed) { throw 'TSF request or handle cleanup failed.' }
        if ($sample -lt $SampleCount) { Start-Sleep -Milliseconds 250 }
    }
    Start-Sleep -Milliseconds 1500
} catch {
    $exitResult = 1
    if (Test-Path -LiteralPath $outputDir) {
        [pscustomobject]@{ObservedUtc=[DateTime]::UtcNow.ToString('o');Error=$_.Exception.Message} |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'capture-error.json') -Encoding UTF8
    }
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
} finally {
    if ($started) {
        & logman stop $sessionName -ets | Set-Content -LiteralPath (Join-Path $outputDir 'trace-stop.txt') -Encoding UTF8
        if ($LASTEXITCODE -ne 0) {
            $exitResult = 1
            Write-Warning "Stop failed. Run 'logman stop $sessionName -ets' as administrator."
        }
    }
    if (Test-Path -LiteralPath $outputDir) {
        try {
            $final = @(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.ifIndex -eq $InterfaceIndex})
            if ($final.Count -ne 1) { throw 'Final adapter is missing or ambiguous.' }
            $final[0] | Select-Object Name, Status, ifIndex, DriverVersion |
                ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'adapter-after.json') -Encoding UTF8
            if ($null -ne $baseline -and ($final[0].Status -ne 'Up' -or
                $final[0].DriverVersion -ne $baseline.DriverVersion -or
                $final[0].InterfaceGuid -ne $baseline.InterfaceGuid)) {
                throw 'Final adapter state, version, or identity differs from the required baseline.'
            }
        } catch {
            $exitResult = 1
            Write-Warning ('Final adapter read failed: ' + $_.Exception.Message)
        }
    }
}
Write-Output $outputDir
exit $exitResult
