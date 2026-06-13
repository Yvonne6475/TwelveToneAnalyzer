"""Music-inspired light theme for the Twelve-Tone Analyzer. Supports font size scaling."""

import os

from PyQt5.QtGui import QFont
from PyQt5.QtCore import QStandardPaths
from src.utils.config import get_settings


def default_save_path(filename: str) -> str:
    """Return a safe default save path (Desktop, never CWD which may be read-only)."""
    d = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
    if not d or not os.path.isdir(d):
        d = os.path.expanduser("~")
    return os.path.join(d, filename)


# Color palette — elegant music score aesthetic
# Warm white background, deep navy headings, gold accents, burgundy highlights

def get_font_size() -> int:
    return get_settings().value("appearance/font_size", 11, type=int)


def set_font_size(size: int):
    get_settings().setValue("appearance/font_size", size)


def build_stylesheet(font_size: int = 11) -> str:
    fs = font_size
    fs_sm = max(fs - 1, 9)
    fs_lg = fs + 1
    fs_xl = fs + 3

    return f"""
/* === Global === */
QMainWindow {{
    background-color: #faf8f5;
    color: #2c2c2c;
}}

QWidget {{
    background-color: #faf8f5;
    color: #2c2c2c;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: {fs}pt;
}}

/* === Menu Bar === */
QMenuBar {{
    background-color: #f0ede6;
    color: #4a3728;
    border-bottom: 1px solid #d4c8b0;
    padding: 0px 0;
    font-weight: bold;
    font-size: {fs_sm}pt;
    min-height: 0px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 3px 10px;
    border-radius: 4px;
    margin: 1px 3px;
}}

QMenuBar::item:selected {{
    background-color: #e8dcc8;
    color: #6b4c2a;
}}

QMenu {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #d4c8b0;
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: #e8dcc8;
    color: #4a3728;
}}

QMenu::separator {{
    height: 1px;
    background: #d4c8b0;
    margin: 4px 8px;
}}

/* === Tab Widget === */
QTabWidget::pane {{
    border: 1px solid #d4c8b0;
    border-radius: 8px;
    background-color: #fefdfb;
    margin: 2px;
}}

QTabBar::tab {{
    background-color: #f0ede6;
    color: #6b5c4a;
    border: 1px solid #d4c8b0;
    padding: 5px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    font-size: {fs_sm}pt;
}}

QTabBar::tab:selected {{
    background-color: #fefdfb;
    color: #4a3728;
    border-bottom: 3px solid #c8a048;
}}

QTabBar::tab:hover:!selected {{
    background-color: #e8dcc8;
    color: #6b4c2a;
}}

/* === Group Box === */
QGroupBox {{
    border: 1px solid #d4c8b0;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: bold;
    font-size: {fs_sm}pt;
    color: #4a3728;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: #6b4c2a;
}}

/* === Buttons === */
QPushButton {{
    background-color: #e8dcc8;
    color: #4a3728;
    border: 1px solid #c8b898;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: {fs}pt;
}}

QPushButton:hover {{
    background-color: #dcc8a0;
    border-color: #b89868;
}}

QPushButton:pressed {{
    background-color: #c8a878;
}}

QPushButton:disabled {{
    background-color: #f0ede6;
    color: #b8a898;
    border-color: #d4c8b0;
}}

/* Accent: green */
QPushButton[accent="green"] {{
    background-color: #c8d8c0;
    border-color: #a0c090;
    color: #2c3a28;
}}
QPushButton[accent="green"]:hover {{
    background-color: #b0c8a8;
}}
QPushButton[accent="green"]:disabled {{
    background-color: #e8ece0;
    color: #a0b098;
}}

/* Accent: orange */
QPushButton[accent="orange"] {{
    background-color: #e8d0b8;
    border-color: #d0a878;
    color: #4a3020;
}}
QPushButton[accent="orange"]:hover {{
    background-color: #e0c0a0;
}}
QPushButton[accent="orange"]:disabled {{
    background-color: #f0e8e0;
    color: #c0b0a0;
}}

/* Accent: purple */
QPushButton[accent="purple"] {{
    background-color: #d8c8e0;
    border-color: #b8a0c8;
    color: #3a2848;
}}
QPushButton[accent="purple"]:hover {{
    background-color: #c8b0d8;
}}
QPushButton[accent="purple"]:disabled {{
    background-color: #e8e0f0;
    color: #b0a0c0;
}}

/* Accent: teal */
QPushButton[accent="teal"] {{
    background-color: #b8d8d0;
    border-color: #90c0b8;
    color: #1a3a34;
}}
QPushButton[accent="teal"]:hover {{
    background-color: #a0c8c0;
}}

/* === Labels === */
QLabel {{
    color: #2c2c2c;
    background: transparent;
}}

/* === Input fields === */
QLineEdit {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #c8b898;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: {fs}pt;
    selection-background-color: #d4c8b0;
    selection-color: #2c2c2c;
}}

QLineEdit:focus {{
    border-color: #a08050;
}}

/* === Combo Box === */
QComboBox {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #c8b898;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: {fs}pt;
}}

QComboBox:hover {{
    border-color: #a08050;
}}

QComboBox QAbstractItemView {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #d4c8b0;
    border-radius: 4px;
    selection-background-color: #e8dcc8;
    selection-color: #4a3728;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

/* === Spin Box === */
QSpinBox {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #c8b898;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {fs}pt;
}}

QSpinBox:focus {{
    border-color: #a08050;
}}

/* === Table Widget === */
QTableWidget {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #d4c8b0;
    border-radius: 8px;
    gridline-color: #e0d8c8;
    selection-background-color: #e8dcc8;
    selection-color: #4a3728;
    alternate-background-color: #f8f4ec;
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

QHeaderView::section {{
    background-color: #f0ede6;
    color: #4a3728;
    border: 1px solid #d4c8b0;
    padding: 8px 10px;
    font-weight: bold;
    font-size: {fs_sm}pt;
}}

/* === Text Edit === */
QTextEdit {{
    background-color: #fefdfb;
    color: #2c2c2c;
    border: 1px solid #c8b898;
    border-radius: 6px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: {fs}pt;
}}

/* === Check Box === */
QCheckBox {{
    color: #2c2c2c;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #a09070;
    border-radius: 4px;
}}

QCheckBox::indicator:checked {{
    background-color: #6b4c2a;
    border-color: #6b4c2a;
}}

/* === Scroll Bars === */
QScrollBar:vertical {{
    background: #f0ede6;
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: #c8b898;
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: #a89870;
}}

QScrollBar:horizontal {{
    background: #f0ede6;
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: #c8b898;
    border-radius: 5px;
    min-width: 20px;
}}

/* === Status Bar === */
QStatusBar {{
    background-color: #f0ede6;
    color: #6b5c4a;
    border-top: 1px solid #d4c8b0;
    padding: 4px 10px;
    font-size: {fs_sm}pt;
}}

/* === Splitter === */
QSplitter::handle {{
    background-color: #d4c8b0;
    width: 2px;
}}

/* === Tooltips === */
QToolTip {{
    background-color: #fefdfb;
    color: #4a3728;
    border: 1px solid #c8a048;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: {fs_sm}pt;
}}

/* === Slider (for font size) === */
QSlider::groove:horizontal {{
    border: 1px solid #c8b898;
    height: 6px;
    background: #f0ede6;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #6b4c2a;
    border: 1px solid #4a3728;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: #8a6840;
}}
"""


def apply_theme(app):
    """Apply the light music theme to the application."""
    font_size = get_font_size()
    app.setStyleSheet(build_stylesheet(font_size))


def refresh_theme(app):
    """Re-apply theme with current font size (call after font size change)."""
    apply_theme(app)
