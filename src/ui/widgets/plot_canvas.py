"""Matplotlib FigureCanvas wrapper for embedding plots in PyQt5 tabs."""

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PlotCanvas(FigureCanvas):
    """Embeddable matplotlib canvas that supports toolbar navigation."""

    def __init__(self, parent=None, dpi=100):
        self.fig = Figure(dpi=dpi, facecolor='#fefdfb')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(350)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy()
        )

    def clear(self):
        self.fig.clear()
        self.resize(self.sizeHint())

    def set_size_inches(self, w, h):
        self.fig.set_size_inches(w, h)
        w_px = int(w * self.fig.dpi)
        h_px = int(h * self.fig.dpi)
        self.setMinimumSize(w_px, h_px)
        self.resize(w_px, h_px)

    def sizeHint(self):
        w = int(self.fig.get_figwidth() * self.fig.dpi)
        h = int(self.fig.get_figheight() * self.fig.dpi)
        return self.minimumSize().expandedTo(super().sizeHint())

    def tight_layout(self):
        self.fig.tight_layout()
