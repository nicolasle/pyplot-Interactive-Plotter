"""
Pyplot Interactive Plotter
Desktop Application Entrypoint
Run with: python app.py
"""

import sys
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient
from PySide6.QtCore import Qt, QLocale


class AppSplashScreen(QSplashScreen):
    """
    Lightweight, modern splash screen displayed instantly on cold start
    to provide immediate visual confirmation and loading progress.
    """
    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self._status_text = "Starting..."

    def set_status(self, text: str):
        self._status_text = text
        self.repaint()
        QApplication.processEvents()

    def drawContents(self, painter: QPainter):
        super().drawContents(painter)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.setPen(QColor("#8fa0b5"))
        rect = self.rect().adjusted(32, 0, -32, -22)
        painter.drawText(rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, self._status_text)
        painter.restore()


def _create_splash_pixmap() -> QPixmap:
    width, height = 480, 220
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Modern dark card background matching DARK_THEME
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#1e1e24"))
    gradient.setColorAt(1.0, QColor("#141418"))
    painter.setBrush(QBrush(gradient))
    painter.setPen(QPen(QColor("#3d3d4d"), 1.5))
    painter.drawRoundedRect(1, 1, width - 2, height - 2, 10, 10)

    # Title
    font = QFont("Segoe UI", 16, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#4da6ff"))
    painter.drawText(32, 58, "Pyplot Interactive Plotter")

    # Subtitle
    font.setPointSize(9)
    font.setWeight(QFont.Weight.Normal)
    painter.setFont(font)
    painter.setPen(QColor("#9da2b0"))
    painter.drawText(32, 84, "Publication-Quality Scientific Visualizer")

    # Accent decorative bar
    painter.setBrush(QBrush(QColor("#007acc")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(32, 102, 50, 3, 1.5, 1.5)

    painter.end()
    return pixmap


def main():
    # Force C locale globally so all numbers use decimal point (.) and not comma (,)
    QLocale.setDefault(QLocale.c())

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Pyplot Interactive Plotter")
    app.setOrganizationName("Scientific Tools")

    # Show splash screen immediately for instant visual feedback on startup
    pixmap = _create_splash_pixmap()
    splash = AppSplashScreen(pixmap)
    splash.show()
    splash.set_status("Loading scientific plotting engine...")

    # Import heavy UI and plotting dependencies while splash is visible
    from gui.main_window import MainWindow, NumericInputFilter

    # Install numeric input filter to map comma to period in spinboxes & limit edits
    decimal_filter = NumericInputFilter(app)
    app.installEventFilter(decimal_filter)
    app._decimal_filter_installed = True

    splash.set_status("Building user interface & workspace...")
    window = MainWindow()

    splash.set_status("Ready!")
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
