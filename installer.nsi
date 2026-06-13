; ============================================================================
; Twelve-Tone Music Analyzer Installer Script
; Usage: makensis.exe installer.nsi
; ============================================================================

Unicode true
SetCompressor /SOLID lzma
XPStyle on

; ---------------------------------------------------------------------------
; [Mod 1] RequestExecutionLevel admin
; Force UAC elevation prompt at startup - fixes "unable to write qtxxx.dll"
; ---------------------------------------------------------------------------
RequestExecutionLevel admin

; ---------------------------------------------------------------------------
; Definitions
; ---------------------------------------------------------------------------
!define PRODUCT "Twelve-Tone Music Analyzer"
!define VERSION "1.2"
!define PUBLISHER "Yvonne"
!define EXE_NAME "TwelveToneAnalyzer.exe"

Name "${PRODUCT} ${VERSION}"
OutFile "TwelveToneAnalyzer_Setup_v${VERSION}.exe"

; ---------------------------------------------------------------------------
; [Mod 2] Default install path changed to D:\ to avoid C:\Program Files
; permission restrictions that cause "unable to write qtxxx.dll/qtxxx.qm"
; Old: InstallDir "$PROGRAMFILES64\${PRODUCT}"
; ---------------------------------------------------------------------------
InstallDir "D:\${PRODUCT}"
InstallDirRegKey HKLM "Software\${PRODUCT}" "InstallDir"

; ---------------------------------------------------------------------------
; Modern UI
; ---------------------------------------------------------------------------
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstall pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; ============================================================================
; [Mod 3] Pre-flight check: detect if TwelveToneAnalyzer.exe is running
; If running, show warning and abort - prevents "unable to write" errors
; caused by locked qtxxx.dll / qtxxx.qm files
; ============================================================================
Function .onInit
  ; --- Check if the app is already running ---
  nsExec::ExecToStack 'cmd /c tasklist /fi "IMAGENAME eq ${EXE_NAME}" /nh 2>nul | find /i "${EXE_NAME}"'
  Pop $0   ; find exit code: 0=found, 1=not found
  ${If} $0 == 0
    MessageBox MB_ICONSTOP|MB_OK \
      "${PRODUCT} is currently running!$\n$\nPlease close the application before installing.$\n$\nMethod: Right-click taskbar icon > Close window, or end ${EXE_NAME} in Task Manager."
    Abort
  ${EndIf}

  ; --- Check if already installed (read registry) ---
  ReadRegStr $R0 HKLM "Software\${PRODUCT}" "InstallDir"
  ${If} $R0 != ""
    StrCpy $INSTDIR $R0
  ${EndIf}
FunctionEnd

; ============================================================================
; Install Section
; ============================================================================
Section "Install"
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  ; Copy all files from dist\TwelveToneAnalyzer directory
  File /r "dist\TwelveToneAnalyzer\*.*"

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

  ; Store install path for upgrades
  WriteRegStr HKLM "Software\${PRODUCT}" "InstallDir" "$INSTDIR"

  ; Generate uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Calculate install size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" \
    "EstimatedSize" "$0"
SectionEnd

; ============================================================================
; Uninstall Section
; ============================================================================
Section "Uninstall"
  Delete "$INSTDIR\uninstall.exe"
  RMDir /r "$INSTDIR"

  Delete "$SMPROGRAMS\${PRODUCT}\${PRODUCT}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT}"

  Delete "$DESKTOP\${PRODUCT}.lnk"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}"
  DeleteRegKey HKLM "Software\${PRODUCT}"
SectionEnd
