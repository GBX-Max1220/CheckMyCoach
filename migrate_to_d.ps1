# 安全迁移脚本：把 C 盘大文件/文件夹迁到 D 盘（用软链接保留路径）
# 只动用户目录下的数据，不动系统和程序文件

$targets = @(
    @{Path="$env:USERPROFILE\Downloads"; Label="Downloads"},
    @{Path="$env:USERPROFILE\Desktop"; Label="Desktop"},
    @{Path="$env:USERPROFILE\Documents"; Label="Documents"},
    @{Path="$env:USERPROFILE\Music"; Label="Music"},
    @{Path="$env:USERPROFILE\Pictures"; Label="Pictures"},
    @{Path="$env:USERPROFILE\Videos"; Label="Videos"},
    @{Path="$env:USERPROFILE\OneDrive"; Label="OneDrive"},
    @{Path="$env:LOCALAPPDATA\Programs\Python\Python312\Lib\site-packages\tensorflow"; Label="TensorFlow"},
    @{Path="$env:LOCALAPPDATA\Programs\Python\Python312\Lib\site-packages\torch"; Label="PyTorch"},
    @{Path="$env:LOCALAPPDATA\Microsoft\WindowsApps"; Label="WindowsApps"}
)

Write-Host "=== C 盘大文件夹扫描 ===" -ForegroundColor Cyan
Write-Host ""

$movable = @()
foreach ($t in $targets) {
    $p = $t.Path
    if (Test-Path $p) {
        $size = (Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        if ($size -gt 0) {
            $gb = [math]::Round($size / 1GB, 2)
            Write-Host "$gb GB  $($t.Label)  ($p)" -ForegroundColor Yellow
            if ($gb -gt 0.1) {
                $movable += @{Path=$p; Label=$t.Label; Size=$size}
            }
        }
    } else {
        Write-Host "not found  $($t.Label)"
    }
}

Write-Host ""
Write-Host "=== 前 3 大可迁移目录 ===" -ForegroundColor Cyan
$sorted = $movable | Sort-Object Size -Descending | Select-Object -First 3
$i = 1
foreach ($item in $sorted) {
    $gb = [math]::Round($item.Size / 1GB, 2)
    Write-Host "$i. $gb GB  $($item.Label)  $($item.Path)" -ForegroundColor Green
    $i++
}

Write-Host ""
Write-Host "要迁移最大的 3 个目录到 D:\? (y/n)" -ForegroundColor White
$ans = Read-Host
if ($ans -eq 'y') {
    foreach ($item in $sorted) {
        $name = Split-Path $item.Path -Leaf
        $dest = "D:\$name"
        Write-Host "移动 $name 到 D:\..." -ForegroundColor Yellow
        
        # Step 1: 复制到 D 盘
        robocopy $item.Path $dest /E /COPY:DAT /R:2 /W:2 /NDL /NFL /NJH /NJS
        
        # Step 2: 测试 D 盘文件存在
        if ((Get-ChildItem $dest -ErrorAction SilentlyContinue).Count -gt 0) {
            # Step 3: 删掉 C 盘原文件夹
            Remove-Item $item.Path -Recurse -Force
            # Step 4: 创建软链接
            cmd /c "mklink /J `"$($item.Path)`" `"$dest`"" 
            Write-Host "  ✅ $name 已迁移到 D:\$name" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $name 复制失败，跳过" -ForegroundColor Red
        }
    }
    
    # 报告空间
    $free = (Get-PSDrive C).Free
    $freeGb = [math]::Round($free / 1GB, 1)
    Write-Host "C 盘剩余: $freeGb GB" -ForegroundColor Cyan
} else {
    Write-Host "取消" -ForegroundColor Gray
}
