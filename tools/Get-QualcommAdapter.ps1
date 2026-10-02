#requires -Version 5.1
<#
.SYNOPSIS
Read the selected adapter and active Qualcomm driver location.
.DESCRIPTION
Discovery only. No elevation, device open, registry write, or driver change.
The JSON includes the runtime MAC selector for the local probe; do not publish it.
Exit 0: discovery succeeded. Exit 1: invalid/missing/ambiguous target or read failure.
#>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$InterfaceIndex)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
try {
    $selected = @(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.ifIndex -eq $InterfaceIndex})
    if ($selected.Count -ne 1) { throw 'Interface index is missing or ambiguous.' }
    $adapter = $selected[0]
    if ($adapter.DriverFileName -ine 'qcwlanhmt8380.sys') { throw 'Selected interface does not use the qualified Qualcomm driver.' }
    $service = Get-CimInstance Win32_SystemDriver -Filter "Name='qcwlan'" -ErrorAction Stop
    if (-not $service -or -not (Test-Path -LiteralPath $service.PathName -PathType Leaf)) { throw 'Active driver file is unavailable.' }
    [pscustomobject]@{
        ifIndex=$adapter.ifIndex; Status=$adapter.Status.ToString()
        DriverFileName=$adapter.DriverFileName; DriverVersion=$adapter.DriverVersion
        DriverPath=$service.PathName; ServiceState=$service.State
        MacAddress=$adapter.MacAddress
    } | ConvertTo-Json
    exit 0
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    exit 1
}
