@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM   TwelveToneAnalyzer — 一键打包脚本
REM
REM   【运行前必须激活 .venv 虚拟环境】
REM   若未创建:
REM     python -m venv .venv
REM     .venv\Scripts\activate
REM     pip install -r requirements.txt
REM
REM   【用法】
REM     build.bat         → 发布打包 (文件夹模式, 无控制台)
REM     build.bat debug   → 调试打包 (文件夹模式, 弹出控制台看报错)
REM ============================================================

REM ============================================================
REM  1. 强制锁定项目 .venv 内的 Python/PyInstaller
REM     绝不调用系统全局 Python, 避免版本冲突导致:
REM       "Failed to load Python DLL python39.dll"
REM ============================================================
set VENV=.venv
set PYTHON=%VENV%\Scripts\python.exe
set ENTRY=main.py
set APP_NAME=TwelveToneAnalyzer
set DIST_DIR=dist
set BUILD_DIR=build
set HOOK=pyi_rth_qt_dll.py

REM 检查虚拟环境是否存在
if not exist "%PYTHON%" (
    echo ============================================================
    echo  [ERROR] 未找到虚拟环境 .venv\Scripts\python.exe
    echo  ─────────────────────────────────────────────────────────
    echo  请先在项目根目录执行:
    echo    python -m venv .venv
    echo    .venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo  ─────────────────────────────────────────────────────────
    echo  确认虚拟环境创建成功后，重新运行 build.bat
    echo ============================================================
    pause
    exit /b 1
)
echo [INFO] 虚拟环境: %VENV%
echo [INFO] Python:    %PYTHON%

REM 确保 PyInstaller 安装在 .venv 中, 不污染全局
%PYTHON% -c "import PyInstaller" 2>nul || (
    echo [INFO] 正在安装 PyInstaller 到 .venv...
    %PYTHON% -m pip install pyinstaller -q
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] PyInstaller 安装失败
        pause & exit /b 1
    )
)

REM ============================================================
REM  2. 自动清理所有旧打包缓存
REM     - build\      PyInstaller 编译中间文件
REM     - dist\       上次打包输出
REM     - *.spec      PyInstaller 规格文件
REM     旧缓存可能残留过期 DLL 导致 QtWidgets 加载失败
REM ============================================================
echo [INFO] 清理旧构建缓存...
if exist "%BUILD_DIR%\%APP_NAME%"   rmdir /s /q "%BUILD_DIR%\%APP_NAME%"  2>nul
if exist "%DIST_DIR%\%APP_NAME%"    rmdir /s /q "%DIST_DIR%\%APP_NAME%"   2>nul
if exist "*.spec"                    del /q "*.spec"                       2>nul
echo [INFO] 缓存已清除

REM ============================================================
REM  3. 生成运行时 DLL 搜索钩子
REM     在 PyQt5 导入前注册 Qt5/bin 到 Windows DLL 搜索路径,
REM     修复 "ImportError: DLL load failed while importing QtWidgets"
REM ============================================================
(
    echo import os, sys
    echo # [修复] 在PyQt5导入前注册Qt5/bin到Windows DLL搜索路径
    echo _qt_bin = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'bin')
    echo if os.path.isdir(_qt_bin^):
    echo     try:
    echo         os.add_dll_directory(_qt_bin^)
    echo     except AttributeError:
    echo         os.environ['PATH'] = _qt_bin + os.pathsep + os.environ.get('PATH', ''^)
    echo # [修复] 同时注册 _MEIPASS 根目录 (OpenSSL DLL等)
    echo if sys.platform == 'win32':
    echo     try:
    echo         os.add_dll_directory(sys._MEIPASS^)
    echo     except AttributeError:
    echo         pass
) > "%HOOK%"
echo [INFO] DLL 搜索钩子已生成: %HOOK%

