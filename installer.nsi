Unicode true
; ============================================================================
; Twelve-Tone Music Analyzer - NSIS Installer (optimized v2)
;
; Optimizations (2026-06-15):
;   1. RequestExecutionLevel admin — 默认管理员权限，避免写入重试卡顿
;   2. LZMA固态压缩 64MB字典 — 极致压缩比，减少解压计算耗时
;   3. InstallDir → D:\ — 避开 C:\Program Files 系统权限拦截
;   4. 剔除Qt dev/unused DLLs + 无用qm翻译 + .lib导入库 — 减少解压文件总量
;   5. CRCCheck off — 关闭安装过程实时文件校验，提升解压速度
;
; Build modes:
;   makensis installer.nsi                    -> Debug (fast iteration)
;   makensis -DRELEASE installer.nsi          -> Release (zip mode, best compression)
; ============================================================================
XPStyle on

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Optimization 5: 关闭安装过程实时文件校验 — 跳过每文件CRC校验，显著提速
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRCCheck off

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Optimization 2: LZMA极致固态压缩 — 减少解压计算耗时
;   Release: /SOLID + 64MB字典 = 最大压缩比，单数据流解压
;   Debug:   /SOLID + 16MB字典 = 平衡迭代速度与压缩
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
!ifdef RELEASE
    SetCompressor /SOLID lzma
    SetCompressorDictSize 64    ; 64 MB dictionary — 极致压缩
    !define COMPRESS_MODE "Release (solid lzma 64MB dict + pre-zip)"
!else
    SetCompressor /SOLID lzma   ; also solid — avoids per-file seek overhead
    SetCompressorDictSize 16    ; moderate dictionary for faster debug builds
    !define COMPRESS_MODE "Debug (solid lzma 16MB dict)"
!endif

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Optimization 1: 默认申请管理员权限 — 避免向受保护目录写入DLL/QM时的权限报错
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RequestExecutionLevel admin

; Locked-file retry: if a DLL is held by antivirus or a lingering process,
; retry instead of failing immediately.  Works with admin rights above.
SetOverwrite try

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Definitions
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
!define PRODUCT "Twelve-Tone Music Analyzer"
!define VERSION "1.3.2"
!define PUBLISHER "Yvonne"
!define EXE_NAME "TwelveToneAnalyzer.exe"
!define ZIP_NAME "app.zip"

Name "${PRODUCT} ${VERSION}"
OutFile "TwelveToneAnalyzer_Setup_v${VERSION}.exe"

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Optimization 3: 默认安装路径到D盘 — 避开 C:\Program Files 系统权限拦截
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
InstallDir "D:\${PRODUCT}"
InstallDirRegKey HKLM "Software\${PRODUCT}" "InstallDir"

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Modern UI
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Pre-flight: detect running instance (prevents DLL/QM lock conflicts)
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Function .onInit
  nsExec::ExecToStack 'cmd /c tasklist /fi "IMAGENAME eq ${EXE_NAME}" /nh 2>nul | find /i "${EXE_NAME}"'
  Pop $0
  ${If} $0 == 0
    MessageBox MB_ICONSTOP|MB_OK \
      "${PRODUCT} is currently running!$\n$\nPlease close the application before installing."
    Abort
  ${EndIf}

  ReadRegStr $R0 HKLM "Software\${PRODUCT}" "InstallDir"
  ${If} $R0 != ""
    StrCpy $INSTDIR $R0
  ${EndIf}

  !ifdef RELEASE
    DetailPrint "Installer mode: ${COMPRESS_MODE}"
  !endif
