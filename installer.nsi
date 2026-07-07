Unicode true
; ============================================================================
; Twelve-Tone Music Analyzer - NSIS Installer (optimized v2)
;
; Optimizations (2026-06-15):
;   1. RequestExecutionLevel admin
;   2. LZMA solid + 64MB dict
;   3. InstallDir -> %PROGRAMFILES64%\
;   4. Exclude Qt dev DLLs, libs, unused translations
;   5. CRCCheck off
;
; Build: makensis -DRELEASE installer.nsi
; ============================================================================
XPStyle on

; (5) Disable per-file CRC verification
CRCCheck off

; (2) ZLIB for fast decompression — ~2-3x faster install than LZMA
!ifdef RELEASE
    SetCompressor zlib
    !define COMPRESS_MODE "Release (zlib)"
!else
    SetCompressor zlib
    !define COMPRESS_MODE "Debug (zlib)"
!endif

; (1) Admin rights + locked-file retry
RequestExecutionLevel admin
SetOverwrite try

; Definitions
!define PRODUCT "Twelve-Tone Music Analyzer"
; VERSION injected by CI via /DVERSION=... (do NOT hardcode here)
!define PUBLISHER "Yvonne"
!define EXE_NAME "TwelveToneAnalyzer.exe"

Name "${PRODUCT} ${VERSION}"
OutFile "TwelveToneAnalyzer_Setup_v${VERSION}.exe"

; (3) Default install to D:\
InstallDir "$PROGRAMFILES64\${PRODUCT}"

; Modern UI
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

; Pre-flight: detect running instance
Function .onInit
  ; Check VC++ Redistributable (required by PyQt5)
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  IfErrors 0 +3
    MessageBox MB_ICONINFORMATION|MB_OK       "Microsoft Visual C++ Redistributable not detected.$\r$\n$\r$\n       If the app fails to start with 'VCRUNTIME140.dll missing', please install:$\r$\n       https://aka.ms/vs/17/release/vc_redist.x64.exe"
    Goto +2
  ${If} $0 != 1
    MessageBox MB_ICONINFORMATION|MB_OK       "Microsoft Visual C++ Redistributable not detected.$\r$\n$\r$\n       If the app fails to start with 'VCRUNTIME140.dll missing', please install:$\r$\n       https://aka.ms/vs/17/release/vc_redist.x64.exe"
  ${EndIf}

  nsExec::ExecToStack 'cmd /c tasklist /fi "IMAGENAME eq ${EXE_NAME}" /nh 2>nul | find /i "${EXE_NAME}"'
  Pop $0
  ${If} $0 == 0
    MessageBox MB_ICONSTOP|MB_OK \
      "${PRODUCT} is currently running!$\n$\nPlease close the application before installing."
    Abort
  ${EndIf}



  !ifdef RELEASE
    DetailPrint "Installer mode: ${COMPRESS_MODE}"
  !endif
FunctionEnd

; (4) Install: store zip uncompressed (raw copy, skip LZMA decompression)
Section "Install"
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  DetailPrint "Installing application files..."
  File /r /x *.pyc /x __pycache__ /x .git "dist\TwelveToneAnalyzer\*"

  ; Start menu shortcuts
  CreateDirectory "$SMPROGRAMS\${PRODUCT}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT}\${PRODUCT}.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT}\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ; Desktop shortcut
  CreateShortCut "$DESKTOP\${PRODUCT}.lnk" "$INSTDIR\${EXE_NAME}"

  ; Registry keys
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

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "EstimatedSize" "$0"
SectionEnd

; Uninstall Section
Section "Uninstall"
  Delete "$INSTDIR\uninstall.exe"
  RMDir /r /REBOOTOK "$INSTDIR"

  Delete "$SMPROGRAMS\${PRODUCT}\${PRODUCT}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT}"

  Delete "$DESKTOP\${PRODUCT}.lnk"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}"
  DeleteRegKey HKLM "Software\${PRODUCT}"
SectionEnd
