<#
.SYNOPSIS
    TwelveToneAnalyzer — Interactive Update Script
.DESCRIPTION
    Run after making code changes. Asks:
      1. Continue modifying? (Y → exit and modify, then re-run)
      2. Package new EXE?     (runs build.bat, optional version bump)
      3. Upload to GitHub?    (git add/commit/push)
.EXAMPLE
    .\update.ps1
#>

$ErrorActionPreference = "Continue"
$APP_NAME = "TwelveToneAnalyzer"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  $APP_NAME — Update Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ═══════════════════════════════════════════════════════════════
# Step 1 — Continue modifying?
# ═══════════════════════════════════════════════════════════════
$continue = Read-Host "[1/4] Do you want to continue modifying code? [Y/N]"
if ($continue -match '^[Yy]') {
    Write-Host ""
    Write-Host "    OK, make your changes. When done, run:" -ForegroundColor Yellow
    Write-Host "      .\update.ps1" -ForegroundColor White
    Write-Host ""
    exit 0
}

Write-Host "    Proceeding with update workflow..." -ForegroundColor Green
Write-Host ""

# ═══════════════════════════════════════════════════════════════
# Step 2 — Package new EXE?
# ═══════════════════════════════════════════════════════════════
$doBuild = Read-Host "[2/4] Package new EXE? [Y/N]"
$versionBumped = $false

