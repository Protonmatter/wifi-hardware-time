#requires -Version 5.1
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '../research/acquisition/Invoke-PassiveObservation.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $source).Path,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$definition=$ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-PassivePython'},$true)
if($null -eq $definition){throw 'Missing testable native process helper'}
Invoke-Expression $definition.Extent.Text
$python=(Get-Command python -ErrorAction Stop).Source
$folder=Join-Path (Join-Path $PSScriptRoot '../artifacts') ('passive-launcher-test-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder | Out-Null
$child=Join-Path $folder 'child.py'
try {
    foreach($expected in 0,1,2){
        "import sys`nsys.stderr.write('offline diagnostic\n')`nsys.exit($expected)" | Set-Content -LiteralPath $child -Encoding UTF8
        $actual=Invoke-PassivePython -PythonPath $python -RunnerPath $child -ManifestPath (Join-Path $folder 'unused.json') -ManifestSha256 ('0'*64) -Folder $folder
        if($actual -ne $expected){throw "Exit-code mismatch: expected $expected, got $actual"}
        if((Get-Content (Join-Path $folder 'runner.stderr.txt') -Raw) -notmatch 'offline diagnostic'){throw 'Missing stderr evidence'}
    }
    Write-Output 'Passive launcher exit/stderr regressions passed; no tracing or adapter operation.'
} finally {
    foreach($name in 'child.py','runner.stdout.txt','runner.stderr.txt'){
        $path=Join-Path $folder $name
        if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}
    }
    Remove-Item -LiteralPath $folder
}
