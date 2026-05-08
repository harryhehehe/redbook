#Requires -Version 5.0
<#
.SYNOPSIS
  一键打包"小红书帖子生成器"为 onedir EXE。

.EXAMPLE
  .\build_exe.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  小红书帖子生成器 - PyInstaller 打包" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# 1. 清理旧产物
Write-Host "`n[1/4] 清理旧 build/dist..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$ProjectRoot\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$ProjectRoot\dist"  -ErrorAction SilentlyContinue

# 2. 检查依赖
Write-Host "`n[2/4] 检查 PyInstaller..." -ForegroundColor Yellow
$piVer = (pip show pyinstaller 2>$null | Select-String "Version:").ToString()
if (-not $piVer) {
    Write-Host "PyInstaller 未安装，正在安装..." -ForegroundColor Yellow
    pip install pyinstaller | Out-Null
}
Write-Host "  $piVer" -ForegroundColor Green

# 3. 打包
Write-Host "`n[3/4] PyInstaller 打包中（约 3-8 分钟）..." -ForegroundColor Yellow
$startTime = Get-Date
pyinstaller --noconfirm --clean app.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n打包失败！查看上方错误信息。" -ForegroundColor Red
    exit 1
}
$elapsed = (Get-Date) - $startTime

# 4. 汇报
Write-Host "`n[4/4] 完成 ✓ 用时 $($elapsed.Minutes)分$($elapsed.Seconds)秒" -ForegroundColor Green

$distDir = Join-Path $ProjectRoot "dist\小红书帖子生成器"
$exePath = Join-Path $distDir "小红书帖子生成器.exe"
if (Test-Path $exePath) {
    $size = [math]::Round((Get-ChildItem -Recurse $distDir | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-Host "`n================================================" -ForegroundColor Cyan
    Write-Host "  产物目录：$distDir" -ForegroundColor Green
    Write-Host "  入口 EXE：$exePath" -ForegroundColor Green
    Write-Host "  整体大小：$size MB" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "`n下一步：" -ForegroundColor Yellow
    Write-Host "  1. 双击 $exePath 测试" -ForegroundColor White
    Write-Host "  2. 整个文件夹 zip 后可拷贝到其他 Windows 电脑" -ForegroundColor White
    Write-Host "  3. 详细说明见 BUILD_AND_DEPLOY.md" -ForegroundColor White
} else {
    Write-Host "`n产物没生成，检查 PyInstaller 日志" -ForegroundColor Red
    exit 1
}
