#requires -Version 5.1
#requires -RunAsAdministrator
<#
.SYNOPSIS
Capture one exact-build Qualcomm TSF read with a temporary ETW session.
.DESCRIPTION
Requires an explicitly selected Up interface, administrator privileges, Python,
and the qualified driver. Validates in preview mode before starting ETW.
Uses a 4 MB circular trace; stops the session in finally. Does not enable
continuous TSF reporting, reset counters, or change the driver debug level.
Exit 0 means request/collection completed, not that firmware delivery is proven.
Exit 1 means failure. If interrupted externally, stop the session named in
session.json with: logman stop <SessionName> -ets
#>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$InterfaceIndex)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sessionName = 'WifiTime-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$outputDir = Join-Path $repoRoot ('artifacts/' + $sessionName)
$started = $false
$exitResult = 0
try {
    $python = (Get-Command python -ErrorAction Stop).Source
    New-Item -ItemType Directory -Path $outputDir -Force -ErrorAction Stop | Out-Null
    [pscustomobject]@{SessionName=$sessionName;StartedUtc=[DateTime]::UtcNow.ToString('o');InterfaceIndex=$InterfaceIndex;MaxMB=4} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'session.json') -Encoding UTF8
    $probe = Join-Path $PSScriptRoot 'qualcomm_probe.py'
    & $python $probe --if-index $InterfaceIndex --command tsf_read_value --output (Join-Path $outputDir 'preview.json')
    if ($LASTEXITCODE -ne 0) { throw 'Driver/interface validation failed.' }
    & logman start $sessionName -p '{bb6f5b93-635c-47be-816f-e895e77064a8}' 0x2000000000000010 0xff -o (Join-Path $outputDir 'tsf.etl') -f bincirc -max 4 -ets |
        Set-Content -LiteralPath (Join-Path $outputDir 'trace-start.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'ETW could not start; no TSF request sent.' }
    $started = $true
    & $python $probe --if-index $InterfaceIndex --command tsf_read_value --execute --output (Join-Path $outputDir 'request.json')
    if ($LASTEXITCODE -ne 0) { throw 'TSF probe failed; inspect request.json if present.' }
    Start-Sleep -Milliseconds 1500
} catch {
    $exitResult = 1
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
            Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.ifIndex -eq $InterfaceIndex} |
                Select-Object Name, Status, ifIndex, DriverVersion |
                ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'adapter-after.json') -Encoding UTF8
        } catch {
            $exitResult = 1
            Write-Warning ('Final adapter read failed: ' + $_.Exception.Message)
        }
    }
}
Write-Output $outputDir
exit $exitResult
