"""
Pyplot Interactive Plotter
Desktop Application Entrypoint
Run with: python app.py
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.main_window import MainWindow


def main():
    # Configure high-DPI attributes if supported
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Pyplot Interactive Plotter")
    app.setOrganizationName("Scientific Tools")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
