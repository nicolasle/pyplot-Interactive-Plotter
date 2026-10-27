"""
Pyplot Interactive Plotter
Desktop Application Entrypoint
Run with: python app.py
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QLocale

from gui.main_window import MainWindow, NumericInputFilter


def main():
    # Force C locale globally so all numbers use decimal point (.) and not comma (,)
    QLocale.setDefault(QLocale.c())

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Pyplot Interactive Plotter")
    app.setOrganizationName("Scientific Tools")

    # Install numeric input filter to map comma to period in spinboxes & limit edits
    decimal_filter = NumericInputFilter(app)
    app.installEventFilter(decimal_filter)
    app._decimal_filter_installed = True

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
