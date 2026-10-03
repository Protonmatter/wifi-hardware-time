#requires -Version 5.1
param([string]$CaptureScript=(Join-Path $PSScriptRoot '../research/windows_timestamps/Capture-NdisTimestampStatus.ps1'))
$ErrorActionPreference='Stop'
$capture=$CaptureScript
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($capture,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
$functionAst=$ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-BoundedChild'},$true)
$unbounded=@($functionAst.FindAll({param($node) $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -and $node.Member.Value -eq 'WaitForExit' -and $node.Arguments.Count -eq 0},$true))
if($unbounded.Count){throw 'Unbounded process wait can prevent trace cleanup.'}
# Extract only the owned child helper: never execute the trace/adapter script body.
Invoke-Expression $functionAst.Extent.Text
$artifactRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts'))
$output=Join-Path $artifactRoot ('NdisHelperTest-'+[Guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $output -Force
$ps=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
try {
    Invoke-BoundedChild -File $ps -Arguments @('-NoProfile','-Command','exit 0') -Label 'success'
    $rejected=$false
    try {Invoke-BoundedChild -File $ps -Arguments @('-NoProfile','-Command','exit 7') -Label 'failure'}
    catch {if($_.Exception.Message -notlike '*exit 7'){throw};$rejected=$true}
    if(-not $rejected){throw 'Nonzero child exit accepted.'}
    $timer=[Diagnostics.Stopwatch]::StartNew();$rejected=$false
    try {Invoke-BoundedChild -File $ps -Arguments @('-NoProfile','-Command','Start-Sleep -Seconds 20') -Label 'timeout' -TimeoutMs 300}
    catch {if($_.Exception.Message -notlike '*timeout*'){throw};$rejected=$true}
    if(-not $rejected -or $timer.ElapsedMilliseconds -gt 6000){throw 'Timeout handling not bounded.'}
    Write-Output 'NDIS capture child helper regressions passed; no trace or adapter operation.'
} finally {
    $resolved=[IO.Path]::GetFullPath($output)
    if(-not $resolved.StartsWith($artifactRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw 'Refuse cleanup outside test artifacts.'
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
