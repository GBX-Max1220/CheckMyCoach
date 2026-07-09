$paths = @(
    "C:\Program Files",
    "C:\Program Files (x86)",
    "$env:LOCALAPPDATA\Programs",
    "$env:LOCALAPPDATA\Microsoft\WindowsApps",
    "$env:LOCALAPPDATA\Packages"
)

foreach ($base in $paths) {
    if (Test-Path $base) {
        $items = Get-ChildItem $base -Directory -ErrorAction SilentlyContinue | Sort-Object Name
        foreach ($item in $items) {
            $size = (Get-ChildItem $item.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            if ($size -gt 200MB) {
                $gb = [math]::Round($size / 1GB, 2)
                Write-Host "$gb GB  $($item.FullName)"
            }
        }
    }
}
