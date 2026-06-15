Unicode true
; ============================================================================
; Twelve-Tone Music Analyzer - NSIS Installer (optimized v2)
;
; Optimizations (2026-06-15):
;   1. RequestExecutionLevel admin
;   2. LZMA solid + 64MB dict
;   3. InstallDir -> D:\
;   4. Exclude Qt dev DLLs, libs, unused translations
;   5. CRCCheck off
;
; Build: makensis -DRELEASE installer.nsi
; ============================================================================
XPStyle on

; (5) Disable per-file CRC verification
CRCCheck off

; (2) LZMA: small dict = fast decompress; zip already handles per-file compression
!ifdef RELEASE
    SetCompressor /SOLID lzma
    SetCompressorDictSize 8
    !define COMPRESS_MODE "Release (solid lzma 8MB dict + zip extract)"
!else
    SetCompressor /SOLID lzma
    SetCompressorDictSize 8
    !define COMPRESS_MODE "Debug (solid lzma 8MB dict)"
!endif

; (1) Admin rights + locked-file retry
RequestExecutionLevel admin
SetOverwrite try

; Definitions
!define PRODUCT "Twelve-Tone Music Analyzer"
!define VERSION "1.3.3"
!define PUBLISHER "Yvonne"
!define EXE_NAME "TwelveToneAnalyzer.exe"
!define ZIP_NAME "app.zip"

Name "${PRODUCT} ${VERSION}"
OutFile "TwelveToneAnalyzer_Setup_v${VERSION}.exe"

; (3) Default install to D:\
InstallDir "D:\${PRODUCT}"
InstallDirRegKey HKLM "Software\${PRODUCT}" "InstallDir"

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

; (4) Install: zip-extract for fast single-pass installation
Section "Install"
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  DetailPrint "Extracting application files..."
  File /oname=$INSTDIR\${ZIP_NAME} "dist\${ZIP_NAME}"
  nsExec::ExecToLog 'powershell -NoProfile -Command "Expand-Archive -Path \"$INSTDIR\${ZIP_NAME}\" -DestinationPath \"$INSTDIR\" -Force"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Extraction failed (code $0).$\nPlease try reinstalling or contact support."
    Abort
  ${EndIf}
  Delete "$INSTDIR\${ZIP_NAME}"

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
