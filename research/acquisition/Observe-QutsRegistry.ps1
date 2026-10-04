#requires -Version 5.1
<#
.SYNOPSIS
Preview or capture bounded Windows registry-query events from existing QUTS processes.
.DESCRIPTION
Preview is read-only. -Execute requires an elevated local console and a NEW private
output directory. Observes only OS ETW; sends no QUTS RPC or firmware command.
Uses a unique WPR instance, a 32 MiB memory collector and a bounded observation.
Kernel registry events are collected without a provider-process scope filter;
analysis must retain only the exact QUTS PIDs and the declared control PID.
Raw ETL, process identities and registry paths are private. Exit 0 capture/preview
completed, 1 blocked/failed; completion alone is not branch or timing qualification.
.EXAMPLE
./Observe-QutsRegistry.ps1
.EXAMPLE
./Observe-QutsRegistry.ps1 -Execute -OutputDirectory C:/PrivateEvidence/quts-registry-01
.NOTES
Cleanup stops/cancels only this script's unique WPR instance. No service/device or
registry configuration is changed. Interrupted host execution may require:
wpr -cancel -instancename <instance recorded in result.json>
Windows 11 and the pinned QUTS/driver files are prerequisites. No vendor code is loaded.
#>
[CmdletBinding()]
param([switch]$Execute,[string]$OutputDirectory,[ValidateRange(5,30)][int]$Seconds=20)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$profile=Join-Path $PSScriptRoot 'quts-registry.wprp'
$wpr=Join-Path $env:windir 'System32\wpr.exe'
if(-not $Execute){
    & $wpr -profiles $profile
    if($LASTEXITCODE -ne 0){exit 1}
    [pscustomobject]@{mode='preview';seconds=$Seconds;process_filter='post-capture exact PIDs';memory_buffers_mib=32;vendor_requests=0}
    exit 0
}
$elevated=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(-not $elevated){throw 'Execution requires an elevated local console; preview does not.'}
if([string]::IsNullOrWhiteSpace($OutputDirectory) -or (Test-Path -LiteralPath $OutputDirectory)){throw 'Provide a NEW private OutputDirectory.'}
$null=New-Item -ItemType Directory -Path $OutputDirectory
$outputRoot=(Resolve-Path -LiteralPath $OutputDirectory).ProviderPath
$instance='wht-quts-registry-'+[Guid]::NewGuid().ToString('N')
$result=[ordered]@{schema='wht/quts-registry-observation-v1';instance=$instance;started_utc=[DateTimeOffset]::UtcNow.ToString('o');seconds=$Seconds;memory_buffers_mib=32;disposition='blocked';trace_started=$false;trace_stopped=$false;cleanup='not-needed';error=$null}
$attempted=$false
$exitCode=1
$commandCount=0
$controls=New-Object 'System.Collections.Generic.List[object]'

