#requires -Version 5.1
<#
.SYNOPSIS
Build public-query and ETW health helpers; never runs acquisition.
.DESCRIPTION
Requires installed Visual Studio target build tools and Windows SDK. Outputs only
to ignored artifacts/ndis-experiment-<architecture>. Exit 0 on build/manifest success, 1 on failure.
Validate with --help only; hardware and controller modes need separate authority.
Rollback: remove this experiment's generated output after preserving evidence.
#>
[CmdletBinding()]
param([ValidateSet('arm64','x64')][string]$Architecture='arm64')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
try {
    $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $output=Join-Path $repo ('artifacts/ndis-experiment-'+$Architecture)
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
    $sources=@();$binaries=@()
    foreach($name in @('ndis_query_probe','ndis_trace_health')){
        $source=Join-Path $PSScriptRoot ($name+'.c')
        $binary=Join-Path $output ($name+'.exe')
        $object=Join-Path $output ($name+'.obj')
        & $compiler /nologo /W4 /WX /O2 /Brepro $source ('/Fo'+$object) ('/Fe'+$binary) /link /Brepro ('/MACHINE:'+$Architecture) iphlpapi.lib advapi32.lib ole32.lib
        if($LASTEXITCODE -ne 0){throw ('Compilation failed: '+$name)}
        $sources += [pscustomobject]@{path=('research/windows_timestamps/'+$name+'.c');sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash}
        $binaries += [pscustomobject]@{name=($name+'.exe');sha256=(Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash}
    }
    $sources += [pscustomobject]@{path='research/windows_timestamps/Build-NdisExperiment.ps1';sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash}
    [pscustomobject]@{schema='ndis-experiment-build/v1';architecture=$Architecture;compiler=$compiler;compiler_sha256=(Get-FileHash -LiteralPath $compiler -Algorithm SHA256).Hash;sdk_version=$env:WindowsSDKVersion;sources=$sources;binaries=$binaries} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding UTF8
    Write-Output (Join-Path $output 'manifest.json')
    exit 0
} catch {Write-Error $_ -ErrorAction Continue;exit 1}
