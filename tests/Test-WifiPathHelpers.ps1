#requires -Version 5.1
# Offline subprocess regression only: does not run the collector body or open a device.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '../research/acquisition/Observe-WifiDataPath.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
foreach($name in @('Save-Result','Invoke-OwnedCommand')){
    $functionAst=$ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
    if($null -eq $functionAst){throw 'Expected helper unavailable'}
    $unbounded=@($functionAst.FindAll({param($node) $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -and $node.Member.Value -eq 'WaitForExit' -and $node.Arguments.Count -eq 0},$true))
    if($unbounded.Count){throw 'Unbounded child wait'}
    Invoke-Expression $functionAst.Extent.Text
}
$artifactRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts'))
$root=Join-Path $artifactRoot ('WifiPathHelperTest-'+[Guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $root
$commands=New-Object 'System.Collections.Generic.List[object]'
$elevated=$false
$result=[ordered]@{test_only=$true;commands=$commands}
$ps=Join-Path $env:windir 'System32/WindowsPowerShell/v1.0/powershell.exe'
try {
    $null=Invoke-OwnedCommand $ps @('-NoProfile','-Command','exit 0') 5
    if($commands[0].exit_code -ne 0 -or $commands[0].cleanup -ne 'child-exited'){throw 'Successful short-lived exit not retained'}
    $rejected=$false
    try {$null=Invoke-OwnedCommand $ps @('-NoProfile','-Command','exit 7') 5}
    catch {if($_.Exception.Message -notlike 'Command failed*'){throw};$rejected=$true}
    if(-not $rejected -or $commands[1].exit_code -ne 7){throw 'Nonzero exit not retained/rejected'}
    $timer=[Diagnostics.Stopwatch]::StartNew();$rejected=$false
    try {$null=Invoke-OwnedCommand $ps @('-NoProfile','-Command','Start-Sleep -Seconds 20') 1}
    catch {if($_.Exception.Message -ne 'Command deadline exceeded'){throw};$rejected=$true}
    if(-not $rejected -or $timer.ElapsedMilliseconds -gt 8000 -or -not $commands[2].timed_out -or $commands[2].cleanup -ne 'killed-owned-child'){throw 'Timeout cleanup not bounded'}
    $receipt=Get-Content -LiteralPath (Join-Path $root 'result.json') -Raw | ConvertFrom-Json
    if(@($receipt.commands).Count -ne 3 -or @($receipt.commands | Where-Object {$_.is_elevated}).Count){throw 'Privilege receipt mismatch'}
    $rejected=$false
    try {$null=Invoke-OwnedCommand $ps @('bad"argument') 5}
    catch {if($_.Exception.Message -ne 'Unsupported command argument quoting'){throw};$rejected=$true}
    if(-not $rejected -or $commands.Count -ne 3){throw 'Quoted input launched a child'}
    Write-Output 'Wi-Fi path child checks passed: short-lived exit, failure, timeout cleanup, privilege receipt and argument rejection. No acquisition.'
} finally {
    $resolved=[IO.Path]::GetFullPath($root)
    if(-not $resolved.StartsWith($artifactRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup outside test artifacts refused'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
