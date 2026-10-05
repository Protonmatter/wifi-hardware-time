#requires -Version 5.1
# Offline: extract only the child-process helper. Never query an adapter.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$source=Join-Path $PSScriptRoot '../research/adapters/Invoke-DeviceServiceControl.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Launcher parser failure.'}
$helper=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-BoundedChild'},$true)
if(-not $helper){throw 'Child helper absent.'}
Invoke-Expression $helper.Extent.Text
$receipt=[ordered]@{}
$base=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts'))
$temp=Join-Path $base ('DeviceServiceControlTest-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $temp
$ps=Join-Path $env:windir 'System32/WindowsPowerShell/v1.0/powershell.exe'
try {
    foreach($code in @(0,7)){
        $actual=Invoke-BoundedChild $ps ('-NoProfile -Command "exit '+$code+'"') (Join-Path $temp ('exit'+$code)) 5000
        if($actual -ne $code){throw 'Short-lived child exit lost.'}
    }
    $watch=[Diagnostics.Stopwatch]::StartNew();$rejected=$false
    try {$null=Invoke-BoundedChild $ps '-NoProfile -Command "Start-Sleep -Seconds 20"' (Join-Path $temp 'timeout') 1000}
    catch {if($_.Exception.Message -notlike 'Owned child exceeded*'){throw};$rejected=$true}
    if(-not $rejected -or $watch.ElapsedMilliseconds -gt 8000 -or -not $receipt.execution_outcome_unknown){throw 'Timeout/cleanup contract failed.'}
    foreach($caseArguments in @('-BuildOnly -TestGet','-TestGet','-Execute -InterfaceIndex 0')){
        $actual=Invoke-BoundedChild $ps ('-NoProfile -File "'+$source+'" '+$caseArguments) (Join-Path $temp 'rejected') 5000
        if($actual -ne 1){throw 'Invalid acquisition options were not rejected.'}
    }
    Write-Output 'Device-service launcher checks passed; no adapter access.'
} finally {
    $resolved=[IO.Path]::GetFullPath($temp)
    if(-not $resolved.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup target escaped test artifacts.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
