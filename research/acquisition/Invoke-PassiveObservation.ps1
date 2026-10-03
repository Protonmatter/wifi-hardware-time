#requires -Version 5.1
#requires -RunAsAdministrator
<# Elevated child wrapper for bounded observation.
Requires an exact-source manifest under ignored artifacts and an existing Python.
Start this script with RunAs for UAC; it does not elevate itself or install anything.
Exit code mirrors the runner (0 healthy observation, 1 rejection/failure, 2 usage).
No private requests, adapter reset, firmware settings or clock writes.
Default is passive. Explicit -ScanComparison selects up to three documented
WlanScan requests; scans can temporarily increase network latency.
Keeps an exclusive launch receipt; use a fresh manifest directory for a new run. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ManifestPath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256,
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [switch]$ScanComparison
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-PassivePython {
    param([string]$PythonPath,[string]$RunnerPath,[string]$ManifestPath,[string]$ManifestSha256,[string]$Folder)
    $arguments=@(('"'+$RunnerPath+'"'),'--manifest',('"'+$ManifestPath+'"'),'--manifest-sha256',$ManifestSha256,'--execute')
    $child=Start-Process -FilePath $PythonPath -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $Folder 'runner.stdout.txt') -RedirectStandardError (Join-Path $Folder 'runner.stderr.txt')
    return $child.ExitCode
}
$ManifestPath=(Resolve-Path -LiteralPath $ManifestPath).Path
$PythonPath=(Resolve-Path -LiteralPath $PythonPath).Path
$folder=Split-Path -Parent $ManifestPath
$runnerName=if($ScanComparison){'run_scan_comparison.py'}else{'run_passive_observation.py'}
$runner=Join-Path $PSScriptRoot $runnerName
$stream=[IO.File]::Open((Join-Path $folder 'launch-start.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    $bytes=[Text.Encoding]::UTF8.GetBytes(([pscustomobject]@{Pid=$PID;StartedUtc=[DateTime]::UtcNow.ToString('o');ManifestSha256=$ManifestSha256}|ConvertTo-Json))
    $stream.Write($bytes,0,$bytes.Length)
} finally {$stream.Dispose()}
$code=1;$failure=$null
try {
    $code=Invoke-PassivePython -PythonPath $PythonPath -RunnerPath $runner -ManifestPath $ManifestPath -ManifestSha256 $ManifestSha256 -Folder $folder
} catch {$failure=$_.Exception.Message}
finally {
    [pscustomobject]@{ExitCode=$code;Error=$failure;CompletedUtc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $folder 'process-result.json') -Encoding UTF8
}
exit $code
