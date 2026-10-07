#requires -Version 7.4
<# Read-only Windows Installer database metadata; never installs or registers a package. #>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[ValidateRange(1,100000)][int]$MaxRows=100000)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if([IO.Path]::GetExtension($Path) -notin @('.msi','.msm')){throw 'Expected MSI/MSM database'}
$installer=$null;$db=$null
try {
    $installer=New-Object -ComObject WindowsInstaller.Installer
    $db=$installer.OpenDatabase((Resolve-Path -LiteralPath $Path).ProviderPath,0)
    $available=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $tableView=$db.OpenView('SELECT `Name` FROM `_Tables`')
    try{
        $tableView.Execute()
        while($null -ne ($record=$tableView.Fetch())){
            try{$null=$available.Add($record.GetType().InvokeMember('StringData','GetProperty',$null,$record,@(1)))}
            finally{[Runtime.InteropServices.Marshal]::ReleaseComObject($record) | Out-Null}
        }
    }finally{$tableView.Close();[Runtime.InteropServices.Marshal]::ReleaseComObject($tableView) | Out-Null}
    $tables=[ordered]@{}
    foreach($table in @('File','Class','ProgId','Component','Registry','TypeLib','AppId')){
        if(-not $available.Contains($table)){
            if($table -eq 'File'){throw 'Required File table is absent'}
            $tables[$table]=@{status='Absent';reason='Table not listed in _Tables'}
            continue
        }
        $view=$null
        try{
            $view=$db.OpenView(('SELECT * FROM `{0}`' -f $table));$view.Execute()
            $rows=[Collections.Generic.List[object]]::new()
            while($null -ne ($record=$view.Fetch())){
                try{
                    $count=$record.GetType().InvokeMember('FieldCount','GetProperty',$null,$record,$null)
                    if($count -le 0 -or $count -gt 64){throw 'Invalid field count'}
                    $row=@(for($i=1;$i -le $count;$i++){$record.GetType().InvokeMember('StringData','GetProperty',$null,$record,@($i))})
                    $rows.Add($row)
                    if($rows.Count -gt $MaxRows){throw 'Table exceeds row bound'}
                }finally{[Runtime.InteropServices.Marshal]::ReleaseComObject($record) | Out-Null}
            }
            $tables[$table]=@($rows.ToArray())
        }finally{if($null -ne $view){$view.Close();[Runtime.InteropServices.Marshal]::ReleaseComObject($view) | Out-Null}}
    }
    [ordered]@{schema='wht/msi-table-inspection-v1';mode='read-only';tables=$tables} | ConvertTo-Json -Depth 9
}finally{
    if($null -ne $db){[Runtime.InteropServices.Marshal]::ReleaseComObject($db) | Out-Null}
    if($null -ne $installer){[Runtime.InteropServices.Marshal]::ReleaseComObject($installer) | Out-Null}
}
