$items = Get-ChildItem $env:APPDATA -Directory
foreach ($item in $items) {
    $files = Get-ChildItem $item.FullName -Recurse -File -ErrorAction SilentlyContinue
    $size = ($files | Measure-Object -Property Length -Sum).Sum
    if ($size -gt 100MB) {
        $gb = [math]::Round($size / 1GB, 2)
        Write-Host "$gb GB  $($item.Name)"
    }
}
