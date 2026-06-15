"""Main application window with tabbed interface."""

import os
import sys
import traceback
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QStatusBar, QAction, QLabel,
    QFileDialog, QMessageBox, QApplication,
)
from PyQt5.QtCore import Qt, QProcess

from music21 import converter

from src.ui.widgets.score_opener import load_score_async, prompt_url_dialog
from src.utils.config import get_temp_dir, get_musescore_path
from src.utils.i18n import tr, tr_list, load_language, set_language, current_language

from src.ui.tabs.overview_tab import OverviewTab
from src.ui.tabs.annotated_score_tab import AnnotatedScoreTab
from src.ui.tabs.visualization_tab import VisualizationTab
from src.ui.tabs.twelve_tone_tab import TwelveToneTab
from src.ui.tabs.chord_tab import ChordTab
from src.ui.tabs.audio_tab import AudioTab
from src.ui.tabs.lattice_tab import LatticeTab
from src.ui.tabs.forte_name_tab import ForteNameTab
from src.ui.tabs.set_relations_tab import SetRelationsTab

from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.musescore_prompt import check_musescore_on_startup
from src.ui.theme import refresh_theme, get_font_size


class MainWindow(QMainWindow):
    def __init__(self, musescore_path=""):
        super().__init__()
        load_language()
        self._musescore_path = musescore_path
        self._score = None
        self._midi_score = None
        self._score_path = ""
        self._temp_dir = get_temp_dir()
        self._setup_ui()
        self._update_musescore_status()

    def _setup_ui(self):
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(1000, 680)
        self._create_menus()
        self._create_tabs()
        self._create_statusbar()

    def _create_menus(self):
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu(tr("menu.file"))

        act_open = QAction(tr("menu.file.open"), self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_open_file)
        file_menu.addAction(act_open)

        act_open_url = QAction(tr("menu.file.open_url"), self)
        act_open_url.triggered.connect(self._on_open_url)
        file_menu.addAction(act_open_url)

        act_open_github = QAction(tr("menu.file.open_github"), self)
        act_open_github.triggered.connect(self._on_open_github)
        file_menu.addAction(act_open_github)

        act_open_corpus = QAction(tr("menu.file.open_corpus"), self)
        act_open_corpus.triggered.connect(self._on_open_corpus)
        file_menu.addAction(act_open_corpus)

        file_menu.addSeparator()

        act_open_audio = QAction(tr("menu.file.open_audio"), self)
        act_open_audio.triggered.connect(self._on_open_audio)
        file_menu.addAction(act_open_audio)

        file_menu.addSeparator()

        act_exit = QAction(tr("menu.file.exit"), self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Settings menu
        settings_menu = mb.addMenu(tr("menu.settings"))
        act_settings = QAction(tr("menu.settings.prefs"), self)
        act_settings.triggered.connect(self._on_settings)
        settings_menu.addAction(act_settings)

        # Language submenu
        lang_menu = settings_menu.addMenu(tr("menu.settings.language"))
        act_zh = QAction(tr("menu.language.zh"), self)
        act_zh.triggered.connect(lambda: self._on_switch_language("zh"))
        lang_menu.addAction(act_zh)
        act_en = QAction(tr("menu.language.en"), self)
        act_en.triggered.connect(lambda: self._on_switch_language("en"))
        lang_menu.addAction(act_en)

        # Export menu
        export_menu = mb.addMenu(tr("menu.export"))
        act_export_report = QAction(tr("menu.export.report"), self)
        act_export_report.triggered.connect(self._on_export_report)
        export_menu.addAction(act_export_report)

        # Help menu
        help_menu = mb.addMenu(tr("menu.help"))

        act_check_update = QAction(tr("menu.help.check_update"), self)
        act_check_update.triggered.connect(self._on_check_update)
        help_menu.addAction(act_check_update)

        help_menu.addSeparator()

        act_about = QAction(tr("menu.help.about"), self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    def _create_tabs(self):
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._overview_tab = OverviewTab(self)
        self._annotated_score_tab = AnnotatedScoreTab(self)
        self._visualization_tab = VisualizationTab(self)
        self._twelve_tone_tab = TwelveToneTab(self)
        self._chord_tab = ChordTab(self)
        self._audio_tab = AudioTab(self)
        self._lattice_tab = LatticeTab(self)
        self._forte_name_tab = ForteNameTab(self)
        self._set_relations_tab = SetRelationsTab(self)

        self._tabs.addTab(self._overview_tab, tr("tab.overview"))
        self._tabs.addTab(self._annotated_score_tab, tr("tab.annotated_score"))
        self._tabs.addTab(self._visualization_tab, tr("tab.visualization"))
        self._tabs.addTab(self._twelve_tone_tab, tr("tab.twelve_tone"))
        self._tabs.addTab(self._chord_tab, tr("tab.chord"))
        self._tabs.addTab(self._audio_tab, tr("tab.audio"))
        self._tabs.addTab(self._lattice_tab, tr("tab.lattice"))
        self._tabs.addTab(self._forte_name_tab, tr("tab.forte_name"))
        self._tabs.addTab(self._set_relations_tab, tr("tab.set_relations"))

    def _create_statusbar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._musescore_label = QLabel(tr("status.musescore.not_configured"))
        self._status_bar.addPermanentWidget(self._musescore_label)

    def _update_musescore_status(self):
        ms_path = get_musescore_path()
        if ms_path and os.path.isfile(ms_path):
            self._musescore_label.setText(tr("status.musescore.ready"))
        else:
            self._musescore_label.setText(tr("status.musescore.not_configured"))

    @property
    def score(self):
        return self._score

    @property
    def midi_score(self):
        return self._midi_score

    @property
    def score_path(self):
        return self._score_path

    @property
    def temp_dir(self):
        return self._temp_dir

    @property
    def musescore_path(self):
        return get_musescore_path()

    def set_score(self, score, path=""):
        from src.core.score_analyzer import get_measure_range, normalize_score

        # Normalize Opus → Score so all downstream code works
        score = normalize_score(score)

        self._score = score
        self._score_path = path

        is_mei = path.endswith('.mei') if path else False
        if is_mei:
            self._max_measure = 0  # MEI: measure range not applicable
        else:
            try:
                _, self._max_measure = get_measure_range(score)
            except Exception:
                self._max_measure = 272

        self._try_load_midi(path)

        errors = []
        for tab in [self._overview_tab, self._annotated_score_tab,
                     self._visualization_tab, self._twelve_tone_tab,
                     self._chord_tab, self._lattice_tab,
                     self._forte_name_tab, self._set_relations_tab,
                     self._audio_tab]:
            try:
                tab.on_score_loaded(score, path)
            except Exception:
                tb = traceback.format_exc()
                print(tb)
                errors.append(f"{type(tab).__name__}: {tb[-200:]}")
        if errors:
            QMessageBox.warning(self, "Load Error",
                                "Errors processing score:\n\n" + "\n".join(errors))

        name = Path(path).name if path else tr("generic.score_name")
        self.statusBar().showMessage(
            tr("status.score_loaded", name=name, measures=self._max_measure)
        )

    def _try_load_midi(self, path: str):
        self._midi_score = None
        if not path:
            return
        if path.endswith('.mei'):
            return
        try:
            self._midi_score = converter.parse(path)
        except Exception:
            pass

    def set_audio_file(self, path):
        self._audio_tab.on_audio_loaded(path)
        self._tabs.setCurrentWidget(self._audio_tab)
        self.statusBar().showMessage(tr("status.audio_loaded", name=Path(path).name))

    def get_max_measure(self) -> int:
        return getattr(self, "_max_measure", 272)

    def _on_switch_language(self, lang: str):
        current = current_language()
        if lang == current:
            return
        set_language(lang)
        from src.utils.config import get_settings
        get_settings().setValue("general/language_configured", True)
        reply = QMessageBox.question(
            self, tr("dialog.restart_title"), tr("dialog.restart_lang_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._restart_app()

    def _restart_app(self):
        """Restart the application to apply settings changes."""
        QProcess.startDetached(sys.executable, sys.argv)
        QApplication.quit()

    # ---- Slot handlers ----

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.open_score"), "",
            tr("dialog.open_score_filter")
        )
        if path:
            self.statusBar().showMessage(tr("status.loading_score"))
            load_score_async(self, lambda s, p: self.set_score(s, p), "file", path)

    def _on_open_url(self):
        url = prompt_url_dialog(self, tr("dialog.url_prompt"), tr("dialog.url_label"))
        if url:
            self.statusBar().showMessage(tr("status.downloading"))
            load_score_async(self, lambda s, p: self.set_score(s, p), "url", url)

    def _on_open_github(self):
        url = prompt_url_dialog(
            self,
            tr("dialog.github_prompt"), tr("dialog.github_label"),
            default_text="https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/Luo's_String_Quartet_No.2_full_score.musicxml"
        )
        if url:
            self.statusBar().showMessage(tr("status.downloading_github"))
            load_score_async(self, lambda s, p: self.set_score(s, p), "url", url)

    def _on_open_corpus(self):
        from src.ui.widgets.score_opener import _prompt_corpus_name
        name = _prompt_corpus_name(self)
        if not name:
            return
        self.statusBar().showMessage(tr("status.loading_score"))
        load_score_async(self, lambda s, p: self.set_score(s, p), "corpus", name)

    def _on_open_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.open_audio"), "",
            tr("dialog.open_audio_filter")
        )
        if path:
            self.set_audio_file(path)

    def _on_settings(self):
        old_font_size = get_font_size()
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self._update_musescore_status()
            self._temp_dir = get_temp_dir()
            new_font_size = get_font_size()
            if new_font_size != old_font_size:
                reply = QMessageBox.question(
                    self, tr("dialog.restart_title"), tr("dialog.restart_font_msg"),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self._restart_app()
                else:
                    refresh_theme(QApplication.instance())
            else:
                refresh_theme(QApplication.instance())

    def _on_export_report(self):
        QMessageBox.information(self, tr("dialog.export_report"), tr("dialog.export_report_msg"))

    def _on_check_update(self):
        """Check for updates via GitHub Releases API."""
        from src.core.updater import check_for_updates, VERSION
        from src.ui.dialogs.update_dialog import UpdateDialog

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            info = check_for_updates()
            QApplication.restoreOverrideCursor()

            if info is None:
                QMessageBox.information(
                    self,
                    tr("update.uptodate"),
                    tr("update.uptodate_msg", version=VERSION),
                )
            else:
                dlg = UpdateDialog(info, self)
                dlg.exec_()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                tr("update.error"),
                tr("update.error_msg", detail=str(e)),
            )

    def _on_about(self):
        QMessageBox.about(self, tr("about.title"), tr("about.text"))
