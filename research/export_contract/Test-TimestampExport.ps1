#requires -Version 5.1
<#
.SYNOPSIS
Build and run the offline owned timestamp exporter regression harness.
.DESCRIPTION
Requires installed Visual Studio C tools and Windows SDK, ordinary user rights.
No device is opened. Outputs artifacts/owned-export-<architecture>. Exit 0 means
offline structural tests passed; exit 1 means build or test failure. Rollback:
remove this script's artifact directory after preserving any needed evidence.
.PARAMETER Architecture
Compiler target; defaults to ARM64 for this research workstation.
.EXAMPLE
./research/export_contract/Test-TimestampExport.ps1 -Architecture arm64
#>
[CmdletBinding()]
param([ValidateSet('arm64','x64')][string]$Architecture='arm64')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
try {
    $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $output=Join-Path $repo ('artifacts/owned-export-'+$Architecture)
    $null=New-Item -ItemType Directory -Path $output -Force
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $installation=& $vswhere -latest -products '*' -property installationPath
    if($LASTEXITCODE -ne 0 -or -not $installation){throw 'Installed Visual Studio build tools not found.'}
    Import-Module (Join-Path $installation 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
    $hostArchitecture=if($env:PROCESSOR_ARCHITEW6432){$env:PROCESSOR_ARCHITEW6432}else{$env:PROCESSOR_ARCHITECTURE}
    $hostArchitecture=switch($hostArchitecture){'ARM64'{'arm64'} 'AMD64'{'x64'} default{throw 'ARM64 or x64 build host required.'}}
    Enter-VsDevShell -VsInstallPath $installation -SkipAutomaticLocation -DevCmdArguments ('-arch='+$Architecture+' -host_arch='+$hostArchitecture) | Out-Null
    if($env:VSCMD_ARG_TGT_ARCH -ne $Architecture){throw 'Requested compiler target environment not active.'}
    $compiler=(Get-Command cl.exe -ErrorAction Stop).Source
    $binary=Join-Path $output 'native_timestamp_export.exe'
    & $compiler /nologo /std:c11 /W4 /WX /O2 /Brepro (Join-Path $repo 'tests/native_timestamp_export.c') (Join-Path $PSScriptRoot 'timestamp_export.c') ('/Fo'+$output+'\') ('/Fe'+$binary) /link /Brepro ('/MACHINE:'+$Architecture)
    if($LASTEXITCODE -ne 0){throw 'Compilation failed.'}
    & $binary
    if($LASTEXITCODE -ne 0){throw 'Offline contract regression failed.'}
    Write-Output ('Compiler: '+$compiler)
    Write-Output ('Binary: '+$binary)
    exit 0
} catch {Write-Error $_ -ErrorAction Continue;exit 1}
