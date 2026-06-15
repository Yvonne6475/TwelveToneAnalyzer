@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM   TwelveToneAnalyzer — Optimized Build Script
REM
REM   【用法】
REM     build.bat               → Quick build (~1min, 增量)
REM     build.bat full          → Full clean build (~5min)
REM     build.bat debug         → Debug build (console)
REM     build.bat installer     → Quick build + NSIS installer
REM     build.bat release       → Full build + NSIS release installer
REM ============================================================

set VENV=.venv
set PYTHON=%VENV%\Scripts\python.exe
set APP_NAME=TwelveToneAnalyzer
set DIST_DIR=dist
set BUILD_DIR=build

REM ── Parse args ────────────────────────────────────────────
set MODE=%1
set MODE2=%2

set DO_CLEAN=no
set DO_NSIS=no
set NSIS_RELEASE=no
set IS_DEBUG=no

if /i "%MODE%"=="full"     set DO_CLEAN=yes
if /i "%MODE%"=="release"  set DO_CLEAN=yes & set DO_NSIS=yes & set NSIS_RELEASE=yes
if /i "%MODE%"=="installer" set DO_NSIS=yes & set NSIS_RELEASE=yes
if /i "%MODE%"=="debug"    set IS_DEBUG=yes
if /i "%MODE2%"=="debug"   set IS_DEBUG=yes
if /i "%MODE2%"=="installer" set DO_NSIS=yes & set NSIS_RELEASE=yes

REM ── Check venv ─────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [ERROR] .venv not found
    pause & exit /b 1
)

REM ── Select spec ───────────────────────────────────────────
if "%IS_DEBUG%"=="yes" (
    set SPEC_FILE=TwelveToneAnalyzer_debug.spec
    set OUTPUT_NAME=%APP_NAME%_debug
) else (
    set SPEC_FILE=TwelveToneAnalyzer.spec
    set OUTPUT_NAME=%APP_NAME%
)

REM ═══════════════════════════════════════════════════════════
echo.
echo   TwelveToneAnalyzer Build Pipeline
echo   Mode: !MODE! !MODE2!   (debug=!IS_DEBUG! clean=!DO_CLEAN! nsis=!DO_NSIS!)
echo ═══════════════════════════════════════════════════════════
echo.

REM ═══════════════════════════════════════════════════════════
REM Step 1/4 — PyInstaller build
REM ═══════════════════════════════════════════════════════════
echo [1/4] ████░░░░░░ PyInstaller build...

if "%DO_CLEAN%"=="yes" (
    echo        Cleaning old builds...
    if exist "%BUILD_DIR%\%OUTPUT_NAME%" rmdir /s /q "%BUILD_DIR%\%OUTPUT_NAME%" 2>nul
    if exist "%DIST_DIR%\%OUTPUT_NAME%"  rmdir /s /q "%DIST_DIR%\%OUTPUT_NAME%"  2>nul
    %PYTHON% -m PyInstaller --clean "%SPEC_FILE%"
) else (
    if exist "%DIST_DIR%\%OUTPUT_NAME%" rmdir /s /q "%DIST_DIR%\%OUTPUT_NAME%" 2>nul
    %PYTHON% -m PyInstaller "%SPEC_FILE%"
)

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller failed!
    pause & exit /b 1
)
echo        PyInstaller done.

REM ═══════════════════════════════════════════════════════════
REM Step 2/4 — Post-build fixes
REM ═══════════════════════════════════════════════════════════
echo [2/4] ██████░░░░ Post-build fixes...
set QT5_BIN=%VENV%\Lib\site-packages\PyQt5\Qt5\bin
set INTERNAL=%DIST_DIR%\%OUTPUT_NAME%\_internal
if exist "%INTERNAL%\" (
    if exist "%QT5_BIN%\Qt5Core.dll" (
        copy /y "%QT5_BIN%\*.dll" "%INTERNAL%\" >nul 2>&1
    )
    if exist "resources\fix_qt.conf" (
        copy /y "resources\fix_qt.conf" "%INTERNAL%\PyQt5\qt.conf" >nul 2>&1
    )
)
echo        Post-build done.

REM ═══════════════════════════════════════════════════════════
REM Step 3/4 — Pre-build prep (clean + optional zip)
REM ═══════════════════════════════════════════════════════════
if "%DO_NSIS%"=="yes" (
    echo [3/4] ████████░░ Pre-build prep...
    if "%NSIS_RELEASE%"=="yes" (
        %PYTHON% build_prep.py --zip
        if %ERRORLEVEL% neq 0 (
            echo [ERROR] build_prep.py failed!
            pause & exit /b 1
        )
    ) else (
        %PYTHON% build_prep.py
    )
    echo        Pre-build prep done.
)

REM ═══════════════════════════════════════════════════════════
REM Step 4/4 — NSIS installer
REM ═══════════════════════════════════════════════════════════
if "%DO_NSIS%"=="yes" (
    echo [4/4] ██████████ NSIS installer...
    set NSIS_EXE=%LOCALAPPDATA%\Programs\nsis\makensis.exe
    if not exist "!NSIS_EXE!" set NSIS_EXE=.\nsis_portable\nsis-3.10\makensis.exe
    if not exist "!NSIS_EXE!" (
        echo [WARN] NSIS not found, skipping installer
    ) else (
        if "%NSIS_RELEASE%"=="yes" (
            "!NSIS_EXE!" /DRELEASE installer.nsi
        ) else (
            "!NSIS_EXE!" installer.nsi
        )
        if !ERRORLEVEL! neq 0 (
            echo [ERROR] NSIS failed!
            pause & exit /b 1
        )
        for %%f in (TwelveToneAnalyzer_Setup_v*.exe) do (
            echo        Installer: %%f  (!_size! MB^)
        )
    )
)

REM ═══════════════════════════════════════════════════════════
echo.
echo   ============================================
echo     Build Complete!
echo     EXE: %DIST_DIR%\%OUTPUT_NAME%\%OUTPUT_NAME%.exe
if "%DO_NSIS%"=="yes" (
    for %%f in (TwelveToneAnalyzer_Setup_v*.exe) do (
        echo     Setup: %%f
    )
)
echo   ============================================

if "%DO_NSIS%"=="" explorer "%DIST_DIR%"
exit /b 0