REM ============================================================
REM  4. 判断打包模式
REM ============================================================
set MODE=%1
if "%MODE%"=="debug" (
    REM 调试模式: 不隐藏控制台, 闪退时可看到完整 Python Traceback
    set CONSOLE_FLAG=
    set DEBUG_NAME=_debug
    echo [MODE] 调试打包 (弹出控制台, 可查看报错)
) else (
    REM 发布模式: -w 隐藏控制台窗口, GUI 程序无黑框
    set CONSOLE_FLAG=-w
    set DEBUG_NAME=
    echo [MODE] 发布打包 (无控制台, 文件夹模式)
)

echo ============================================================
echo   开始打包 %APP_NAME%.exe ...
echo ============================================================

REM ============================================================
REM  5. 执行 PyInstaller 打包
REM     -D                  → 文件夹打包, 不使用 -F 单文件
REM                           (单文件每次解压到 temp, Python DLL 可能丢失)
REM     -w                  → 隐藏控制台 (debug模式不传此参数)
REM     --runtime-hook      → 启动前执行 DLL 路径注册
REM     --collect-all       → 收集整个包 (模块 + 数据 + 二进制)
REM     --collect-binaries  → 额外强制收集所有 .dll/.pyd 二进制文件
REM     --hidden-import     → 强制打包隐式/延迟导入模块
REM ============================================================

REM ============ PyQt5: 收集全部模块+Qt5全部DLL ============
REM ======== music21: 全量收集(曲库/MEI/MIDI/MusicXML/lilypond) ========
REM ======== matplotlib: Qt绘图后端 + 十二音矩阵弹窗 ========
REM ======== numpy / scipy ========
REM ======== 音频处理 (audio_tab) ========
REM ======== assets静态资源 (若有) ========

%PYTHON% -m PyInstaller ^
    -D ^
    %CONSOLE_FLAG% ^
    -n %APP_NAME%%DEBUG_NAME% ^
    --runtime-hook %HOOK% ^
    --collect-all PyQt5 ^
    --collect-binaries PyQt5 ^
    --hidden-import PyQt5.sip ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    --collect-all music21 ^
    --hidden-import music21.corpus.corpora ^
    --hidden-import music21.converter.subConverters ^
    --hidden-import music21.mei ^
    --hidden-import music21.mei.base ^
    --hidden-import music21.mei.translate ^
    --hidden-import music21.midi ^
    --hidden-import music21.midi.translate ^
    --hidden-import music21.musicxml ^
    --hidden-import music21.musicxml.xmlToM21 ^
    --hidden-import music21.musicxml.m21ToXml ^
    --hidden-import music21.graph ^
    --hidden-import music21.graph.plot ^
    --hidden-import music21.graph.utilities ^
    --hidden-import music21.lily ^
    --hidden-import music21.lily.translate ^
    --hidden-import music21.stream ^
    --hidden-import music21.note ^
    --hidden-import music21.chord ^
    --hidden-import music21.serial ^
    --hidden-import music21.metadata ^
    --hidden-import music21.converter ^
    --hidden-import music21.interval ^
    --hidden-import music21.pitch ^
    --hidden-import music21.analysis ^
    --hidden-import music21.analysis.discrete ^
    --hidden-import music21.ext ^
    --hidden-import matplotlib ^
    --hidden-import matplotlib.backends.backend_qt5agg ^
    --hidden-import matplotlib.backends.backend_qtagg ^
    --hidden-import matplotlib.backends.backend_template ^
    --hidden-import matplotlib.pyplot ^
    --hidden-import matplotlib.figure ^
    --hidden-import matplotlib.patches ^
    --hidden-import matplotlib.lines ^
    --hidden-import matplotlib.text ^
    --hidden-import matplotlib.ticker ^
    --hidden-import matplotlib.colors ^
    --hidden-import matplotlib.cm ^
    --hidden-import numpy ^
    --hidden-import numpy.core ^
    --hidden-import scipy ^
    --hidden-import scipy.interpolate ^
    --hidden-import scipy.signal ^
    --hidden-import scipy.sparse ^
    --hidden-import librosa ^
    --hidden-import soundfile ^
    --hidden-import audioread ^
    --hidden-import resampy ^
    --hidden-import numba ^
    --add-data "assets;assets" ^
    --clean ^
    %ENTRY%

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo  [ERROR] 打包失败! 请检查上方报错信息。
    echo ============================================================
    pause
    exit /b 1
)

