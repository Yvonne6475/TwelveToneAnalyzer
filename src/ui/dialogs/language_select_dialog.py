"""First-launch language selection dialog."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QPushButton,
    QButtonGroup, QHBoxLayout,
)
from PyQt5.QtCore import Qt
from src.utils.i18n import set_language, current_language
from src.utils.config import get_settings


# Self-contained: this dialog runs BEFORE the i18n system is loaded,
# so all text is defined inline (bilingual).
TEXTS = {
    "title": {"zh": "选择界面语言", "en": "Select Interface Language"},
    "prompt": {"zh": "请选择软件使用语言", "en": "Please choose your app language"},
    "option_zh": {"zh": "简体中文", "en": "简体中文"},
    "option_en": {"zh": "English", "en": "English"},
    "confirm": {"zh": "确认并启动软件", "en": "Confirm & Launch App"},
}


class LanguageSelectDialog(QDialog):
    """Shown only on first launch.  Returns the chosen language code."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chosen_lang = "zh"
        self._setup_ui()

    def _setup_ui(self):
        # Try to use the current language if one was already set; otherwise
        # default to zh for the dialog itself.
        try:
            display_lang = current_language()
        except Exception:
            display_lang = "zh"

        def t(key: str) -> str:
            return TEXTS.get(key, {}).get(display_lang, key)

        self.setWindowTitle(t("title"))
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        prompt = QLabel(t("prompt"))
        prompt.setAlignment(Qt.AlignCenter)
        prompt.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(prompt)

        # Radio group
        self._group = QButtonGroup(self)
        radio_layout = QVBoxLayout()
        radio_layout.setSpacing(8)

        self._rb_zh = QRadioButton(t("option_zh"))
        self._rb_en = QRadioButton(t("option_en"))

        for rb, lang in [(self._rb_zh, "zh"), (self._rb_en, "en")]:
            rb.setStyleSheet("font-size: 14pt; padding: 6px 12px;")
            self._group.addButton(rb)
            radio_layout.addWidget(rb)
            rb.toggled.connect(lambda checked, l=lang: self._on_choice(l) if checked else None)

        self._rb_zh.setChecked(True)
        radio_widget = QLabel()  # dummy container
        radio_widget.setLayout(radio_layout)
        layout.addWidget(radio_widget)

        # Confirm button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_confirm = QPushButton(t("confirm"))
        btn_confirm.setMinimumWidth(200)
        btn_confirm.setStyleSheet(
            "font-size: 14pt; padding: 8px 24px;"
            "background-color: #6b4c2a; color: #fefdfb;"
            "border-radius: 6px; font-weight: bold;"
        )
        btn_confirm.clicked.connect(self._on_confirm)
        btn_layout.addWidget(btn_confirm)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_choice(self, lang: str):
        self._chosen_lang = lang

    def _on_confirm(self):
        # Persist immediately
        set_language(self._chosen_lang)
        get_settings().setValue("general/language_configured", True)
        self.accept()

    @property
    def chosen_lang(self) -> str:
        return self._chosen_lang
