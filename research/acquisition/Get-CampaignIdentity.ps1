#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$InterfaceIndex)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
try {
    $selected=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.ifIndex -eq $InterfaceIndex})
    if($selected.Count -ne 1){throw 'Missing or ambiguous interface.'}
    $driver=Get-CimInstance Win32_SystemDriver -Filter "Name='qcwlan'" -ErrorAction Stop
    $adapter=$selected[0]
    [pscustomobject]@{Name=$adapter.Name;Status=$adapter.Status.ToString();ifIndex=$adapter.ifIndex;
        DriverVersion=$adapter.DriverVersion;DriverFileName=$adapter.DriverFileName;
        InterfaceGuid=$adapter.InterfaceGuid.ToString();PnPDeviceID=$adapter.PnPDeviceID;
        DriverPath=$driver.PathName;ServiceState=$driver.State} | ConvertTo-Json
    exit 0
} catch {Write-Error $_.Exception.Message;exit 1}