if ($doBuild -match '^[Yy]') {
    # --- Optional version bump ---
    $newVersion = Read-Host "    Enter new version (press Enter to skip)"
    if ($newVersion -and $newVersion.Trim() -ne '') {
        $newVersion = $newVersion.Trim()
        Write-Host "    Bumping version to v$newVersion ..." -ForegroundColor Yellow

        # installer.nsi
        $nsiPath = Join-Path $SCRIPT_DIR "installer.nsi"
        if (Test-Path $nsiPath) {
            $nsi = Get-Content $nsiPath -Raw
            $nsi = $nsi -replace '!define VERSION "[\d.]+"', "!define VERSION `"$newVersion`""
            $nsi | Set-Content $nsiPath -NoNewline
            Write-Host "      installer.nsi updated" -ForegroundColor Green
        }

        # i18n.py
        $i18nPath = Join-Path $SCRIPT_DIR "src\utils\i18n.py"
        if (Test-Path $i18nPath) {
            $i18n = Get-Content $i18nPath -Raw
            $i18n = $i18n -replace 'v[\d.]+', "v$newVersion"
            $i18n | Set-Content $i18nPath -NoNewline
            Write-Host "      src\utils\i18n.py updated" -ForegroundColor Green
        }

        # macOS: TwelveToneAnalyzer_mac.spec (CFBundleShortVersionString + CFBundleVersion)
        $macSpecPath = Join-Path $SCRIPT_DIR "TwelveToneAnalyzer_mac.spec"
        if (Test-Path $macSpecPath) {
            $macSpec = Get-Content $macSpecPath -Raw
            $macSpec = $macSpec -replace "'CFBundleShortVersionString': '[\d.]+'", "'CFBundleShortVersionString': '$newVersion'"
            $macSpec = $macSpec -replace "'CFBundleVersion': '[\d.]+'", "'CFBundleVersion': '${newVersion}.0'"
            $macSpec | Set-Content $macSpecPath -NoNewline
            Write-Host "      TwelveToneAnalyzer_mac.spec updated (macOS)" -ForegroundColor Green
        }

        # macOS: build_mac.sh (DMG_NAME)
        $macBuildPath = Join-Path $SCRIPT_DIR "build_mac.sh"
        if (Test-Path $macBuildPath) {
            $macBuild = Get-Content $macBuildPath -Raw
            $macBuild = $macBuild -replace 'DMG_NAME="TwelveToneAnalyzer_Setup_v[\d.]+"', "DMG_NAME=`"TwelveToneAnalyzer_Setup_v$newVersion`""
            $macBuild | Set-Content $macBuildPath -NoNewline
            Write-Host "      build_mac.sh updated (macOS DMG name)" -ForegroundColor Green
        }

        $versionBumped = $true
    }

    # --- Run build.bat ---
    Write-Host "    Building EXE..." -ForegroundColor Yellow
    $buildLog = Join-Path $SCRIPT_DIR ".build_output.tmp"

    # Check .venv exists
    $venvPython = Join-Path $SCRIPT_DIR ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "    [ERROR] .venv not found. Please create it first:" -ForegroundColor Red
        Write-Host "      python -m venv .venv" -ForegroundColor White
        Write-Host "      .venv\Scripts\activate" -ForegroundColor White
        Write-Host "      pip install -r requirements.txt" -ForegroundColor White
        exit 1
    }

    # Run PyInstaller directly (avoid build.bat's pause which hangs)
    & $venvPython -m PyInstaller --clean "$SCRIPT_DIR\TwelveToneAnalyzer.spec" 2>&1 | Tee-Object -FilePath $buildLog

    if ($LASTEXITCODE -ne 0) {
        Write-Host "    [ERROR] Build failed! See .build_output.tmp for details." -ForegroundColor Red
        exit 1
    }
    Remove-Item $buildLog -ErrorAction SilentlyContinue

    # Post-build fixes
    $internal = "dist\$APP_NAME\_internal"
    $qt5bin = ".venv\Lib\site-packages\PyQt5\Qt5\bin"
    if ((Test-Path $internal) -and (Test-Path "$qt5bin\Qt5Core.dll")) {
        Copy-Item "$qt5bin\*.dll" $internal -Force
        Write-Host "    Qt5 DLLs copied" -ForegroundColor Green
    }
    if (Test-Path "resources\fix_qt.conf") {
        Copy-Item "resources\fix_qt.conf" "$internal\PyQt5\qt.conf" -Force
        Write-Host "    qt.conf patched" -ForegroundColor Green
    }

    Write-Host "    EXE built: dist\$APP_NAME\$APP_NAME.exe" -ForegroundColor Green
} else {
    Write-Host "    Skipping EXE build." -ForegroundColor DarkGray
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# Step 3 — Upload to GitHub?
# ═══════════════════════════════════════════════════════════════
$doPush = Read-Host "[3/4] Upload to GitHub? [Y/N]"

if ($doPush -match '^[Yy]') {
    # --- Commit message ---
    $defaultMsg = if ($versionBumped) { "release: v$newVersion" } else { "update: rebuild" }
    $commitMsg = Read-Host "    Enter commit message (press Enter for '$defaultMsg')"
    if (-not $commitMsg -or $commitMsg.Trim() -eq '') {
        $commitMsg = $defaultMsg
    }

    Write-Host "    git add . ..." -ForegroundColor Yellow
    git add .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    [ERROR] git add failed" -ForegroundColor Red
        exit 1
    }

    Write-Host "    git commit ..." -ForegroundColor Yellow
    git commit -m $commitMsg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    [WARN] git commit failed (nothing to commit?)" -ForegroundColor Yellow
    } else {
        Write-Host "    git push ..." -ForegroundColor Yellow
        git push
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    [ERROR] git push failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "    Pushed to GitHub." -ForegroundColor Green
    }
} else {
    Write-Host "    Skipping GitHub upload." -ForegroundColor DarkGray
}

# ═══════════════════════════════════════════════════════════════
# Step 4 — Summary
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Update Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
if ($doBuild -match '^[Yy]') {
    Write-Host "  EXE:         dist\$APP_NAME\$APP_NAME.exe" -ForegroundColor White
}
if ($versionBumped) {
    Write-Host "  Version:     v$newVersion" -ForegroundColor White
}
if ($doPush -match '^[Yy]') {
    Write-Host "  Git:         committed & pushed" -ForegroundColor White
}
Write-Host ""