REM ============================================================
REM  6. 打包后: 复制 Qt5 DLL 到 _internal 根目录 (双重保障)
REM     部分 Windows 版本 DLL 搜索不递归子目录,
REM     将 Qt5/bin 下全部 DLL 复制到 _internal 根确保可见
REM ============================================================
set QT5_BIN=%VENV%\Lib\site-packages\PyQt5\Qt5\bin
set INTERNAL=%DIST_DIR%\%APP_NAME%%DEBUG_NAME%\_internal
if exist "%INTERNAL%\" (
    if exist "%QT5_BIN%\Qt5Core.dll" (
        echo [INFO] 复制 Qt5 DLL 到 _internal 根目录 (双重保障)...
        copy /y "%QT5_BIN%\*.dll" "%INTERNAL%\" >nul 2>&1
        echo [INFO] 完成
    )
    REM 修复 qt.conf — PyPI wheel 自带的 qt.conf 有硬编码的 C:/Python27/ 路径,
    REM 导致打包后 Qt 在用户机器上找不到插件和二进制文件
    if exist "resources\fix_qt.conf" (
        echo [INFO] 修复 qt.conf (替换硬编码路径)...
        copy /y "resources\fix_qt.conf" "%INTERNAL%\PyQt5\qt.conf" >nul 2>&1
        echo [INFO] qt.conf 已修复
    )
)

REM ============================================================
echo.
echo ============================================================
echo                       打包完成!
echo ============================================================
echo.
echo  【exe 启动路径】
echo    %DIST_DIR%\%APP_NAME%%DEBUG_NAME%\%APP_NAME%%DEBUG_NAME%.exe
echo.
echo  【分发方式】
echo    将整个 "%APP_NAME%%DEBUG_NAME%" 文件夹打包为 .zip
echo    用户解压后双击文件夹内 exe 即可运行
echo.
echo  【资源路径适配】
echo    已在 src\utils\config.py 中添加 resource_path()
echo    用法: from src.utils.config import resource_path
echo          path = resource_path("assets/icon.png")
echo    打包/开发环境自动切换 sys._MEIPASS / 项目根目录
echo.
echo  ============================================================
echo  【操作步骤】
echo  ============================================================
echo   1. 确保 .venv 虚拟环境已创建并激活
echo      python -m venv .venv
echo      .venv\Scripts\activate
echo      pip install -r requirements.txt
echo.
echo   2. 双击 build.bat (正常发布) 或 build.bat debug (调试)
echo      打包时间约 2-5 分钟, 请耐心等待
echo.
echo   3. 打包完成后自动打开 dist\ 文件夹
echo      进入 %APP_NAME%%DEBUG_NAME%\ 双击 exe 测试
echo.
echo   4. 若 exe 闪退:
echo      - 运行 build.bat debug 打包调试版
echo      - 双击 debug 版 exe, 控制台会显示完整报错
echo      - 根据报错补 --hidden-import 或检查缺 DLL
echo.
echo  【故障速查】
echo   "DLL load failed while importing QtWidgets"
echo     → --collect-binaries PyQt5 已修复
echo     → 确认目标机器安装了 VC++ Redistributable x64
echo.
echo   "Failed to load Python DLL python39.dll"
echo     → -D 文件夹模式已修复 (不用 -F 单文件)
echo     → 检查杀毒软件是否拦截隔离了 DLL
echo.
echo   "No module named 'music21.xxx'"
echo     → 根据报错名称补充 --hidden-import music21.xxx
echo     → 重新运行 build.bat
echo.
echo   乐谱解析失败 / 绘图窗口不弹出
echo     → 已包含 music21 MEI/MIDI/MusicXML/graph 全部 hidden-import
echo     → 已包含 matplotlib Qt5Agg 后端
echo ============================================================

REM 7. 自动打开 dist 输出文件夹
explorer "%DIST_DIR%"
pause
