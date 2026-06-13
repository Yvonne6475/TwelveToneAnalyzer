"""Forte Name Dialog: batch analysis of pitch-class sets with Forte classification."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt

from music21 import chord

from src.utils.i18n import tr, tr_list


class ForteNameDialog(QDialog):
    """Standalone dialog for batch pitch-class set Forte analysis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("forte.title"))
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Input area
        layout.addWidget(QLabel(tr("forte.input_label")))
        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText(
            "6 8 11 1 4\n7 10 0 3 5\n2 5 7 9 0\n7 9 0\n..."
        )
        self._input_edit.setMinimumHeight(100)
        layout.addWidget(self._input_edit)

        # Button row
        btn_row = QHBoxLayout()
        self._btn_analyze = QPushButton(tr("forte.btn_analyze"))
        self._btn_analyze.setProperty("accent", "teal")
        self._btn_analyze.clicked.connect(self._on_analyze)
        btn_row.addWidget(self._btn_analyze)

        self._btn_copy = QPushButton(tr("forte.btn_copy"))
        self._btn_copy.setEnabled(False)
        self._btn_copy.clicked.connect(self._on_copy)
        btn_row.addWidget(self._btn_copy)

        self._btn_export = QPushButton(tr("forte.btn_export_csv"))
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._on_export_csv)
        btn_row.addWidget(self._btn_export)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Results table
        headers = tr_list("forte.table.headers")
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._table, 1)

    def _on_analyze(self):
        text = self._input_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, tr("forte.title"), tr("forte.empty_input"))
            return

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        self._results = []

        for line in lines:
            try:
                pcs = list(map(int, line.split()))
            except ValueError:
                continue
            if not pcs:
                continue
            c = chord.Chord(pcs)
            self._results.append({
                "input": pcs,
                "normal": list(c.normalOrder),
                "prime": c.primeFormString,
                "forte": c.forteClass,
            })

        self._table.setRowCount(len(self._results))
        for row, r in enumerate(self._results):
            self._table.setItem(row, 0,
                QTableWidgetItem(" ".join(map(str, r["input"]))))
            self._table.setItem(row, 1,
                QTableWidgetItem(str(r["normal"])))
            self._table.setItem(row, 2,
                QTableWidgetItem(r["prime"]))
            self._table.setItem(row, 3,
                QTableWidgetItem(r["forte"]))

        self._btn_copy.setEnabled(bool(self._results))
        self._btn_export.setEnabled(bool(self._results))

    def _on_copy(self):
        lines = [
            "Input Set\tNormal Order\tPrime Form\tForte Class"
        ]
        for r in self._results:
            lines.append(
                f"{' '.join(map(str, r['input']))}\t"
                f"{r['normal']}\t{r['prime']}\t{r['forte']}"
            )
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, tr("forte.title"), "Copied to clipboard.")

    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("forte.save_csv"), "forte_analysis.csv",
            "CSV (*.csv);;All Files (*)"
        )
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write("Input Set,Normal Order,Prime Form,Forte Class\n")
            for r in self._results:
                f.write(
                    f'"{" ".join(map(str, r["input"]))}",'
                    f'"{r["normal"]}","{r["prime"]}","{r["forte"]}"\n'
                )
        from src.utils.i18n import tr as _tr
        QMessageBox.information(self, _tr("forte.title"),
                                _tr("dialog.saved_to", path=path))
