@echo off
chcp 65001 >nul
echo ========================================
echo   TwelveToneAnalyzer - 清理打包缓存
echo ========================================
echo.
echo 即将删除以下目录/文件:
echo   - build\TwelveToneAnalyzer
echo   - dist\TwelveToneAnalyzer
echo   - dist\app.zip
echo   - *.spec (PyInstaller 生成的临时 spec)
echo.
set /p confirm="确认清理? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo 已取消。
    pause
    exit /b
)

echo.
echo 清理中...

if exist "build\TwelveToneAnalyzer" (
    rmdir /s /q "build\TwelveToneAnalyzer"
    echo [OK] 已删除 build\TwelveToneAnalyzer
) else (
    echo [--] build\TwelveToneAnalyzer 不存在
)

if exist "dist\TwelveToneAnalyzer" (
    rmdir /s /q "dist\TwelveToneAnalyzer"
    echo [OK] 已删除 dist\TwelveToneAnalyzer
) else (
    echo [--] dist\TwelveToneAnalyzer 不存在
)

if exist "dist\app.zip" (
    del /q "dist\app.zip"
    echo [OK] 已删除 dist\app.zip
) else (
    echo [--] dist\app.zip 不存在
)

echo.
echo 清理完成！
echo.
pause
