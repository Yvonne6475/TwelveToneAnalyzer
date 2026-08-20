"""Twelve-tone matrix visualization — standalone popup window."""

import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QWidget

from src.core.twelve_tone import generate_matrix

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B']


class MatrixWidget(QWidget):
    """Placeholder; show_matrix() opens a standalone matplotlib window.

    Closing the heatmap window does not prompt for saving; use the
    Export Heatmap button in the tab to save the figure as PNG.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._standalone_fig = None

    @property
    def fig(self):
        return self._standalone_fig

    def show_matrix(self, row: list[int], block: bool = False):
        """Render heatmap in a standalone matplotlib window.

        Parameters
        ----------
        row : list[int]
            12 pitch-class integers.
        block : bool
            If False (default), returns immediately — the caller is
            responsible for polling fig.number and prompting save.
            If True, blocks until the user closes the window, then
            prompts to save inline.
        """
        mat = generate_matrix(row)

        fig, ax = plt.subplots(figsize=(16, 11))
        self._standalone_fig = fig
        _num = fig.number

        cax = ax.matshow(mat, cmap='tab20', vmin=0, vmax=11)

        # Edge labels
        top_labels = [f"I{mat[0, j]}" for j in range(12)]
        left_labels = [f"P{mat[i, 0]}" for i in range(12)]
        right_labels = [f"R{mat[i, -1]}" for i in range(12)]
        bottom_labels = [f"RI{mat[-1, j]}" for j in range(12)]

        ax.set_xticks(np.arange(12))
        ax.set_yticks(np.arange(12))
        ax.set_xticklabels(top_labels, rotation=90, fontsize=14)
        ax.xaxis.set_ticks_position("top")
        ax.set_yticklabels(left_labels, fontsize=14)

        ax_twin_x = ax.secondary_xaxis(location="bottom")
        ax_twin_x.set_xticks(np.arange(12))
        ax_twin_x.set_xticklabels(bottom_labels, rotation=90, fontsize=14)

        ax_twin_y = ax.secondary_yaxis(location="right")
        ax_twin_y.set_yticks(np.arange(12))
        ax_twin_y.set_yticklabels(right_labels, fontsize=14)

        for i in range(12):
            for j in range(12):
                pc = mat[i, j]
                ax.text(j, i, f"{NOTE_NAMES[pc]}\n({pc})",
                        ha="center", va="center", fontsize=12)

        ax.set_title("12-Tone Matrix  ( I top / P left / R right / RI bottom )", fontsize=20, pad=25)
        cb = plt.colorbar(cax, shrink=0.85)
        cb.set_label("Pitch Class: 0=C, 10=A, 11=B", fontsize=14)
        plt.tight_layout()

        if block:
            # Blocking mode: just show until the window is closed.
            plt.show()
        else:
            # Non-blocking: keep the window open and return immediately.
            plt.show(block=False)