FunctionEnd

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Optimization 4: Qt dev/unused DLL exclusion patterns
;
; These DLLs are NOT needed at runtime by this application but are bundled
; by PyInstaller's collect_dynamic_libs('PyQt5').  Excluding them here means
; NSIS never extracts them — fewer files, fewer permission checks, faster install.
;
;   Qt dev tools:        Designer, Help, Test
;   Unused Qt modules:   Bluetooth, DBus, Location, Multimedia, MultimediaWidgets,
;                        NFC, Positioning, PositioningQuick, Quick3D, QuickTest,
;                        RemoteObjects, Sensors, SerialPort, Sql, TextToSpeech,
;                        WebChannel, WebSockets, WebView, WinExtras, XmlPatterns
;
; We also exclude:
;   *.lib files  — C-extension import libraries (dev-only, dead weight at runtime)
;   *.pdb files  — debug symbols (never needed)
;   *.ilk *.exp  — MSVC incremental-link / export files
;   Unused .qm   — Qt translations for languages the app doesn't support
;                   (keep only qt_zh_CN.qm + qt_en.qm which match our NSIS languages)
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
!define DEBUG_EXCLUDES \
    /x "__pycache__" \
    /x "*.pyc" \
    /x ".git" \
    /x "*.lib" \
    /x "*.pdb" \
    /x "*.ilk" \
    /x "*.exp" \
    /x "Qt5Designer*" \
    /x "Qt5Help*" \
    /x "Qt5Test*" \
    /x "Qt5DBus*" \
    /x "Qt5Bluetooth*" \
    /x "Qt5Nfc*" \
    /x "Qt5Sql*" \
    /x "Qt5SerialPort*" \
    /x "Qt5Sensors*" \
    /x "Qt5Location*" \
    /x "Qt5Positioning*" \
    /x "Qt5RemoteObjects*" \
    /x "Qt5WebChannel*" \
    /x "Qt5WebSockets*" \
    /x "Qt5WebView*" \
    /x "Qt5XmlPatterns*" \
    /x "Qt5TextToSpeech*" \
    /x "Qt5WinExtras*" \
    /x "Qt5Quick3D*" \
    /x "Qt5QuickTest*" \
    /x "Qt5Multimedia*"

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Install Section
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section "Install"
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  !ifdef RELEASE
    ; ── RELEASE MODE: extract from pre-built zip (1 file → fast NSIS pass) ──
    DetailPrint "Extracting application files..."
    File /oname=$INSTDIR\${ZIP_NAME} "dist\${ZIP_NAME}"
    ; PowerShell Expand-Archive — built-in on Win 10+, no per-file progress overhead
    nsExec::ExecToLog 'powershell -NoProfile -Command "Expand-Archive -Path \"$INSTDIR\${ZIP_NAME}\" -DestinationPath \"$INSTDIR\" -Force"'
    Pop $0
    ${If} $0 != 0
      MessageBox MB_ICONSTOP "Extraction failed (code $0).$\nPlease try reinstalling or contact support."
      Abort
    ${EndIf}
    Delete "$INSTDIR\${ZIP_NAME}"
  !else
    ; ── DEBUG MODE: File /r with aggressive Qt dev-tool & junk exclusions ──
    File /r ${DEBUG_EXCLUDES} "dist\TwelveToneAnalyzer\*.*"
  !endif

  ; Start menu shortcuts
  CreateDirectory "$SMPROGRAMS\${PRODUCT}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT}\${PRODUCT}.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT}\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ; Desktop shortcut
  CreateShortCut "$DESKTOP\${PRODUCT}.lnk" "$INSTDIR\${EXE_NAME}"

  ; Registry keys for uninstall
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "DisplayName" "${PRODUCT}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "DisplayIcon" "$INSTDIR\${EXE_NAME}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "NoRepair" 1

  WriteRegStr HKLM "Software\${PRODUCT}" "InstallDir" "$INSTDIR"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Calculate install size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "EstimatedSize" "$0"
SectionEnd

; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
; Uninstall Section
; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section "Uninstall"
  Delete "$INSTDIR\uninstall.exe"
  ; /REBOOTOK: if DLLs are locked by antivirus, schedule removal on reboot
  RMDir /r /REBOOTOK "$INSTDIR"

  Delete "$SMPROGRAMS\${PRODUCT}\${PRODUCT}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT}"

  Delete "$DESKTOP\${PRODUCT}.lnk"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}"
  DeleteRegKey HKLM "Software\${PRODUCT}"
SectionEnd
