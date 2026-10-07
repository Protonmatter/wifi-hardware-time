#requires -Version 5.1
<#
.SYNOPSIS
Preview, build, or run one exact-adapter device-service positive control.
.DESCRIPTION
Default is read-only preflight. -BuildOnly compiles and self-tests without WLAN
calls. -Execute enumerates services; -TestGet additionally sends one fixed opcode-1
test GET only if advertised. No TSF request, cross timestamp, arbitrary command,
notification registration, firmware mask, profile change or automatic elevation.
Requires installed Visual Studio C tools/SDK to build. The service API may require
an administrator token. Record elevation; do not retry failures automatically.
The owned native child has a 30-second observation bound and 5-second cleanup
wait. Timeout is unknown execution outcome, not proof of server/firmware drain.
Exit 0: preview/build/control passed; 1: failure; PowerShell binding errors are
usage failures. Private output is restricted to a NEW directory under artifacts.
Rollback: no configuration to restore; preserve the receipt then remove only the
chosen generated directory. Process exit closes the client handle, not a clock epoch.
.EXAMPLE
./research/adapters/Invoke-DeviceServiceControl.ps1 -InterfaceIndex 20
.EXAMPLE
./research/adapters/Invoke-DeviceServiceControl.ps1 -BuildOnly -Architecture arm64 -OutputDirectory artifacts/service-control-build
.EXAMPLE
./research/adapters/Invoke-DeviceServiceControl.ps1 -Execute -TestGet -InterfaceIndex 20 -OutputDirectory artifacts/service-control-once
#>
[CmdletBinding()]
param(
    [ValidateRange(0,2147483647)][int]$InterfaceIndex=0,
    [ValidateSet('arm64','x64')][string]$Architecture='arm64',
    [string]$OutputDirectory,
    [switch]$BuildOnly,
    [switch]$Execute,
    [switch]$TestGet
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$expectedHash='CA884CE1A22113194F3C467F36ABC39AFB0C137E5A7A8E2697420438B21E4115'
$receiptPath=$null
$receipt=[ordered]@{schema='wht/device-service-control-run-v1'; mode='preview'; elevated=$false; result='not_started'; hardware_timing_qualified=$false}
function Get-TargetContext {
    $items=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.ifIndex -eq $InterfaceIndex})
    if($items.Count -ne 1){throw 'Interface missing or ambiguous.'}
    $a=$items[0]
    if($a.DriverFileName -ine 'qcwlanhmt8380.sys' -or $a.DriverVersion -ne '1.0.4374.1300' -or $a.Status.ToString() -ne 'Up'){
        throw 'Require the exact Qualcomm package on an Up adapter.'
    }
    $s=Get-CimInstance Win32_SystemDriver -Filter "Name='qcwlan'" -ErrorAction Stop
    if(-not $s -or $s.State -ne 'Running' -or -not (Test-Path -LiteralPath $s.PathName -PathType Leaf)){
        throw 'Running Qualcomm driver file unavailable.'
    }
    $hash=(Get-FileHash -LiteralPath $s.PathName -Algorithm SHA256).Hash
    if($hash -ne $expectedHash){throw 'Driver hash mismatch.'}
    return [ordered]@{interface_index=$InterfaceIndex; interface_guid=([guid]$a.InterfaceGuid).ToString('B');
        status=$a.Status.ToString(); driver_version=$a.DriverVersion; driver_path=$s.PathName; driver_sha256=$hash}
}
function Invoke-BoundedChild([string]$File,[string]$Arguments,[string]$Prefix,
    [ValidateRange(100,30000)][int]$TimeoutMs=30000) {
    $p=New-Object System.Diagnostics.Process
    $started=$false
    try {
        $p.StartInfo.FileName=$File;$p.StartInfo.Arguments=$Arguments
        $p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true
        $p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
        if(-not $p.Start()){throw 'Owned child did not start.'}
        $started=$true
        $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
        if(-not $p.WaitForExit($TimeoutMs)){
            $receipt['child_timeout']= $true
            $receipt['execution_outcome_unknown']= $true
            throw 'Owned child exceeded its deadline; no retry or drain claim.'
        }
        if(-not $stdout.Wait(5000) -or -not $stderr.Wait(5000)){throw 'Child output did not close.'}
        [IO.File]::WriteAllText(($Prefix+'.stdout.txt'),$stdout.Result)
        [IO.File]::WriteAllText(($Prefix+'.stderr.txt'),$stderr.Result)
        return $p.ExitCode
    } finally {
        try {
            if($started -and -not $p.HasExited){
                $p.Kill()
                if(-not $p.WaitForExit(5000)){throw 'Owned child cleanup incomplete.'}
            }
        } finally {$p.Dispose()}
    }
}
try {
    if($BuildOnly -and ($Execute -or $TestGet)){throw 'BuildOnly cannot acquire data.'}
    if($TestGet -and -not $Execute){throw 'TestGet requires Execute.'}
    if(-not $BuildOnly -and $InterfaceIndex -eq 0){throw 'An explicit interface index is required.'}
    if($Execute -and $Architecture -ne 'arm64'){throw 'This live profile is ARM64 only.'}
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    try {$receipt.elevated=(New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}
    finally {$identity.Dispose()}
    if(-not $BuildOnly){$receipt['before']=Get-TargetContext}
    if(-not $BuildOnly -and -not $Execute){$receipt.result='preflight_passed';$receipt | ConvertTo-Json -Depth 8;exit 0}
    if(-not $OutputDirectory){throw 'A new private output directory is required.'}
    $output=if([IO.Path]::IsPathRooted($OutputDirectory)){[IO.Path]::GetFullPath($OutputDirectory)}else{[IO.Path]::GetFullPath((Join-Path $repo $OutputDirectory))}
    $artifactRoot=[IO.Path]::GetFullPath((Join-Path $repo 'artifacts'))+[IO.Path]::DirectorySeparatorChar
    if(-not $output.StartsWith($artifactRoot,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $output)){
        throw 'Require a new output directory below this repository artifacts folder.'
    }
    $null=New-Item -ItemType Directory -Path $output -ErrorAction Stop
    $receiptPath=Join-Path $output 'result.json'
    $receipt.mode=if($BuildOnly){'build_only'}elseif($TestGet){'enumerate_and_fixed_test_get'}else{'enumerate_only'}
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $installation=& $vswhere -latest -products '*' -property installationPath
    if($LASTEXITCODE -ne 0 -or -not $installation){throw 'Installed Visual Studio tools not found.'}
    Import-Module (Join-Path $installation 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
    $hostArch=if($env:PROCESSOR_ARCHITEW6432){$env:PROCESSOR_ARCHITEW6432}else{$env:PROCESSOR_ARCHITECTURE}
    $hostArch=switch($hostArch){'ARM64'{'arm64'} 'AMD64'{'x64'} default{throw 'Unsupported build host.'}}
    Enter-VsDevShell -VsInstallPath $installation -SkipAutomaticLocation -DevCmdArguments ('-arch='+$Architecture+' -host_arch='+$hostArch) | Out-Null
    if($env:VSCMD_ARG_TGT_ARCH -ne $Architecture){throw 'Compiler target mismatch.'}
    $source=Join-Path $PSScriptRoot 'device_service_control.c'
    $binary=Join-Path $output 'device_service_control.exe'
    $receipt['source_sha256']=(Get-FileHash -LiteralPath $source).Hash
    & cl.exe /nologo /W4 /WX /O2 /Brepro $source ('/Fo'+(Join-Path $output 'control.obj')) ('/Fe'+$binary) /link /Brepro wlanapi.lib iphlpapi.lib ole32.lib advapi32.lib *> (Join-Path $output 'build.txt')
    if($LASTEXITCODE -ne 0){throw 'Build failed; inspect build.txt.'}
    $receipt['binary_sha256']=(Get-FileHash -LiteralPath $binary).Hash
    if((Invoke-BoundedChild $binary '--self-test' (Join-Path $output 'self-test')) -ne 0){throw 'Offline native self-test failed.'}
    if($Execute){
        $fresh=Get-TargetContext
        if(($fresh | ConvertTo-Json -Compress) -ne ($receipt.before | ConvertTo-Json -Compress)){throw 'Identity changed during build.'}
        $arguments='--execute '+$InterfaceIndex+' '+$fresh.interface_guid
        if($TestGet){$arguments+=' --test-get'}
        $receipt['live_attempted']=$true
        $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
        try {
            $code=Invoke-BoundedChild $binary $arguments (Join-Path $output 'control')
            $receipt['native_exit_code']=$code
            $receipt['native_result']=Get-Content -LiteralPath (Join-Path $output 'control.stdout.txt') -Raw | ConvertFrom-Json
        } finally {
            try {$receipt['after']=Get-TargetContext}
            catch {$receipt['postflight_error']=$_.Exception.Message}
        }
        if($receipt.Contains('postflight_error')){throw 'Postflight failed; native outcome retained separately.'}
        if(($receipt.after | ConvertTo-Json -Compress) -ne ($receipt.before | ConvertTo-Json -Compress)){throw 'Target identity or state changed.'}
        if($code -ne 0){throw 'Native control failed; inspect recorded API status. No automatic retry.'}
    }
    $receipt.result='passed'
    $receipt | ConvertTo-Json -Depth 8
    exit 0
} catch {
    $receipt.result='failed';$receipt['error']=$_.Exception.Message
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally {
    if($receiptPath){$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8}
}
