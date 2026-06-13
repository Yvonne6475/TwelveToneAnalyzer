<#
.SYNOPSIS
    TwelveToneAnalyzer — One-click release script (Windows)

.DESCRIPTION
    Rebuilds EXE + NSIS installer, optionally bumps version and pushes to GitHub.

.PARAMETER Version
    New version string (e.g. "1.2"). If omitted, keeps current version.

.PARAMETER Message
    Git commit message. If omitted, uses "release: v<version>".

.PARAMETER SkipPush
    If set, skips git commit and push.

.EXAMPLE
    .\release.ps1

.EXAMPLE
    .\release.ps1 -Version "1.2" -Message "fix: DLL loading on Windows 11"
#>
param(
    [string]$Version,
    [string]$Message,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$APP_NAME = "TwelveToneAnalyzer"
$PROJECT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  $APP_NAME — Release Builder" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---- 1. Check venv ----
$VENV = "$PROJECT\.venv"
$PYTHON = "$VENV\Scripts\python.exe"
if (-not (Test-Path $PYTHON)) {
    Write-Host "[ERROR] .venv not found at $VENV" -ForegroundColor Red
    Write-Host "        Run: python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt"
    exit 1
}
Write-Host "[1/7] Virtual env: OK" -ForegroundColor Green

# ---- 2. Bump version ----
if ($Version) {
    Write-Host "[2/7] Bumping version to $Version ..." -ForegroundColor Yellow

    # installer.nsi
    $nsi = Get-Content "installer.nsi" -Raw
    $nsi = $nsi -replace '!define VERSION "[\d.]+"', "!define VERSION `"$Version`""
    $nsi | Set-Content "installer.nsi" -NoNewline

    # i18n.py
    $i18n = Get-Content "src\utils\i18n.py" -Raw
    $i18n = $i18n -replace 'v[\d.]+', "v$Version"
    $i18n | Set-Content "src\utils\i18n.py" -NoNewline

    # build_mac.sh
    if (Test-Path "build_mac.sh") {
        $mac = Get-Content "build_mac.sh" -Raw
        $mac = $mac -replace 'DMG_NAME="TwelveToneAnalyzer_Setup_v[\d.]+"', "DMG_NAME=`"TwelveToneAnalyzer_Setup_v$Version`""
        $mac | Set-Content "build_mac.sh" -NoNewline
    }

    Write-Host "         Version bumped to $Version" -ForegroundColor Green
} else {
    Write-Host "[2/7] Version: unchanged (use -Version '1.2' to bump)" -ForegroundColor DarkGray
}

# ---- 3. Clean ----
Write-Host "[3/7] Cleaning old builds..." -ForegroundColor Yellow
if (Test-Path "dist\$APP_NAME")     { Remove-Item -Recurse -Force "dist\$APP_NAME" }
if (Test-Path "build\$APP_NAME")    { Remove-Item -Recurse -Force "build\$APP_NAME" }
if (Test-Path "dist\${APP_NAME}_debug") { Remove-Item -Recurse -Force "dist\${APP_NAME}_debug" }
Remove-Item "TwelveToneAnalyzer_Setup_v*.exe" -Force -ErrorAction SilentlyContinue
Write-Host "         Cleaned" -ForegroundColor Green

# ---- 4. Build EXE ----
Write-Host "[4/7] Building EXE with PyInstaller..." -ForegroundColor Yellow
& $PYTHON -m PyInstaller TwelveToneAnalyzer.spec 2>&1 | Select-Object -Last 5
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "         EXE built" -ForegroundColor Green

# ---- 5. Post-build fixes ----
Write-Host "[5/7] Applying post-build fixes..." -ForegroundColor Yellow

# Fix qt.conf
if (Test-Path "resources\fix_qt.conf") {
    Copy-Item "resources\fix_qt.conf" "dist\$APP_NAME\_internal\PyQt5\qt.conf" -Force
    Write-Host "         qt.conf fixed" -ForegroundColor Green
}

# Copy Qt5 DLLs to _internal root
$QT5_BIN = "$VENV\Lib\site-packages\PyQt5\Qt5\bin"
$INTERNAL = "dist\$APP_NAME\_internal"
if ((Test-Path $INTERNAL) -and (Test-Path "$QT5_BIN\Qt5Core.dll")) {
    Copy-Item "$QT5_BIN\*.dll" $INTERNAL -Force
    Write-Host "         Qt5 DLLs copied to _internal root" -ForegroundColor Green
}

# ---- 6. Build NSIS installer ----
Write-Host "[6/7] Building NSIS installer..." -ForegroundColor Yellow
$NSIS = ".\nsis_portable\nsis-3.10\makensis.exe"
if (Test-Path $NSIS) {
    & $NSIS installer.nsi 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] NSIS build failed" -ForegroundColor Yellow
    } else {
        $installer = Get-ChildItem "TwelveToneAnalyzer_Setup_v*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        Write-Host "         Installer: $($installer.Name) ($('{0:N0}' -f ($installer.Length / 1MB)) MB)" -ForegroundColor Green
    }
} else {
    Write-Host "         NSIS not found, skipping installer" -ForegroundColor DarkGray
}

# ---- 7. Git commit & push ----
if (-not $SkipPush) {
    Write-Host "[7/7] Committing to Git..." -ForegroundColor Yellow
    git add .
    if (-not $Message) {
        if ($Version) {
            $Message = "release: v$Version"
        } else {
            $Message = "release: rebuild installer"
        }
    }
    git commit -m $Message
    git push
    Write-Host "         Pushed to GitHub" -ForegroundColor Green
} else {
    Write-Host "[7/7] Git: skipped (-SkipPush)" -ForegroundColor DarkGray
}

# ---- Done ----
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Release Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  EXE:         dist\$APP_NAME\$APP_NAME.exe" -ForegroundColor White
$installer = Get-ChildItem "TwelveToneAnalyzer_Setup_v*.exe" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($installer) {
    Write-Host "  Installer:   $($installer.Name)" -ForegroundColor White
}
Write-Host ""
