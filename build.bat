@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM   TwelveToneAnalyzer — Build Script
REM
REM   Optimized: uses .spec files instead of raw CLI flags.
REM   All PyInstaller configuration is now in:
REM     - TwelveToneAnalyzer.spec        (release)
REM     - TwelveToneAnalyzer_debug.spec  (debug)
REM
REM   【用法】
REM     build.bat         → 发布打包 (文件夹模式, 无控制台)
REM     build.bat debug   → 调试打包 (文件夹模式, 弹出控制台)
REM ============================================================

REM ============================================================
REM  1. Force use of project .venv Python/PyInstaller
REM ============================================================
set VENV=.venv
set PYTHON=%VENV%\Scripts\python.exe
set APP_NAME=TwelveToneAnalyzer
set DIST_DIR=dist

if not exist "%PYTHON%" (
    echo ============================================================
    echo  [ERROR] Virtual environment not found: .venv\Scripts\python.exe
    echo  ─────────────────────────────────────────────────────────
    echo  Please run the following commands in the project root:
    echo    python -m venv .venv
    echo    .venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo  ─────────────────────────────────────────────────────────
    echo  Then re-run build.bat
    echo ============================================================
    pause
    exit /b 1
)
echo [INFO] Virtual env: %VENV%
echo [INFO] Python:      %PYTHON%

REM Ensure PyInstaller is installed in .venv
%PYTHON% -c "import PyInstaller" 2>nul || (
    echo [INFO] Installing PyInstaller to .venv...
    %PYTHON% -m pip install pyinstaller -q
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to install PyInstaller
        pause & exit /b 1
    )
)

REM ============================================================
REM  2. Select build mode
REM ============================================================
set MODE=%1
if /i "%MODE%"=="debug" (
    set SPEC_FILE=TwelveToneAnalyzer_debug.spec
    set OUTPUT_NAME=%APP_NAME%_debug
    echo [MODE] Debug build (console visible, traceback shown)
) else (
    set SPEC_FILE=TwelveToneAnalyzer.spec
    set OUTPUT_NAME=%APP_NAME%
    echo [MODE] Release build (no console, folder mode)
)

REM ============================================================
REM  3. Clean old build artifacts
REM ============================================================
echo [INFO] Cleaning old build cache...
set BUILD_DIR=build
if exist "%BUILD_DIR%\%OUTPUT_NAME%"   rmdir /s /q "%BUILD_DIR%\%OUTPUT_NAME%"   2>nul
if exist "%DIST_DIR%\%OUTPUT_NAME%"    rmdir /s /q "%DIST_DIR%\%OUTPUT_NAME%"    2>nul
echo [INFO] Cache cleaned

REM ============================================================
REM  4. Verify runtime hooks exist
REM ============================================================
if not exist "pyi_rth_qt_dll.py" (
    echo [WARN] pyi_rth_qt_dll.py not found - build may fail
)
if not exist "pyi_rth_music21.py" (
    echo [WARN] pyi_rth_music21.py not found - music21 corpus may break
)

REM ============================================================
REM  5. PyInstaller build via .spec file
REM    All hidden-import, collect-all, and DLL rules are
REM    defined in the .spec files — no CLI duplication needed.
REM ============================================================
echo ============================================================
echo   Building %OUTPUT_NAME%.exe ...
echo ============================================================

%PYTHON% -m PyInstaller --clean "%SPEC_FILE%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo  [ERROR] Build failed! Check the output above.
    echo ============================================================
    pause
    exit /b 1
)

REM ============================================================
REM  6. Post-build: copy Qt5 DLLs to _internal root
REM     (belt-and-suspenders for DLL search path on Windows)
REM ============================================================
set QT5_BIN=%VENV%\Lib\site-packages\PyQt5\Qt5\bin
set INTERNAL=%DIST_DIR%\%OUTPUT_NAME%\_internal
if exist "%INTERNAL%\" (
    if exist "%QT5_BIN%\Qt5Core.dll" (
        echo [INFO] Copying Qt5 DLLs to _internal root...
        copy /y "%QT5_BIN%\*.dll" "%INTERNAL%\" >nul 2>&1
        echo [INFO] Done
    )
    if exist "resources\fix_qt.conf" (
        echo [INFO] Patching qt.conf...
        copy /y "resources\fix_qt.conf" "%INTERNAL%\PyQt5\qt.conf" >nul 2>&1
        echo [INFO] qt.conf patched
    )
)

REM ============================================================
echo.
echo ============================================================
echo                       Build Complete!
echo ============================================================
echo.
echo   EXE:  %DIST_DIR%\%OUTPUT_NAME%\%OUTPUT_NAME%.exe
echo.
echo   Distribute: zip the "%OUTPUT_NAME%" folder
echo   User runs:  extract → double-click %OUTPUT_NAME%.exe
echo.
echo ============================================================
echo   Troubleshooting
echo ============================================================
echo   "DLL load failed"
echo     → Check VC++ Redistributable x64 is installed
echo.
echo   "No module named 'xxx'"
echo     → Add to hiddenimports in %SPEC_FILE%
echo     → Re-run build.bat
echo.
echo   EXE crashes silently
echo     → Run: build.bat debug
echo     → Launch debug EXE to see Python traceback
echo ============================================================

REM Open dist folder
explorer "%DIST_DIR%"
pause
