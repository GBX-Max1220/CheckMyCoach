# C 盘清理指引

## 1. 清 Windows 临时文件（最安全）
按 Win + R → 输入 `cleanmgr` → 选择 C 盘 → 勾选所有 → 确定

## 2. 清 pip 缓存
```powershell
pip cache purge
```

## 3. 清 Python 临时文件
```powershell
del $env:TEMP\* /s /q 2>$null
```

## 4. 如果 Hermes 没用上，删它的 venv
```powershell
rm C:\Users\gbx12\AppData\Local\hermes\hermes-agent\venv -Recurse -Force
```

## 5. 查大文件夹
```powershell
# 看 C 盘还剩多少
Get-PSDrive C
```
