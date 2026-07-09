$targets = @(
    "$env:LOCALAPPDATA\pip",
    "$env:LOCALAPPDATA\uv",
    "$env:LOCALAPPDATA\Temp",
    "$env:LOCALAPPDATA\hermes",
    "$env:USERPROFILE\.cache",
    "$env:LOCALAPPDATA\Programs\Python",
    "$env:USERPROFILE\anaconda3",
    "$env:USERPROFILE\AppData\Roaming"
)

foreach ($t in $targets) {
    if (Test-Path $t) {
        $size = (Get-ChildItem $t -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $gb = [math]::Round($size / 1GB, 2)
        if ($gb -gt 0.1) {
            Write-Host "$gb GB  $t"
        }
    } else {
        Write-Host "not found  $t"
    }
}
