# TwelveToneAnalyzer — DMG 打包发布流程

## 前置检查清单

打包前逐项确认：

1. **代码无 bug** — 已修复已知问题，源码可正常运行
2. **i18n 键完整** — 中英文翻译均已添加
3. **Git 工作区干净** — 所有改动已 commit

---

## ⚠️ 打包前必须询问用户

> **每项都要等用户明确答复后再执行，不要跳过。**

### 1. 确认是否打包
> 准备构建 DMG，是否继续？

### 2. 确认版本号
> 当前版本 `x.x.x`，是否需要升级版本号？如需要请告诉新版本号。

**版本号涉及以下文件：**

| 文件 | 位置 |
|------|------|
| `src/core/updater.py` | `VERSION = "x.x.x"` |
| `build_mac.sh` | `DMG_NAME="..._vx.x.x"` |
| `TwelveToneAnalyzer_mac.spec` | `CFBundleShortVersionString` / `CFBundleVersion` |
| `src/utils/i18n.py` | 关于对话框中的版本文字 |
| `installer.nsi` | `!define VERSION "x.x.x"` |

### 3. 确认是否需要更新 Release Notes
> `release_notes.md` 是否需要更新？

---

## 构建步骤

```bash
# 1. 激活虚拟环境
cd /path/to/TwelveToneAnalyzer
source .venv_mac/bin/activate

# 2. 清理旧构建
rm -rf build/ dist/

# 3. PyInstaller 构建 .app
pyinstaller TwelveToneAnalyzer_mac.spec

# 4. 打包 DMG
DMG_DIR="dist/dmg_staging"
mkdir -p "$DMG_DIR"
cp -R "dist/TwelveToneAnalyzer.app" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"
hdiutil create -volname "TwelveToneAnalyzer" \
    -srcfolder "$DMG_DIR" -ov -format UDZO \
    "dist/TwelveToneAnalyzer_Setup_vx.x.x.dmg"
rm -rf "$DMG_DIR"

# 5. 安装测试
rm -rf /Applications/TwelveToneAnalyzer.app
cp -R dist/TwelveToneAnalyzer.app /Applications/
open /Applications/TwelveToneAnalyzer.app
```

---

## 发布到 GitHub

```bash
# 创建 Release 并上传 DMG
gh release create vx.x.x \
  --repo Yvonne6475/TwelveToneAnalyzer \
  --title "TwelveToneAnalyzer vx.x.x" \
  --notes "$(cat release_notes.md)" \
  "dist/TwelveToneAnalyzer_Setup_vx.x.x.dmg"

# 提交版本变更并推送
git add .
git commit -m "release: vx.x.x"
git push origin master
```

---

## 常见构建问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `NameError: name 'serial' is not defined` | PyInstaller 未正确包含 `music21.serial` | 在 `.spec` 的 hiddenimports 中显式添加 `'music21.serial'`，并将 `create_12tone_matrix` 中的 import 改为函数内延迟导入 |
| codesign 警告 | 开发构建未签名 | 可忽略，不影响运行 |
| 矩阵列对齐错位 | QTextEdit CSS font-family 不可靠 | 用程序化 `QFont` + `setDefaultFont` 替代 CSS |
