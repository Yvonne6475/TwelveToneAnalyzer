"""Reusable table widgets with copy support."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QMenu, QTableWidget

from src.utils.i18n import tr


class CopyableTableWidget(QTableWidget):
    """QTableWidget with multi-cell selection and Ctrl/Cmd+C copy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            if self._copy_selected():
                event.accept()
                return
        super().keyPressEvent(event)

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is not None and not item.isSelected():
            self.clearSelection()
            item.setSelected(True)
        menu = QMenu(self)
        copy_action = menu.addAction(tr("table.copy"))
        if menu.exec_(self.viewport().mapToGlobal(pos)) is copy_action:
            self._copy_selected()

    def _copy_selected(self) -> bool:
        text = self._selected_text()
        if not text:
            return False
        QApplication.clipboard().setText(text)
        return True

    def _selected_text(self):
        items = self.selectedItems()
        if not items:
            return ""
        positions = [(item.row(), item.column(), item.text()) for item in items]
        rows = sorted({r for r, _, _ in positions})
        cols = sorted({c for _, c, _ in positions})
        grid = {(r, c): text for r, c, text in positions}
        return "\n".join(
            "\t".join(grid.get((r, c), "") for c in cols)
            for r in rows
        )
