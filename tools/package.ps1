# 打包 skill 成 zip(Windows PowerShell 用)
# 用法:  .\tools\package.ps1                       打包全部 skill
#        .\tools\package.ps1 ziwei calendar-converter   只打包指定的
# 若出現「已停用指令碼執行」,先執行一次:
#        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# 產出在 dist\,每個 skill 一個 zip;zip 內路徑用「/」,上傳 claude.ai 與 Linux/Mac 都能正確解開。
# Windows 不存放金鑰:mingli-master 沒有 config.json 時會跳過,請改在 Chromebook / Mac 打包。
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Skills)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$dist = Join-Path $root "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
if (-not $Skills) { $Skills = Get-ChildItem (Join-Path $root "skills") -Directory | ForEach-Object Name }
foreach ($s in $Skills) {
    $src = Join-Path (Join-Path $root "skills") $s
    if (-not (Test-Path (Join-Path $src "SKILL.md"))) { Write-Host "略過 $s(找不到 SKILL.md)"; continue }
    if ($s -eq "mingli-master" -and -not (Test-Path (Join-Path $src "config.json"))) {
        Write-Host "⚠ 略過 mingli-master:沒有 config.json,打包後存檔網址會遺失。請在 Chromebook / Mac 打包。" -ForegroundColor Yellow
        continue
    }
    $zipPath = Join-Path $dist "$s.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath }
    $zip = [System.IO.Compression.ZipFile]::Open($zipPath, "Create")
    try {
        Get-ChildItem $src -Recurse -File | Where-Object {
            $_.FullName -notmatch '[\\/](__pycache__|\.hko_cache)[\\/]' -and $_.Extension -ne ".pyc"
        } | ForEach-Object {
            $rel = $s + "/" + $_.FullName.Substring($src.Length + 1).Replace("\", "/")
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $rel) | Out-Null
        }
    } finally { $zip.Dispose() }
    $extra = if (Test-Path (Join-Path $src "config.json")) { "(含 config.json)" } else { "" }
    Write-Host "✓ dist/$s.zip $extra"
}
