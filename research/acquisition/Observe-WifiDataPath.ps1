#requires -Version 5.1
<#
.SYNOPSIS
Preview or run a bounded FastConnect packet capture beside a CPU-stack trace.
.DESCRIPTION
Preview performs identity, file and profile checks only. Execution requires a
NEW private output directory; the paired kernel trace needs an administrator
token. -PacketsOnly can use existing Npcap permissions without elevation and
explicitly records that no kernel trace was collected. This script does not
self-elevate: launch through normal RunAs/UAC or an existing administrator shell.
Every child command records privilege context, QPC brackets and exit status.
Captures Ethernet headers in normal mode, never requests monitor/promiscuous mode,
and sends no private IOCTL, test packet or firmware command. ETW is system-wide.
The 128-byte snap length can include application data; keep every raw file private.
Requires installed Wireshark/Npcap, Windows WPR and the exact qualified driver.
.EXAMPLE
./Observe-WifiDataPath.ps1
.EXAMPLE
./Observe-WifiDataPath.ps1 -Execute -OutputDirectory C:/PrivateEvidence/wifi-path-01 -ElevationOrigin RunAs
.NOTES
Exit 0 means preview/capture completed, not hardware timestamp qualification.
Exit 1 means blocked/failed. Capture limits: 5-15 seconds, 10000 packets, 8 MiB
packet file, 32 MiB ETW buffers. Cleanup stops/cancels only the unique WPR instance
recorded in result.json and waits for or kills only the owned dumpcap child.
If interrupted externally: wpr -cancel -instancename <recorded instance>.
No device reset, WLAN profile change, service restart or clock adjustment occurs.
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [switch]$PacketsOnly,
    [string]$OutputDirectory,
    [ValidateRange(5,15)][int]$Seconds=10,
    [ValidateSet('ExistingAdministrator','RunAs')][string]$ElevationOrigin='ExistingAdministrator',
    [string]$WiresharkDirectory='C:/Program Files/Wireshark'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$elevated=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$wpr=Join-Path $env:windir 'System32/wpr.exe'
$dumpcap=Join-Path $WiresharkDirectory 'dumpcap.exe'
$profile=Join-Path $PSScriptRoot 'wifi-path.wprp'

function Get-TargetIdentity {
    $adapters=@(Get-NetAdapter -ErrorAction Stop | Where-Object {$_.InterfaceDescription -match 'Qualcomm.*7800' -and $_.Status -eq 'Up'})
    if($adapters.Count -ne 1 -or $adapters[0].DriverVersion -ne '1.0.4374.1300'){throw 'Expected one Up FastConnect 7800 with driver 1.0.4374.1300'}
    $driver=Get-CimInstance Win32_SystemDriver -Filter "Name='qcwlan'" -ErrorAction Stop
    if($driver.State -ne 'Running'){throw 'qcwlan is not running'}
    $hash=(Get-FileHash -LiteralPath $driver.PathName -Algorithm SHA256).Hash.ToLowerInvariant()
    if($hash -ne 'ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'){throw 'Unreviewed driver hash'}
    [pscustomobject]@{guid=([Guid]$adapters[0].InterfaceGuid).ToString('B').ToUpperInvariant();pnp_id=$adapters[0].PnPDeviceID;status=[string]$adapters[0].Status;driver_version=$adapters[0].DriverVersion;driver_sha256=$hash;driver_path=$driver.PathName}
}

$root=$null
$instance='wht-wifi-path-'+[Guid]::NewGuid().ToString('N')
$commands=New-Object 'System.Collections.Generic.List[object]'
$origin=if($elevated){$ElevationOrigin}else{'NonElevated'}
$result=[ordered]@{schema='wht/wifi-data-path-v1';started_utc=[DateTimeOffset]::UtcNow.ToString('o');instance=$instance;is_elevated=$elevated;elevation_origin=$origin;packets_only=[bool]$PacketsOnly;uac_normally_required_for_kernel_trace=$true;seconds=$Seconds;trace_started=$false;trace_stopped=$false;cleanup='not-needed';disposition='blocked';error=$null;qpc_frequency=[string][Diagnostics.Stopwatch]::Frequency;commands=$commands}
$attempted=$false
$exitCode=1

