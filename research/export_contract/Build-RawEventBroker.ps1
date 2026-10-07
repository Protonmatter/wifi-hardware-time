#requires -Version 5.1
<#
.SYNOPSIS
Build a user-mode raw-event broker DLL and run its software concurrency tests.
.DESCRIPTION
Requires installed Visual Studio C tools and Windows SDK, ordinary rights.
No device access, driver install, firmware command or clock change. Outputs
artifacts/raw-event-broker-<architecture>. Exit 0: built/tested; 1: failure.
Rollback: remove only this generated output directory after preserving evidence.
.PARAMETER Architecture
Native compiler target: arm64 (default) or x64. The test binary must run locally.
.EXAMPLE
./research/export_contract/Build-RawEventBroker.ps1 -Architecture arm64
#>
[CmdletBinding()]
param([ValidateSet('arm64','x64')][string]$Architecture='arm64')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$testProcess=$null
$testStarted=$false
try {
    $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $output=Join-Path $repo ('artifacts/raw-event-broker-'+$Architecture)
    $null=New-Item -ItemType Directory -Path $output -Force
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $installation=& $vswhere -latest -products '*' -property installationPath
    if($LASTEXITCODE -ne 0 -or -not $installation){throw 'Installed Visual Studio build tools not found.'}
    Import-Module (Join-Path $installation 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
    $hostArchitecture=if($env:PROCESSOR_ARCHITEW6432){$env:PROCESSOR_ARCHITEW6432}else{$env:PROCESSOR_ARCHITECTURE}
    $hostArchitecture=switch($hostArchitecture){'ARM64'{'arm64'} 'AMD64'{'x64'} default{throw 'ARM64 or x64 host required.'}}
    Enter-VsDevShell -VsInstallPath $installation -SkipAutomaticLocation -DevCmdArguments ('-arch='+$Architecture+' -host_arch='+$hostArchitecture) | Out-Null
    if($env:VSCMD_ARG_TGT_ARCH -ne $Architecture){throw 'Requested target environment not active.'}
    $compiler=(Get-Command cl.exe -ErrorAction Stop).Source
    $source=Join-Path $PSScriptRoot 'raw_event_broker.c'
    $harness=Join-Path $repo 'tests/native_raw_event_broker.c'
    $binary=Join-Path $output 'native_raw_event_broker.exe'
    $library=Join-Path $output 'raw_event_broker.dll'
    & $compiler /nologo /std:c11 /W4 /WX /O2 /Brepro $harness $source ('/Fo'+$output+'\') ('/Fe'+$binary) /link /Brepro ('/MACHINE:'+$Architecture)
    if($LASTEXITCODE -ne 0){throw 'Native broker harness compilation failed.'}
    & $compiler /nologo /std:c11 /W4 /WX /O2 /Brepro /LD /DRB_BUILD_SHARED $source ('/Fo'+$output+'\') ('/Fe'+$library) /link /Brepro ('/MACHINE:'+$Architecture) ('/IMPLIB:'+(Join-Path $output 'raw_event_broker.lib'))
    if($LASTEXITCODE -ne 0){throw 'Broker DLL compilation failed.'}
    $stdout=Join-Path $output 'native-tests.txt'
    $stderr=Join-Path $output 'native-tests-errors.txt'
    # A failed/timeout attempt must not leave an older passing test log in place.
    [IO.File]::WriteAllText($stdout,'')
    [IO.File]::WriteAllText($stderr,'')
    # Own the Process handle directly: PowerShell 5.1 Start-Process -PassThru
    # can lose a completed child's ExitCode after a timed WaitForExit call.
    $testProcess=New-Object System.Diagnostics.Process
    $testProcess.StartInfo.FileName=$binary
    $testProcess.StartInfo.UseShellExecute=$false
    $testProcess.StartInfo.CreateNoWindow=$true
    $testProcess.StartInfo.RedirectStandardOutput=$true
    $testProcess.StartInfo.RedirectStandardError=$true
    if(-not $testProcess.Start()){throw 'Native broker harness did not start.'}
    $testStarted=$true
    $standardOutput=$testProcess.StandardOutput.ReadToEndAsync()
    $standardError=$testProcess.StandardError.ReadToEndAsync()
    if(-not $testProcess.WaitForExit(30000)){
        $testProcess.Kill()
        $null=$testProcess.WaitForExit(5000)
        throw 'Native broker harness exceeded 30 seconds.'
    }
    if(-not $standardOutput.Wait(5000) -or -not $standardError.Wait(5000)){throw 'Harness output did not close.'}
    [IO.File]::WriteAllText($stdout,$standardOutput.Result)
    [IO.File]::WriteAllText($stderr,$standardError.Result)
    if($testProcess.ExitCode -ne 0){throw ('Native broker harness failed; inspect '+$stderr)}
    Get-Content -LiteralPath $stdout
    Write-Output ('Built and tested user-mode DLL: '+$library)
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally {
    if($null -ne $testProcess){
        try {
            if($testStarted -and -not $testProcess.HasExited){
                $testProcess.Kill()
                if(-not $testProcess.WaitForExit(5000)){Write-Error 'Owned test process did not exit during cleanup.' -ErrorAction Continue}
            }
        } catch {Write-Error ('Owned test process cleanup failed: '+$_.Exception.Message) -ErrorAction Continue}
        finally {$testProcess.Dispose()}
    }
}