function Invoke-ReadControls([string]$Phase,[string]$DriverKey){
    $controlKey=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(('SYSTEM\CurrentControlSet\Control\Class\'+$DriverKey),$false)
    if($null -eq $controlKey){throw 'Positive-control driver key unavailable'}
    try {
        for($i=0;$i -lt 5;$i++){
            foreach($name in @('NetCfgInstanceId','QCDeviceControlFile')){
                $thread=[WhtRegistryControlThread]::GetCurrentThreadId()
                $beforeQpc=[Diagnostics.Stopwatch]::GetTimestamp()
                $value=$controlKey.GetValue($name,$null)
                $afterQpc=[Diagnostics.Stopwatch]::GetTimestamp()
                $controls.Add([pscustomobject]@{phase=$Phase;pid=$PID;tid=$thread;name=$name;before_qpc=[string]$beforeQpc;after_qpc=[string]$afterQpc;value_present=($null -ne $value)})
            }
        }
    } finally {$controlKey.Dispose()}
    $controls | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $outputRoot 'positive-controls.json') -Encoding UTF8
}

function Invoke-BoundedWpr([string[]]$Arguments){
    $script:commandCount++
    $stem=Join-Path $outputRoot ('wpr-'+$script:commandCount)
    # These arguments are locally constructed, with no embedded quotes permitted.
    foreach($arg in $Arguments){if($arg.Contains('"')){throw 'Embedded quote in WPR argument'}}
    $quoted=@($Arguments | ForEach-Object {'"'+$_+'"'}) -join ' '
    $p=Start-Process -FilePath $wpr -ArgumentList $quoted -WindowStyle Hidden -PassThru -RedirectStandardOutput ($stem+'.stdout.txt') -RedirectStandardError ($stem+'.stderr.txt')
    try {
        if(-not $p.WaitForExit(30000)){$p.Kill();$p.WaitForExit();throw 'WPR command exceeded 30 seconds'}
        if($p.ExitCode -ne 0){throw ('WPR failed with exit '+$p.ExitCode+'; see '+$stem)}
        return $stem
    } finally {$p.Dispose()}
}

function Get-IdentitySnapshot {
    $adapters=@(Get-NetAdapter -ErrorAction Stop | Where-Object {$_.InterfaceDescription -match 'Qualcomm.*7800' -and $_.Status -eq 'Up'})
    if($adapters.Count -ne 1 -or $adapters[0].DriverVersion -ne '1.0.4374.1300'){throw 'Expected one Up exact-version FastConnect adapter'}
    $driver=Get-CimInstance Win32_SystemDriver -Filter "Name='qcwlan'" -ErrorAction Stop
    if($driver.State -ne 'Running' -or (Get-FileHash -LiteralPath $driver.PathName).Hash -ne 'ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'){throw 'Active driver hash/state mismatch'}
    $apps=@(Get-CimInstance Win32_Process -Filter "Name='QUTS.exe'" -ErrorAction Stop)
    if($apps.Count -lt 1 -or $apps.Count -gt 8){throw 'Expected 1-8 existing QUTS applications'}
    $images=@(foreach($app in $apps){
        if(-not $app.ExecutablePath){throw 'Running QUTS image path unavailable'}
        if((Get-FileHash -LiteralPath $app.ExecutablePath).Hash -ne '8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297'){throw 'Running QUTS path has unreviewed file hash'}
        $proc=Get-Process -Id $app.ProcessId -ErrorAction Stop
        try {$module=$proc.MainModule; $base=$module.BaseAddress.ToInt64(); $modulePath=$module.FileName} finally {$proc.Dispose()}
        if(-not $base -or $modulePath -ne $app.ExecutablePath){throw 'QUTS module identity unavailable or mismatched'}
        [pscustomobject]@{process_id=$app.ProcessId;creation_time=$app.CreationDate;image_path=$modulePath;module_base=('0x{0:x}' -f $base);sha256='8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297'}
    })
    $driverKey=(Get-PnpDeviceProperty -InstanceId $adapters[0].PnPDeviceID -KeyName DEVPKEY_Device_Driver -ErrorAction Stop).Data
    [pscustomobject]@{adapter_guid=[string]$adapters[0].InterfaceGuid;pnp_id=$adapters[0].PnPDeviceID;driver_version=$adapters[0].DriverVersion;driver_key=$driverKey;status=[string]$adapters[0].Status;processes=$images}
}

try {
    Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $outputRoot 'executed-script.ps1')
    $savedProfile=Join-Path $outputRoot 'executed-profile.wprp'
    Copy-Item -LiteralPath $profile -Destination $savedProfile
    $result.script_sha256=(Get-FileHash -LiteralPath (Join-Path $outputRoot 'executed-script.ps1')).Hash
    $result.profile_sha256=(Get-FileHash -LiteralPath $savedProfile).Hash
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class WhtRegistryControlThread {
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
'@
    $before=Get-IdentitySnapshot
    $before | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'identity-before.json') -Encoding UTF8
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputRoot 'result.json') -Encoding UTF8
    $null=Invoke-BoundedWpr @('-profiles',$savedProfile)
    $attempted=$true
    $null=Invoke-BoundedWpr @('-start',($savedProfile+'!QutsRegistry'),'-instancename',$instance)
    $result.trace_started=$true
    # Read-only positive control. Distinguish this PID from every vendor PID.
    $result.control_process_id=$PID
    $result.control_qpc_frequency=[string][Diagnostics.Stopwatch]::Frequency
    Start-Sleep -Milliseconds 250
    Invoke-ReadControls 'start' $before.driver_key
    Start-Sleep -Seconds $Seconds
    Invoke-ReadControls 'end' $before.driver_key
    Start-Sleep -Milliseconds 100
    $null=Invoke-BoundedWpr @('-status','collectors','-details','-instancename',$instance)
    $null=Invoke-BoundedWpr @('-stop',(Join-Path $outputRoot 'registry.etl'),'-skipPdbGen','-instancename',$instance)
    $result.trace_stopped=$true
    $result.cleanup='stopped-own-instance'
    $after=Get-IdentitySnapshot
    $after | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'identity-after.json') -Encoding UTF8
    $same=$before.adapter_guid -eq $after.adapter_guid -and $before.pnp_id -eq $after.pnp_id -and
        (($before.processes | Sort-Object process_id | ConvertTo-Json -Depth 5 -Compress) -eq ($after.processes | Sort-Object process_id | ConvertTo-Json -Depth 5 -Compress))
    if(-not $same){throw 'Adapter/process identity changed; capture is ambiguous'}
    $result.disposition='captured_requires_event_and_loss_review'
    $exitCode=0
} catch {
    $result.error=$_.Exception.Message
    $result.disposition='blocked_or_failed'
} finally {
    if($attempted -and -not $result.trace_stopped){
        try {$null=Invoke-BoundedWpr @('-cancel','-instancename',$instance);$result.cleanup='cancelled-own-instance'}
        catch {$result.cleanup='cleanup-unconfirmed: '+$_.Exception.Message;$exitCode=1}
    }
    $result.finished_utc=[DateTimeOffset]::UtcNow.ToString('o')
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputRoot 'result.json') -Encoding UTF8
}
[pscustomobject]@{disposition=$result.disposition;cleanup=$result.cleanup;output_directory=$outputRoot}
exit $exitCode
