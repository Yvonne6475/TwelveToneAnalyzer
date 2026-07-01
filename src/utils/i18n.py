"""Simple internationalization (i18n) module with Chinese/English support."""

from PyQt5.QtCore import QObject, pyqtSignal

# ---- Translation tables ----
# Key → { 'zh': ..., 'en': ... }

TRANSLATIONS = {
    # App
    "app.title": {"zh": "十二音音乐分析软件 — Twelve-Tone Music Analyzer", "en": "Twelve-Tone Music Analyzer"},

    # Menu - File
    "menu.file": {"zh": "文件(&F)", "en": "&File"},
    "menu.file.open": {"zh": "打开乐谱...", "en": "Open Score..."},
    "menu.file.open_url": {"zh": "从 URL 加载...", "en": "Load from URL..."},
    "menu.file.open_github": {"zh": "从 GitHub 加载示例...", "en": "Load Samples from GitHub..."},
    "menu.file.open_corpus": {"zh": "从 music21 曲库加载...", "en": "Load from music21 Corpus..."},
    "menu.file.open_audio": {"zh": "打开音频文件...", "en": "Open Audio File..."},
    "menu.file.exit": {"zh": "退出(&X)", "en": "E&xit"},

    # Menu - Settings
    "menu.settings": {"zh": "设置(&S)", "en": "&Settings"},
    "menu.settings.prefs": {"zh": "首选项...", "en": "Preferences..."},
    "menu.settings.language": {"zh": "语言", "en": "Language"},

    # Menu - Export
    "menu.export": {"zh": "导出(&E)", "en": "&Export"},
    "menu.export.annotated": {"zh": "导出带标注的乐谱...", "en": "Export Annotated Score..."},
    "menu.export.report": {"zh": "导出分析报告 (Markdown)...", "en": "Export Analysis Report (Markdown)..."},

    # Menu - Help
    "menu.tools": {"zh": "工具(&T)", "en": "&Tools"},
    "menu.tools.forte_name": {"zh": "Forte 音级集合分析...", "en": "Forte Set-Class Analysis..."},
    "menu.help": {"zh": "帮助(&H)", "en": "&Help"},
    "menu.help.about": {"zh": "关于...", "en": "About..."},

    # Tabs
    "tab.overview": {"zh": "总览", "en": "Overview"},
    "tab.visualization": {"zh": "音高可视化", "en": "Pitch Visualization"},
    "tab.twelve_tone": {"zh": "十二音序列分析", "en": "Twelve-Tone Row Analysis"},
    "tab.chord": {"zh": "和弦分析", "en": "Chords Analysis"},
    "tab.audio": {"zh": "音频分析", "en": "Audio Analysis"},

    # Status bar
    "status.musescore.ready": {"zh": "MuseScore 4 已就绪", "en": "MuseScore 4 Ready"},
    "status.musescore.not_configured": {"zh": "MuseScore 4 未配置", "en": "MuseScore 4 Not Configured"},
    "status.score_loaded": {"zh": "已加载: {name}  (共 {measures} 小节)", "en": "Loaded: {name} ({measures} measures)"},
    "status.audio_loaded": {"zh": "已加载音频: {name}", "en": "Audio loaded: {name}"},
    "status.loading_score": {"zh": "正在加载乐谱...", "en": "Loading score..."},
    "status.downloading": {"zh": "正在下载乐谱...", "en": "Downloading score..."},
    "status.downloading_github": {"zh": "正在从 GitHub 下载...", "en": "Downloading from GitHub..."},

    # Dialogs - file
    "dialog.open_score": {"zh": "打开乐谱文件", "en": "Open Score File"},
    "dialog.open_score_filter": {"zh": "Music Files (*.musicxml *.xml *.mxl *.midi *.mid *.mei *.abc *.krn);;All Files (*)", "en": "Music Files (*.musicxml *.xml *.mxl *.midi *.mid *.mei *.abc *.krn);;All Files (*)"},
    "dialog.open_audio": {"zh": "打开音频文件", "en": "Open Audio File"},
    "dialog.open_audio_filter": {"zh": "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)", "en": "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)"},
    "dialog.load_failed": {"zh": "加载失败", "en": "Load Failed"},
    "dialog.download_failed": {"zh": "下载失败", "en": "Download Failed"},
    "dialog.no_score": {"zh": "无乐谱", "en": "No Score"},
    "dialog.no_score_msg": {"zh": "请先加载乐谱文件。", "en": "Please load a score file first."},
    "dialog.url_prompt": {"zh": "从 URL 加载", "en": "Load from URL"},
    "dialog.url_label": {"zh": "输入乐谱文件的 URL (MusicXML/MIDI/MEI/ABC/KRN):", "en": "Enter URL of score file (MusicXML/MIDI/MEI/ABC/KRN):"},
    "dialog.url_placeholder": {"zh": "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/...", "en": "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/..."},
    "dialog.save_download_as": {"zh": "保存下载的乐谱为", "en": "Save Downloaded Score As"},
    "dialog.corpus_library_link": {"zh": "打开软件作者曲库 (GitHub)", "en": "Open Author's Corpus Library (GitHub)"},
    "dialog.corpus_prompt": {"zh": "从 music21 曲库选择", "en": "Select from music21 Corpus"},
    "dialog.corpus_label": {"zh": "输入作品名称:", "en": "Enter work name:"},
    "dialog.corpus_browse": {"zh": "浏览曲库参考", "en": "Browse Corpus Reference"},
    "dialog.github_prompt": {"zh": "从 GitHub 加载示例", "en": "Load Sample from GitHub"},
    "dialog.github_label": {"zh": "输入 GitHub raw URL:", "en": "Enter GitHub raw URL:"},

    # Dialogs - export
    "dialog.export_report": {"zh": "导出报告", "en": "Export Report"},
    "dialog.export_report_msg": {"zh": "请在'和弦分析'选项卡中提取和弦后导出 Markdown 报告。", "en": "Please extract chords in the 'Chord Analysis' tab first, then export the Markdown report."},
    "dialog.export_complete": {"zh": "导出完成", "en": "Export Complete"},
    "dialog.saved_to": {"zh": "已保存至:\n{path}", "en": "Saved to:\n{path}"},

    # Forte Name Dialog
    "forte.title": {"zh": "Forte 音级集合分析", "en": "Forte Set-Class Analysis"},
    "forte.input_label": {"zh": "输入音级集合 (每行一组，空格分隔):", "en": "Input Pitch-Class Sets (one per line, space-separated):"},
    "forte.btn_analyze": {"zh": "分析", "en": "Analyze"},
    "forte.btn_copy": {"zh": "复制结果", "en": "Copy Results"},
    "forte.btn_export_csv": {"zh": "导出 CSV", "en": "Export CSV"},
    "forte.btn_from_chord": {"zh": "从和弦分析获取", "en": "Get from Chords Analysis"},
    "forte.no_chord_msg": {"zh": "请先在和弦分析标签页中提取和弦。", "en": "Please extract chords first in the Chords Analysis tab."},
    "forte.from_chord_title": {"zh": "选择和弦集合", "en": "Select Chord Sets"},
    "forte.btn_close": {"zh": "关闭", "en": "Close"},
    "forte.select_all": {"zh": "全选 / 取消全选", "en": "Select / Deselect All"},
    "forte.chord_item": {"zh": "Bar {bar}: [{pc}]  Forte: {forte}", "en": "Bar {bar}: [{pc}]  Forte: {forte}"},
    "forte.bar_merge_item": {"zh": "[小节合并] Bar {bar}: [{pc}]  Forte: {forte}", "en": "[Bar Merge] Bar {bar}: [{pc}]  Forte: {forte}"},
    "forte.empty_input": {"zh": "请输入至少一组音级集合。", "en": "Please enter at least one pitch-class set."},
    "forte.save_csv": {"zh": "保存 CSV", "en": "Save CSV"},
    "forte.table.headers": {
        "zh": ["Chords PCs", "Normal Order", "Intervals", "Interval Vector", "Prime Form", "Forte Class", "P", "I", "R", "RI"],
        "en": ["Chords PCs", "Normal Order", "Intervals", "Interval Vector", "Prime Form", "Forte Class", "P", "I", "R", "RI"]
    },

    # Set Relations tab
    "sr.title": {"zh": "集合关系分析", "en": "Set Relations Analysis"},
    "sr.universe_group": {"zh": "集合全集 (Universe)", "en": "Set Universe"},
    "sr.universe_label": {"zh": "输入所有集合 (每行一组):", "en": "Input all sets (one per line):"},
    "sr.target_label": {"zh": "目标集合:", "en": "Target Set:"},
    "sr.btn_analyze": {"zh": "分析关系", "en": "Analyze Relations"},
    "sr.btn_nexus": {"zh": "查找 Nexus Set", "en": "Find Nexus Set"},
    "sr.btn_from_chord": {"zh": "从和弦分析获取", "en": "Get from Chords Analysis"},
    "sr.no_chord_msg": {"zh": "请先在'和弦分析'选项卡中提取和弦。", "en": "Please extract chords in the 'Chords Analysis' tab first."},
    "sr.empty_universe": {"zh": "请输入至少一组集合到全集。", "en": "Please input at least one set in the universe."},
    "sr.empty_target": {"zh": "请输入目标集合。", "en": "Please input a target set."},
    "sr.invalid_target": {"zh": "目标集合格式无效。", "en": "Invalid target set format."},
    "sr.need_more_sets": {"zh": "全集中至少需要两组集合才能计算 Nexus。", "en": "Need at least 2 sets in the universe to compute nexus."},
    "sr.none": {"zh": "(无)", "en": "(none)"},
    "sr.info_group": {"zh": "基本信息", "en": "Basic Info"},
    "sr.info_target": {"zh": "目标: [{pc}]  Forte: {forte}  Interval Vector: {iv}", "en": "Target: [{pc}]  Forte: {forte}  Interval Vector: {iv}"},
    "sr.info_complement": {"zh": "补集: [{pc}]  Forte: {forte}", "en": "Complement: [{pc}]  Forte: {forte}"},
    "sr.info_nexus": {"zh": "Nexus Set: [{pc}]  关系总数: {score}", "en": "Nexus Set: [{pc}]  Total relations: {score}"},
    "sr.info_intervals": {"zh": "Normal Order: [{pc}]  相邻音程: {intervals}", "en": "Normal Order: [{pc}]  Intervals: {intervals}"},
    "sr.trans_group": {"zh": "变换匹配", "en": "Transformational Matches"},
    "sr.tn_header": {"zh": "—— T_n 移位 ——", "en": "—— T_n Transposition ——"},
    "sr.tn_found": {"zh": "T_{n}: {form} — {count} 个匹配", "en": "T_{n}: {form} — {count} match(es)"},
    "sr.tn_none": {"zh": "T_n: 无匹配", "en": "T_n: no matches found"},
    "sr.trans_found": {"zh": "找到 {n} 个 {label}-匹配: {form}", "en": "Found {n} {label}-match(es): {form}"},
    "sr.trans_none": {"zh": "{label}: {form} — 在 universe 中未找到匹配", "en": "{label}: {form} — no match found in universe"},
    "sr.subsets": {"zh": "子集 ({n})", "en": "Subsets ({n})"},
    "sr.supersets": {"zh": "超集 ({n})", "en": "Supersets ({n})"},
    "sr.z_related": {"zh": "Z-关系 ({n})", "en": "Z-Relations ({n})"},
    "sr.k_related": {"zh": "K-关系 ({n})", "en": "K-Relations ({n})"},
    "sr.invariants": {"zh": "不变包含 ({n})", "en": "Invariant Containments ({n})"},
    "sr.rel_item": {"zh": "[{pc}]  Intervals: {intervals}  Normal: {normal}  Forte: {forte}  Prime: {prime}  IV: {iv}", "en": "[{pc}]  Intervals: {intervals}  Normal: {normal}  Forte: {forte}  Prime: {prime}  IV: {iv}"},
    "sr.rel_k": {"zh": "[{pc}]  Forte: {forte}  (含于目标及其补集)", "en": "[{pc}]  Forte: {forte}  (subset of target & complement)"},
    "sr.rel_z": {"zh": "[{pc}]  Forte: {forte}  Interval Vector: {iv}", "en": "[{pc}]  Forte: {forte}  Interval Vector: {iv}"},
    "sr.combo_bar": {"zh": "Bar {bar}合并: [{pc}]  Forte: {forte}", "en": "Bar {bar} merged: [{pc}]  Forte: {forte}"},
    "sr.combo_item": {"zh": "[{pc}]  Forte: {forte}", "en": "[{pc}]  Forte: {forte}"},
    "sr.nexus_item": {"zh": "[Nexus] [{pc}]  Forte: {forte}  (关联数: {score})", "en": "[Nexus] [{pc}]  Forte: {forte}  (relations: {score})"},
    "sr.nexus_dialog_title": {"zh": "Nexus Set 结果", "en": "Nexus Set Results"},
    "sr.nexus_dialog_header": {"zh": "找到 {count} 个 Nexus 候选 (关联总数: {score})，请选择一个:", "en": "Found {count} nexus candidate(s) (total relations: {score}). Select one:"},
    "sr.computing": {"zh": "计算中...", "en": "Computing..."},
    "sr.progress": {"zh": "计算中... {current}/{total}", "en": "Computing... {current}/{total}"},

    "dialog.export_annotated_msg": {"zh": "已导出:\nMusicXML: {xml}\nPDF: {pdf}", "en": "Exported:\nMusicXML: {xml}\nPDF: {pdf}"},
    "dialog.export_range_title": {"zh": "导出带标注乐谱", "en": "Export Annotated Score"},
    "dialog.export_range_label": {"zh": "小节范围: {min} – {max}", "en": "Measure range: {min} – {max}"},
    "dialog.export_preview": {"zh": "预览标注乐谱", "en": "Preview Annotated Score"},
    "dialog.export_xml": {"zh": "导出 MusicXML", "en": "Export MusicXML"},
    "dialog.export_pdf": {"zh": "导出 PDF", "en": "Export PDF"},
    "dialog.export_xml_msg": {"zh": "MusicXML 已导出:\n{xml}", "en": "MusicXML exported:\n{xml}"},
    "dialog.export_pdf_failed": {"zh": "PDF 导出失败。请确认 MuseScore 4 已安装。\nMuseScore 可以在 musescore.org 免费下载。", "en": "PDF export failed. Please ensure MuseScore 4 is installed.\nMuseScore is available for free at musescore.org."},
    "dialog.export_pdf_msg": {"zh": "PDF 已导出:\n{pdf}", "en": "PDF exported:\n{pdf}"},

    # About
    "about.title": {"zh": "关于", "en": "About"},
    "about.text": {
        "zh": "十二音音乐分析软件 v1.3.9\n\n基于 music21 和 PyQt5 构建\n专为十二音序列音乐分析设计\n\n依赖: music21, PyQt5, matplotlib, numpy, librosa",
        "en": "Twelve-Tone Music Analyzer v1.3.9\n\nBuilt with music21 and PyQt5\nDesigned for twelve-tone serial music analysis\n\nDependencies: music21, PyQt5, matplotlib, numpy, librosa",
    },

    # Update checker
    "update.title": {"zh": "发现新版本", "en": "New Version Available"},
    "update.heading": {"zh": "TwelveToneAnalyzer v{version} 已发布", "en": "TwelveToneAnalyzer v{version} is available"},
    "update.current": {"zh": "当前版本: v{current}", "en": "Current version: v{current}"},
    "update.size": {"zh": "大小: {size}", "en": "Size: {size}"},
    "update.desc_label": {"zh": "更新内容:", "en": "What's new:"},
    "update.btn_download": {"zh": "下载并安装", "en": "Download & Install"},
    "update.btn_skip": {"zh": "跳过此版本", "en": "Skip This Version"},
    "update.btn_remind": {"zh": "稍后提醒", "en": "Remind Later"},
    "update.uptodate": {"zh": "已是最新版本", "en": "Up to Date"},
    "update.uptodate_msg": {"zh": "您正在使用最新版本 v{version}。", "en": "You are running the latest version v{version}."},
    "update.error": {"zh": "检查更新失败", "en": "Update Check Failed"},
    "update.error_msg": {"zh": "无法连接到 GitHub 检查更新。\n\n{detail}\n\n请检查网络连接后重试。", "en": "Could not connect to GitHub to check for updates.\n\n{detail}\n\nPlease check your network and try again."},
    "update.downloading": {"zh": "正在下载... {percent}%", "en": "Downloading... {percent}%"},
    "update.download_complete": {"zh": "下载完成！\n\n安装程序已保存至:\n{path}\n\n是否立即打开安装程序？\n（应用将关闭以完成更新）", "en": "Download complete!\n\nInstaller saved to:\n{path}\n\nOpen the installer now?\n(The app will close to complete the update.)"},
    "menu.help.check_update": {"zh": "检查更新...", "en": "Check for Updates..."},

    # Musescore prompt
    "ms.title": {"zh": "MuseScore 4 未找到", "en": "MuseScore 4 Not Found"},
    "ms.heading": {"zh": "需要 MuseScore 4", "en": "MuseScore 4 Required"},
    "ms.desc": {
        "zh": "MuseScore 4 是免费的乐谱排版软件，本应用需要它来：\n  • 渲染乐谱预览\n  • 生成 PDF / PNG 图片\n  • 导出带标注的乐谱文件\n\n您的系统中未检测到 MuseScore 4，请选择以下操作：",
        "en": "MuseScore 4 is free music notation software. This application needs it to:\n  • Render score previews\n  • Generate PDF / PNG images\n  • Export annotated score files\n\nMuseScore 4 was not detected on your system. Choose an option:",
    },
    "ms.btn_download": {"zh": "下载免费的 MuseScore 4", "en": "Download Free MuseScore 4"},
    "ms.btn_browse": {"zh": "手动定位系统上的 MuseScore 4", "en": "Browse for Installed MuseScore 4"},
    "ms.btn_skip": {"zh": "跳过（部分功能将不可用）", "en": "Skip (Some Features Will Be Unavailable)"},
    "ms.btn_use_detected": {"zh": "使用选中的 MuseScore", "en": "Use Selected MuseScore"},
    "ms.found_list": {"zh": "检测到以下 MuseScore 安装，请选择一个：", "en": "The following MuseScore installations were found. Please choose one:"},
    "ms.browse_title": {"zh": "定位 MuseScore 4 可执行文件", "en": "Locate MuseScore 4 Executable"},

    # Image viewer first-run prompt
    "iv.title": {"zh": "设置图片查看器", "en": "Set Image Viewer"},
    "iv.heading": {"zh": "选择图片查看器", "en": "Choose Image Viewer"},
    "iv.desc": {
        "zh": "图表生成后将自动用图片查看器打开 PNG 图片。推荐使用 BandiView（免费、快速）。\n\n您也可以选择系统上已有的图片查看器。",
        "en": "Charts will be opened as PNG images. BandiView is recommended — free and fast.\n\nYou can also choose an existing viewer on your system."
    },
    "iv.btn_download": {"zh": "下载免费的 BandiView（推荐）", "en": "Download Free BandiView (Recommended)"},
    "iv.btn_browse": {"zh": "手动选择系统上的图片查看器", "en": "Browse for an Installed Image Viewer"},
    "iv.btn_skip": {"zh": "跳过（稍后可在图表页设置）", "en": "Skip (Can Be Set Later in Chart Tab)"},
    "iv.btn_use_selected": {"zh": "使用选中的查看器", "en": "Use Selected Viewer"},
    "iv.found_list": {"zh": "检测到以下可查看 PNG 的程序，请选择一个：", "en": "The following PNG viewers were found. Please choose one:"},
    "iv.browse_title": {"zh": "选择图片查看器程序", "en": "Select Image Viewer Program"},
    "iv.browse_filter": {"zh": "可执行程序 (*.exe);;所有文件 (*)", "en": "Executable (*.exe);;All Files (*)"},

    # Temp directory first-run prompt
    "td.title": {"zh": "设置临时文件夹", "en": "Set Temp Directory"},
    "td.heading": {"zh": "选择临时文件存放位置", "en": "Choose Temp File Location"},
    "td.desc": {
        "zh": "应用运行中产生的临时文件（图表 PNG、乐谱导出等）将保存在此文件夹中。\n您可以随时在设置中更改。",
        "en": "Temporary files (chart PNGs, score exports, etc.) will be stored in this folder.\nYou can change this later in Settings."
    },
    "td.default_path": {"zh": "默认路径：{path}", "en": "Default path: {path}"},
    "td.btn_default": {"zh": "使用默认路径", "en": "Use Default Path"},
    "td.btn_custom": {"zh": "自定义文件夹...", "en": "Choose Custom Folder..."},
    "td.browse_title": {"zh": "选择临时文件夹", "en": "Select Temp Directory"},

    # Settings dialog
    "settings.title": {"zh": "设置", "en": "Settings"},
    "settings.font_group": {"zh": "界面外观", "en": "Appearance"},
    "settings.font_size": {"zh": "字体大小:", "en": "Font Size:"},
    "settings.ms_group": {"zh": "MuseScore 4 路径", "en": "MuseScore 4 Path"},
    "settings.ms_placeholder": {"zh": "未配置 MuseScore 路径", "en": "MuseScore path not configured"},
    "settings.ms_label": {"zh": "可执行文件:", "en": "Executable:"},
    "settings.temp_group": {"zh": "临时文件目录", "en": "Temporary Directory"},
    "settings.temp_label": {"zh": "目录:", "en": "Directory:"},
    "settings.browse": {"zh": "浏览...", "en": "Browse..."},
    "settings.save": {"zh": "保存", "en": "Save"},
    "settings.cancel": {"zh": "取消", "en": "Cancel"},
    "settings.browse_ms": {"zh": "定位 MuseScore 4 可执行文件", "en": "Locate MuseScore 4 Executable"},
    "settings.browse_temp": {"zh": "选择临时目录", "en": "Select Temporary Directory"},

    # Overview tab
    "overview.file_info": {"zh": "文件信息", "en": "File Info"},
    "overview.no_file": {"zh": "未加载文件", "en": "No file loaded"},
    "overview.file_label": {"zh": "文件: {name}", "en": "File: {name}"},
    "overview.measures": {"zh": "声部数: {parts}  |  小节范围: {start} – {end}", "en": "Parts: {parts} | Measures: {start} – {end}"},
    "overview.diag_group": {"zh": "声部诊断", "en": "Voice Diagnosis"},
    "overview.table.headers": {
        "zh": ["编号", "声部名", "乐器", "音符总数", "单音", "和弦数", "音域"],
        "en": ["No.", "Part Name", "Instrument", "Total Notes", "Single Notes", "Chords", "Range"],
    },
    "overview.btn_full_plot": {"zh": "查看全曲总谱图", "en": "View Full Score Plot"},
    "overview.btn_export": {"zh": "导出带标注乐谱 (PDF/MusicXML)", "en": "Export Annotated Score (PDF/MusicXML)"},
    "overview.plot_error": {"zh": "绘图错误", "en": "Plot Error"},
    "overview.export_failed": {"zh": "导出失败", "en": "Export Failed"},

    # Visualization tab
    "viz.part_group": {"zh": "选择声部", "en": "Select Part"},
    "viz.all_parts": {"zh": "所有声部", "en": "All Parts"},
    "viz.measure_group": {"zh": "小节范围", "en": "Measure Range"},
    "viz.start_measure": {"zh": "起始小节:", "en": "Start Measure:"},
    "viz.end_measure": {"zh": "结束小节:", "en": "End Measure:"},
    "viz.plot_type": {"zh": "图表类型", "en": "Plot Type"},
    "viz.btn_generate": {"zh": "生成图表", "en": "Generate Plot"},
    "viz.btn_save_png": {"zh": "保存 PNG", "en": "Save PNG"},
    "viz.save_png": {"zh": "保存图表为 PNG", "en": "Save Plot as PNG"},
    "viz.save_done": {"zh": "图表已保存", "en": "Plot Saved"},
    "viz.plot_placeholder": {"zh": "点击「生成图表」查看图形\n图表将在新窗口中打开", "en": "Click 'Generate Plot' to view\nthe plot in a new window"},
    "viz.score_info": {"zh": "声部: {parts} | 小节: 1–{measures}", "en": "Parts: {parts} | Measures: 1–{measures}"},
    "viz.range_error": {"zh": "范围错误", "en": "Range Error"},
    "viz.range_error_msg": {"zh": "起始小节不能大于结束小节。", "en": "Start measure cannot be greater than end measure."},
    "viz.plot_error": {"zh": "绘图错误", "en": "Plot Error"},
    "viz.plot_types": {
        "zh": ["Note Quarter Length by Pitch", "音级分布直方图 (PitchClass Histogram)", "音级-时值散点图 (Scatter Weighted PClass QLen)", "小节-音级散点图 (Scatter Measure PitchClass)", "水平加权柱状图 (Horizontal Bar Weighted)", "3D 柱状图 (3D Bars)", "调性色块图 (Color Grid)"],
        "en": ["Note Quarter Length by Pitch", "PitchClass Histogram", "Scatter Weighted PitchClass QuarterLength", "Scatter Measure vs PitchClass", "Horizontal Bar Weighted", "3D Bars", "Key Analysis Color Grid"],
    },

    # Twelve-tone tab
    "tt.extract_group": {"zh": "音列提取与编辑", "en": "Row Extraction & Editing"},
    "tt.part_label": {"zh": "声部:", "en": "Part:"},
    "tt.btn_extract": {"zh": "自动提取前12音", "en": "Auto-Extract First 12 Notes"},
    "tt.manual_label": {"zh": "手动输入12音 (空格分隔):", "en": "Manual Input (space-separated):"},
    "tt.btn_confirm": {"zh": "确认音列", "en": "Confirm Row"},
    "tt.extract_failed": {"zh": "提取失败", "en": "Extraction Failed"},
    "tt.input_error": {"zh": "输入错误", "en": "Input Error"},
    "tt.input_count_err": {"zh": "需要12个数字，当前{count}个。", "en": "Need 12 numbers, got {count}."},
    "tt.input_range_err": {"zh": "数字范围必须是 0~11。", "en": "Numbers must be in range 0~11."},
    "tt.input_format_err": {"zh": "包含非数字字符。", "en": "Non-numeric characters found."},
    "tt.forms_group": {"zh": "P / I / R / RI 四种形式", "en": "P / I / R / RI Forms"},
    "tt.matrix_group": {"zh": "12音矩阵", "en": "12-Tone Matrix"},
    "tt.row_group": {"zh": "音列分组", "en": "Row Grouping"},
    "tt.btn_trichords": {"zh": "三音组 (4组)", "en": "Trichords (4 groups)"},
    "tt.btn_tetrachords": {"zh": "四音组 (3组)", "en": "Tetrachords (3 groups)"},
    "tt.btn_hexachords": {"zh": "六音组 (2组)", "en": "Hexachords (2 groups)"},
    "tt.btn_show_row": {"zh": "显示乐谱", "en": "Show Score"},
    "tt.btn_save_row_png": {"zh": "导出 PNG", "en": "Export PNG"},
    "tt.save_row_png": {"zh": "保存 PNG", "en": "Save PNG"},
    "tt.row_png_saved": {"zh": "PNG 已保存至:\n{path}", "en": "PNG saved to:\n{path}"},
    "tt.btn_export_forms": {"zh": "导出四种形式 PNG", "en": "Export Four Forms PNG"},
    "tt.btn_export_heatmap": {"zh": "导出矩阵热力图 PNG", "en": "Export Matrix Heatmap PNG"},
    "tt.btn_dividing_panel": {"zh": "十二音列重组集合", "en": "Open Row Dividing to Sets Panel"},
    "tt.panel_btn_open": {"zh": "▸ 十二音列重组集合", "en": "▸ Open Row Dividing to Sets Panel"},
    "tt.panel_btn_close": {"zh": "▾ 关闭十二音列重组集合", "en": "▾ Close Row Dividing to Sets Panel"},
    "tt.btn_row_division": {"zh": "音列分组弹窗", "en": "Row Division"},
    "tt.dlg_group_size": {"zh": "分组大小:", "en": "Group size:"},
    "tt.merge_title": {"zh": "声部/小节合并十二音搜索", "en": "Merge Parts & Measures"},
    "tt.btn_merge_search": {"zh": "合并并搜索十二音集合", "en": "Merge & Search"},
    "tt.merge_no_score": {"zh": "请先载入乐谱", "en": "Please load a score first"},
    "tt.merge_no_part": {"zh": "请至少选择一个声部", "en": "Select at least one part"},
    "tt.merge_no_notes": {"zh": "所选范围无音符", "en": "No notes in selected range"},
    "tt.matrix_group": {"zh": "12 音矩阵 (A=10, B=11)", "en": "12-Tone Matrix (A=10, B=11)"},
    "tt.heatmap_save_prompt": {"zh": "热力图已关闭。是否保存为 PNG？", "en": "Heatmap closed. Save as PNG?"},
    "tt.forms_exported": {"zh": "四种形式已导出至:\n{path}", "en": "Four forms exported to:\n{path}"},
    "tt.subset_group": {"zh": "48 种形式子集搜索", "en": "Subset Search in 48 Forms"},
    "tt.subset_label": {"zh": "待搜索集合:", "en": "Input Set:"},
    "tt.btn_search_subset": {"zh": "搜索", "en": "Search"},
    "tt.subset_none": {"zh": "未在任何形式中匹配", "en": "No match in any of the 48 forms"},
    "tt.subset_no_row": {"zh": "请先加载或提取十二音序列", "en": "Please load/extract a 12-tone row first"},
    "tt.subset_invalid": {"zh": "无效集合，请输入空格分隔的音级 (0-11)", "en": "Invalid set. Enter space-separated pitch classes (0-11)"},
    "tt.subset_too_short": {"zh": "集合至少需要 3 个音级", "en": "Input set must have at least 3 pitch classes"},
    "tt.export_matrix": {"zh": "导出矩阵 PNG", "en": "Export Matrix PNG"},
    "tt.export_forms": {"zh": "选择四种形式的保存目录", "en": "Choose directory for four forms"},
    "tt.matrix_exported": {"zh": "矩阵图已保存至:\n{path}", "en": "Matrix saved to:\n{path}"},

    # Chord tab
    "chord.filter_group": {"zh": "筛选条件", "en": "Filter"},
    "chord.part_label": {"zh": "声部:", "en": "Parts:"},
    "chord.start_measure": {"zh": "起始小节:", "en": "Start Measure:"},
    "chord.end_measure": {"zh": "结束小节:", "en": "End Measure:"},
    "chord.btn_extract": {"zh": "提取和弦", "en": "Extract Chords"},
    "chord.result_group": {"zh": "和弦分析结果", "en": "Chords Analysis Results"},
    "chord.table.headers": {
        "zh": ["小节", "偏移", "声部", "音符", "Chords PCs", "Normal Order", "Prime Form", "Forte Class", "音域"],
        "en": ["Bar", "Offset", "Part Name", "Notes", "Chords PCs", "Normal Order", "Prime Form", "Forte Class", "Pitch Range"],
    },
    "chord.btn_export_md": {"zh": "导出 Markdown", "en": "Export Markdown"},
    "chord.btn_export_csv": {"zh": "导出 CSV", "en": "Export CSV"},
    "chord.no_part": {"zh": "未选择声部", "en": "No Part Selected"},
    "chord.no_part_msg": {"zh": "请至少选择一个声部。", "en": "Please select at least one part."},
    "chord.range_error": {"zh": "范围错误", "en": "Range Error"},
    "chord.range_error_msg": {"zh": "起始小节不能大于结束小节。", "en": "Start measure cannot be greater than end measure."},
    "chord.extract_failed": {"zh": "提取失败", "en": "Extraction Failed"},
    "chord.save_md": {"zh": "保存 Markdown", "en": "Save Markdown"},
    "chord.save_csv": {"zh": "保存 CSV", "en": "Save CSV"},
    "chord.export_done": {"zh": "导出完成", "en": "Export Complete"},
    "chord.btn_show_score": {"zh": "显示乐谱", "en": "Show Score"},
    "chord.btn_save_png": {"zh": "导出 PNG", "en": "Export PNG"},
    "chord.save_png": {"zh": "保存 PNG", "en": "Save PNG"},

    # Audio tab
    "audio.file_group": {"zh": "音频文件", "en": "Audio File"},
    "audio.no_file": {"zh": "未加载音频", "en": "No audio loaded"},
    "audio.btn_load": {"zh": "加载音频文件...", "en": "Load Audio File..."},
    "audio.ctrl_group": {"zh": "分析参数", "en": "Analysis Parameters"},
    "audio.type_label": {"zh": "分析类型:", "en": "Analysis Type:"},
    "audio.segments_label": {"zh": "分段数:", "en": "Segments:"},
    "audio.btn_analyze": {"zh": "开始分析", "en": "Analyze"},
    "audio.btn_save_plot": {"zh": "保存图表为 PNG", "en": "Save Plot as PNG"},
    "audio.loaded": {"zh": "已加载: {name}  (采样率: {sr} Hz, 时长: {dur:.1f} 秒)", "en": "Loaded: {name} (SR: {sr} Hz, Duration: {dur:.1f}s)"},
    "audio.loading": {"zh": "正在加载: {name}...", "en": "Loading: {name}..."},
    "audio.load_failed": {"zh": "加载失败", "en": "Load Failed"},
    "audio.analysis_error": {"zh": "分析错误", "en": "Analysis Error"},
    "audio.save_png": {"zh": "保存图表", "en": "Save Plot"},
    "audio.save_done": {"zh": "保存完成", "en": "Save Complete"},
    "audio.analysis_types": {
        "zh": ["波形图 (Waveform)", "频谱图 (Spectrogram)", "Chromagram", "MFCC", "Tonnetz", "Tempogram"],
        "en": ["Waveform", "Spectrogram", "Chromagram", "MFCC", "Tonnetz", "Tempogram"],
    },

    # Score viewer
    "score.no_score": {"zh": "未加载乐谱", "en": "No Score Loaded"},

    # URL-loaded fallback
    "generic.score_name": {"zh": "URL加载的乐谱", "en": "URL-loaded Score"},

    # Language switch
    "menu.language.zh": {"zh": "中文", "en": "中文"},
    "menu.language.en": {"zh": "English", "en": "English"},
    "language.changed": {"zh": "语言已切换，正在重新启动...", "en": "Language changed, restarting..."},
    "dialog.restart_title": {"zh": "重启应用", "en": "Restart Application"},
    "dialog.restart_font_msg": {"zh": "字体大小已更改，需要重启应用才能完全生效。\n\n是否立即重启？", "en": "Font size changed. A restart is needed for the changes to take full effect.\n\nRestart now?"},
    "dialog.restart_lang_msg": {"zh": "语言已切换，需要重启应用才能完全生效。\n\n是否立即重启？", "en": "Language changed. A restart is needed for the changes to take full effect.\n\nRestart now?"},

    # Lattice tab
    "tab.lattice": {"zh": "包含格", "en": "Inclusion Lattice"},
    "tab.forte_name": {"zh": "Forte 集合分析", "en": "Forte Set Analysis"},
    "tab.set_relations": {"zh": "集合关系", "en": "Set Relations"},
    "tab.annotated_score": {"zh": "标注乐谱", "en": "Annotated Score"},
    "tab.open_score": {"zh": "打开乐谱", "en": "Open Score"},
    "tab.strip_annotations": {"zh": "导出时去除标注信息（歌词、力度、连音线等）", "en": "Strip annotations on export (lyrics, dynamics, slurs, ties)"},
    "tab.strip_annotations_tip": {"zh": "勾选后导出的 MusicXML 将不包含歌词、力度记号和连音线", "en": "When checked, exported MusicXML excludes lyrics, dynamics, slurs, and ties"},
    "tab.mei_notice": {"zh": "MEI 文件已加载，将使用完整乐谱进行标注（不支持小节范围选择）", "en": "MEI file loaded. Full score will be annotated (measure range not supported for MEI)."},
    "tab.mei_full_score": {"zh": "标注范围：完整乐谱", "en": "Annotation range: Full score"},
    "tab.no_score_loaded": {"zh": "请先导入乐谱", "en": "Please load a score first"},
    "tab.measure_range": {"zh": "小节范围: {min} – {max}", "en": "Measure range: {min} – {max}"},
    "lattice.ctrl_group": {"zh": "音级集合", "en": "Pitch-Class Set"},
    "lattice.input_label": {"zh": "输入音级 (空格分隔):", "en": "Input Pitch Classes (space-separated):"},
    "lattice.min_size": {"zh": "最小子集:", "en": "Min Size:"},
    "lattice.max_size": {"zh": "最大子集:", "en": "Max Size:"},
    "lattice.btn_generate": {"zh": "生成包含格", "en": "Generate Lattice"},
    "lattice.btn_from_row": {"zh": "从十二音列获取", "en": "Get from Twelve-Tone Row"},
    "lattice.btn_save": {"zh": "保存图表为 PNG", "en": "Save Plot as PNG"},
    "lattice.input_error": {"zh": "输入错误", "en": "Input Error"},
    "lattice.no_input": {"zh": "请输入音级集合。", "en": "Please enter a pitch-class set."},
    "lattice.invalid_input": {"zh": "包含非数字字符，请用空格分隔整数。", "en": "Non-numeric characters found. Use space-separated integers."},
    "lattice.size_error": {"zh": "最大子集不能小于最小子集。", "en": "Max size cannot be less than min size."},
    "lattice.range_warn": {"zh": "间隔超过 4 可能导致包含格显示不全，建议缩小范围。\n点击 OK 仍会生成。", "en": "A range > 4 may cause the lattice to display poorly. Consider narrowing the range.\nClick OK to generate anyway."},
    "lattice.range_hint": {"zh": "范围 1–11。注意: 最大与最小之差超过 4 可能导致图形显示不全", "en": "Range 1–11. Note: a span > 4 may result in poor display"},
    "lattice.no_subsets": {"zh": "集合大小({count})不足以生成指定范围的子集。", "en": "Set size ({count}) is too small for the specified range."},
    "lattice.from_row_title": {"zh": "提示", "en": "Info"},
    "lattice.no_row_msg": {"zh": "请在'十二音分析'选项卡中先提取或确认音列。", "en": "Please extract or confirm a row in the 'Twelve-Tone' tab first."},
    "lattice.btn_from_chord": {"zh": "从和弦分析获取", "en": "Get from Chords Analysis"},
    "lattice.btn_chord_relations": {"zh": "Chord Relation Lattice", "en": "Chord Relation Lattice"},
    "lattice.btn_chord_relations_hint": {"zh": "用已提取的和弦集合构建包含关系格（需先点击「从和弦分析获取」）", "en": "Build inclusion lattice from extracted chord sets (click 'Get from Chord Analysis' first)"},
    "lattice.edge_hint": {"zh": "提示：只有连线连接的两个集合之间存在包含关系（子集 / 超集）", "en": "Hint: only connected nodes have an inclusion relationship (subset / superset)"},
    "lattice.no_chord_msg": {"zh": "请先在'和弦分析'选项卡中提取和弦。", "en": "Please extract chords in the 'Chords Analysis' tab first."},
    "lattice.not_enough_sets": {"zh": "当前大小范围内至少需要 2 个集合才能构建关系格。", "en": "Need at least 2 sets in the current size range to build a relations lattice."},
    "lattice.not_enough_sets_with_dropped": {"zh": "大小范围 [{min_sz}–{max_sz}] 内仅有 {kept} 个集合可用（{dropped} 个被过滤），\n至少需要 2 个。请调整 Min/Max Size。", "en": "Only {kept} sets within range [{min_sz}–{max_sz}] ({dropped} filtered out).\nNeed at least 2. Please adjust Min/Max Size."},
    "lattice.select_chord": {"zh": "选择音级集合:", "en": "Select a pitch-class set:"},
    "lattice.collections_group": {"zh": "批量集合分析", "en": "Batch Collections"},
    "lattice.collections_placeholder": {"zh": "每行一组音级，空格分隔:\n0 2 4 7 9\n6 8 11 1 4\n...", "en": "One pc-set per line, space-separated:\n0 2 4 7 9\n6 8 11 1 4\n..."},
    "lattice.btn_analyze_collections": {"zh": "分析并加载", "en": "Analyze & Load"},
    "lattice.collections_empty": {"zh": "请输入至少一组音级集合。", "en": "Please enter at least one pitch-class set."},
    "lattice.save_png": {"zh": "保存包含格图", "en": "Save Lattice Plot"},
    "lattice.saved": {"zh": "保存完成", "en": "Save Complete"},
    "lattice.no_fig": {"zh": "没有可保存的图形，请先生成包含格。", "en": "No figure to save. Please generate a lattice first."},
    "lattice.save_permission_error": {"zh": "保存失败：当前路径无写入权限，请更换保存文件夹。\n\n错误详情：{error}", "en": "Save failed: no write permission for the selected path.\nPlease choose a different folder.\n\nDetail: {error}"},
}


class I18n(QObject):
    """Singleton internationalization manager."""
    language_changed = pyqtSignal(str)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lang = "zh"
        return cls._instance

    @property
    def language(self) -> str:
        return self._lang

    def set_language(self, lang: str):
        from src.utils.config import get_settings
        self._lang = lang
        get_settings().setValue("general/language", lang)
        self.language_changed.emit(lang)

    def load_from_settings(self):
        from src.utils.config import get_settings
        self._lang = get_settings().value("general/language", "zh", type=str)
        if self._lang not in ("zh", "en"):
            self._lang = "zh"


# Global instance
_i18n = I18n()


def tr(key: str, **kwargs) -> str:
    """Translate a key to the current language."""
    entry = TRANSLATIONS.get(key, {})
    text = entry.get(_i18n.language, entry.get("zh", key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def tr_list(key: str) -> list[str]:
    """Translate a key that returns a list."""
    entry = TRANSLATIONS.get(key, {})
    return entry.get(_i18n.language, entry.get("zh", []))


def current_language() -> str:
    return _i18n.language


def set_language(lang: str):
    _i18n.set_language(lang)


def load_language():
    _i18n.load_from_settings()