function Save-Result {
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root 'result.json') -Encoding UTF8
}
function Invoke-OwnedCommand([string]$File,[string[]]$Arguments,[int]$TimeoutSeconds=30,[bool]$RequiresAdministrator=$false) {
    foreach($argument in $Arguments){if($argument.Contains('"') -or $argument.EndsWith('\')){throw 'Unsupported command argument quoting'}}
    $stem=Join-Path $root ('command-'+($commands.Count+1))
    $entry=[ordered]@{file=$File;arguments=$Arguments;is_elevated=$elevated;normally_requires_administrator=$RequiresAdministrator;started_utc=[DateTimeOffset]::UtcNow.ToString('o');before_qpc=[string][Diagnostics.Stopwatch]::GetTimestamp();after_qpc=$null;exit_code=$null;timed_out=$false;cleanup='not-started'}
    $commands.Add($entry)
    Save-Result
    $process=$null
    $stdout=$null
    $stderr=$null
    try {
        $quoted=($Arguments | ForEach-Object {'"'+$_+'"'}) -join ' '
        $info=New-Object Diagnostics.ProcessStartInfo
        $info.FileName=$File
        $info.Arguments=$quoted
        $info.UseShellExecute=$false
        $info.CreateNoWindow=$true
        $info.RedirectStandardOutput=$true
        $info.RedirectStandardError=$true
        $process=New-Object Diagnostics.Process
        $process.StartInfo=$info
        if(-not $process.Start()){throw 'Child process did not start'}
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $stderr=$process.StandardError.ReadToEndAsync()
        $entry.cleanup='child-running'
        if(-not $process.WaitForExit($TimeoutSeconds*1000)){
            $entry.timed_out=$true
            $process.Kill()
            if(-not $process.WaitForExit(5000)){throw 'Owned child termination unconfirmed'}
            $entry.cleanup='killed-owned-child'
            throw 'Command deadline exceeded'
        }
        $entry.exit_code=$process.ExitCode
        $entry.cleanup='child-exited'
        if($process.ExitCode -ne 0){throw ('Command failed; inspect '+$stem)}
        return $stem
    } finally {
        $entry.after_qpc=[string][Diagnostics.Stopwatch]::GetTimestamp()
        if($null -ne $stdout -and $stdout.Wait(5000)){[IO.File]::WriteAllText(($stem+'.stdout.txt'),$stdout.Result)}
        if($null -ne $stderr -and $stderr.Wait(5000)){[IO.File]::WriteAllText(($stem+'.stderr.txt'),$stderr.Result)}
        if($null -ne $process){$process.Dispose()}
        Save-Result
    }
}

try {
    foreach($file in @($wpr,$dumpcap,$profile)){if(-not (Test-Path -LiteralPath $file -PathType Leaf)){throw ('Required file missing: '+$file)}}
    $before=Get-TargetIdentity
    if(-not $Execute){
        & $wpr -profiles $profile
        if($LASTEXITCODE -ne 0){throw 'WPR profile rejected'}
        [pscustomobject]@{mode='preview';is_elevated=$elevated;execute_requires_administrator=(-not $PacketsOnly);seconds=$Seconds;driver_version=$before.driver_version;driver_sha256=$before.driver_sha256;packet_snaplen=128;memory_buffers_mib=32}
        exit 0
    }
    if(-not $elevated -and -not $PacketsOnly){throw 'Paired capture requires a normal elevated administrator launch; preview and permitted Npcap-only access do not'}
    if([string]::IsNullOrWhiteSpace($OutputDirectory) -or (Test-Path -LiteralPath $OutputDirectory)){throw 'Provide a NEW private OutputDirectory'}
    $null=New-Item -ItemType Directory -Path $OutputDirectory
    $root=(Resolve-Path -LiteralPath $OutputDirectory).ProviderPath
    $before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'identity-before.json') -Encoding UTF8
    Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $root 'executed-script.ps1')
    $savedProfile=Join-Path $root 'executed-profile.wprp'
    Copy-Item -LiteralPath $profile -Destination $savedProfile
    $result.tool_files=@(foreach($file in @($wpr,$dumpcap,(Join-Path $root 'executed-script.ps1'),$savedProfile)){
        $signature=Get-AuthenticodeSignature -LiteralPath $file
        [pscustomobject]@{path=$file;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash;signature_status=[string]$signature.Status}
    })
    $interface='\Device\NPF_'+$before.guid
    $null=Invoke-OwnedCommand $dumpcap @('--version')
    $types=Invoke-OwnedCommand $dumpcap @('-i',$interface,'-L')
    $typeText=(Get-Content -LiteralPath ($types+'.stdout.txt') -Raw)+(Get-Content -LiteralPath ($types+'.stderr.txt') -Raw)
    if($typeText -notmatch 'EN10MB'){throw 'Normal-mode Ethernet capture unavailable'}
    $null=Invoke-OwnedCommand $wpr @('-profiles',$savedProfile)
    if(-not $PacketsOnly){
        $attempted=$true
        $null=Invoke-OwnedCommand $wpr @('-start',($savedProfile+'!WifiPath'),'-instancename',$instance) 30 $true
        $result.trace_started=$true
        Save-Result
    }
    $null=Invoke-OwnedCommand $dumpcap @('-i',$interface,'-y','EN10MB','-p','-s','128','-B','4','-a',('duration:'+$Seconds),'-a','filesize:8192','-c','10000','-w',(Join-Path $root 'packets.pcapng'),'-q') ($Seconds+15)
    if(-not $PacketsOnly){
        $null=Invoke-OwnedCommand $wpr @('-status','collectors','-details','-instancename',$instance) 30 $true
        $null=Invoke-OwnedCommand $wpr @('-stop',(Join-Path $root 'cpu.etl'),'-skipPdbGen','-instancename',$instance) 30 $true
        $result.trace_stopped=$true
        $result.cleanup='stopped-own-instance'
    } else {$result.cleanup='packet-child-exited; no-kernel-trace-started'}
    $after=Get-TargetIdentity
    $after | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'identity-after.json') -Encoding UTF8
    if(($before | ConvertTo-Json -Compress) -ne ($after | ConvertTo-Json -Compress)){throw 'Adapter identity changed; capture requires quarantine'}
    $result.disposition=if($PacketsOnly){'packets_only_requires_review; kernel_trace_not_collected'}else{'captured_requires_packet_trace_and_loss_review'}
    $exitCode=0
} catch {
    $result.error=$_.Exception.Message
    $result.disposition='blocked_or_failed'
    Write-Warning $result.error
} finally {
    if($attempted -and -not $result.trace_stopped){
        try {$null=Invoke-OwnedCommand $wpr @('-cancel','-instancename',$instance) 30 $true;$result.cleanup='cancelled-own-instance'}
        catch {$result.cleanup='cleanup-unconfirmed: '+$_.Exception.Message;$exitCode=1}
    }
    if($null -ne $root){$result.finished_utc=[DateTimeOffset]::UtcNow.ToString('o');Save-Result}
}
[pscustomobject]@{disposition=$result.disposition;cleanup=$result.cleanup;output_directory=$root}
exit $exitCode
