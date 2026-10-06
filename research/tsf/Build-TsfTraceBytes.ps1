#requires -Version 5.1
<#
.SYNOPSIS
Build and self-test a saved-file TSF trace-byte exporter.
.DESCRIPTION
Requires installed Visual Studio C tools and Windows SDK. Ordinary user rights.
No device access, ETW session control, provider enablement or vendor code loading.
Outputs ignored artifacts/tsf-trace-bytes-<architecture>. Exit 0 success, 1 failure.
Rollback: retain evidence, then remove only the selected generated build directory.
.EXAMPLE
./research/tsf/Build-TsfTraceBytes.ps1 -Architecture arm64
#>
[CmdletBinding()]
param([ValidateSet('arm64','x64')][string]$Architecture='arm64')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
try {
    $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $output=Join-Path $repo ('artifacts/tsf-trace-bytes-'+$Architecture)
    $null=New-Item -ItemType Directory -Path $output -Force
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $installation=& $vswhere -latest -products '*' -property installationPath
    if($LASTEXITCODE -ne 0 -or -not $installation){throw 'Visual Studio build tools unavailable.'}
    Import-Module (Join-Path $installation 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
    $hostArch=[Environment]::GetEnvironmentVariable('PROCESSOR_ARCHITEW6432')
    if(-not $hostArch){$hostArch=$env:PROCESSOR_ARCHITECTURE}
    $hostArch=switch($hostArch){'ARM64'{'arm64'} 'AMD64'{'x64'} default{throw 'ARM64 or x64 host required.'}}
    Enter-VsDevShell -VsInstallPath $installation -SkipAutomaticLocation -DevCmdArguments ('-arch='+$Architecture+' -host_arch='+$hostArch) | Out-Null
    if($env:VSCMD_ARG_TGT_ARCH -ne $Architecture){throw 'Requested compiler target not active.'}
    $compiler=(Get-Command cl.exe -ErrorAction Stop).Source
    $source=Join-Path $PSScriptRoot 'export_tsf_trace_bytes.c'
    $binary=Join-Path $output 'export_tsf_trace_bytes.exe'
    & $compiler /nologo /W4 /WX /O2 /Brepro $source ('/Fo'+$output+'\') ('/Fe'+$binary) /link /Brepro advapi32.lib
    if($LASTEXITCODE -ne 0){throw 'Trace-byte exporter compilation failed.'}
    & $binary --self-test
    if($LASTEXITCODE -ne 0){throw 'Trace-byte exporter self-test failed.'}
    Write-Output ('Built file-only exporter: '+$binary)
    exit 0
} catch {Write-Error $_ -ErrorAction Continue;exit 1}
