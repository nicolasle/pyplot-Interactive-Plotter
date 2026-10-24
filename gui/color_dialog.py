"""
Enhanced Color Selector Dialog with Matplotlib tab10 Palette
"""

from typing import Optional, Union
from PySide6.QtWidgets import (
    QColorDialog, QWidget, QHBoxLayout, QPushButton, QGroupBox, QDialog
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal

# Matplotlib tab10 categorical palette (Tableau 10)
TAB10_COLORS = [
    ("tab:blue", "#1f77b4"),
    ("tab:orange", "#ff7f0e"),
    ("tab:green", "#2ca02c"),
    ("tab:red", "#d62728"),
    ("tab:purple", "#9467bd"),
    ("tab:brown", "#8c564b"),
    ("tab:pink", "#e377c2"),
    ("tab:gray", "#7f7f7f"),
    ("tab:olive", "#bcbd22"),
    ("tab:cyan", "#17becf"),
]

# Pre-populate custom and standard color slots in QColorDialog globally
for i, (name, hex_code) in enumerate(TAB10_COLORS):
    c = QColor(hex_code)
    QColorDialog.setCustomColor(i, c)
    QColorDialog.setStandardColor(i, c)


class SwatchButton(QPushButton):
    """Button representing a single color swatch with double-click confirmation."""
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class ColorSelectorDialog(QColorDialog):
    """
    Enhanced Color Selector Dialog:
    - Dedicated Matplotlib tab10 palette bar prominently at the top
    - Pre-populated 'Custom Colors' grid slots with the 10 tab10 colors
    - Full color picker (RGB, HSV, HTML Hex) with cross-platform dialog
    - Single-click to preview / select, double-click to immediately accept
    """

    def __init__(
        self,
        initial_color: Optional[Union[str, QColor]] = None,
        parent: Optional[QWidget] = None,
        title: str = "Color Selector (Matplotlib tab10)"
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)

        # Parse and set initial color
        if initial_color:
            if isinstance(initial_color, str):
                cleaned = initial_color.strip()
                if cleaned.lower() == "auto":
                    cleaned = "#1f77b4"
                elif cleaned.startswith("tab:"):
                    tab_dict = dict(TAB10_COLORS)
                    cleaned = tab_dict.get(cleaned, cleaned)
                c = QColor(cleaned)
                if c.isValid():
                    self.setCurrentColor(c)
            elif isinstance(initial_color, QColor) and initial_color.isValid():
                self.setCurrentColor(initial_color)

        # Matplotlib tab10 Palette bar
        tab10_box = QGroupBox("Matplotlib tab10 Colors (Click to preview, double-click to confirm)")
        tab10_box.setStyleSheet(
            "QGroupBox { font-weight: bold; margin-top: 8px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )
        tab10_layout = QHBoxLayout(tab10_box)
        tab10_layout.setContentsMargins(8, 8, 8, 8)
        tab10_layout.setSpacing(6)

        self._swatch_buttons = []
        for name, hex_code in TAB10_COLORS:
            btn = SwatchButton()
            btn.setToolTip(f"{name} ({hex_code})")
            btn.setFixedSize(36, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_code};
                    border: 2px solid #334155;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            # Single click -> select color in dialog
            btn.clicked.connect(lambda checked=False, hc=hex_code: self.setCurrentColor(QColor(hc)))
            # Double click -> select color and confirm
            btn.doubleClicked.connect(lambda hc=hex_code: self._confirm_color(hc))
            tab10_layout.addWidget(btn)
            self._swatch_buttons.append(btn)

        layout = self.layout()
        if layout:
            layout.insertWidget(0, tab10_box)

    def _confirm_color(self, hex_code: str):
        self.setCurrentColor(QColor(hex_code))
        self.accept()

    @classmethod
    def get_color(
        cls,
        initial_color: Optional[Union[str, QColor]] = "#1f77b4",
        parent: Optional[QWidget] = None,
        title: str = "Select Color"
    ) -> QColor:
        """Helper to open dialog and return selected QColor (or invalid QColor if cancelled)."""
        dlg = cls(initial_color=initial_color, parent=parent, title=title)
        if dlg.exec() == QDialog.Accepted:
            return dlg.selectedColor()
        return QColor()
