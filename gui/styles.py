"""
Modern Scientific Styling & Theme for PySide6 Application
"""

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1e1e24;
    color: #e0e0e0;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #1e1e24;
    color: #e0e0e0;
}

QTabWidget::pane {
    border: 1px solid #33333d;
    background-color: #25252d;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #1e1e24;
    color: #a0a0a8;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #2b2b36;
    color: #ffffff;
    border-bottom: 2px solid #3b82f6;
}

QTabBar::tab:hover:!selected {
    background-color: #262630;
    color: #d0d0d8;
}

QGroupBox {
    border: 1px solid #33333e;
    border-radius: 6px;
    margin-top: 1.2em;
    padding-top: 0.8em;
    font-weight: 600;
    color: #93c5fd;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QPushButton {
    background-color: #2e303d;
    color: #f3f4f6;
    border: 1px solid #434656;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3b3e4f;
    border-color: #60a5fa;
}

QPushButton:pressed {
    background-color: #252733;
}

QPushButton#primaryBtn {
    background-color: #2563eb;
    color: white;
    border: 1px solid #3b82f6;
}

QPushButton#primaryBtn:hover {
    background-color: #1d4ed8;
}

QPushButton#accentBtn {
    background-color: #059669;
    color: white;
    border: 1px solid #10b981;
}

QPushButton#accentBtn:hover {
    background-color: #047857;
}

QLineEdit, QComboBox {
    background-color: #282832;
    border: 1px solid #424250;
    border-radius: 4px;
    padding: 4px 8px;
    color: #f3f4f6;
    selection-background-color: #3b82f6;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}

QSpinBox, QDoubleSpinBox {
    background-color: #282832;
    border: 1px solid #424250;
    border-radius: 4px;
    padding-left: 6px;
    padding-right: 22px;
    padding-top: 2px;
    padding-bottom: 2px;
    min-height: 24px;
    color: #f3f4f6;
    selection-background-color: #3b82f6;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #3b82f6;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    height: 13px;
    border-left: 1px solid #424250;
    border-bottom: 1px solid #424250;
    border-top-right-radius: 3px;
    background-color: #2e303d;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background-color: #3b82f6;
}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {
    background-color: #1d4ed8;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    height: 13px;
    border-left: 1px solid #424250;
    border-bottom-right-radius: 3px;
    background-color: #2e303d;
}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #3b82f6;
}

QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background-color: #1d4ed8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #424250;
}

QTableWidget, QTreeWidget, QListWidget {
    background-color: #22222a;
    border: 1px solid #33333e;
    gridline-color: #2e2e38;
    color: #e5e7eb;
    border-radius: 4px;
}

QHeaderView::section {
    background-color: #2a2a35;
    color: #9ca3af;
    padding: 5px;
    border: 1px solid #33333e;
    font-weight: 600;
}

QScrollBar:vertical {
    background: #1e1e24;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #424250;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #565666;
}

QScrollBar:horizontal {
    background: #1e1e24;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background: #424250;
    min-width: 20px;
    border-radius: 4px;
}

QCheckBox {
    spacing: 6px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #4b5563;
    background-color: #282832;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

QSplitter::handle {
    background-color: #33333e;
}

QSplitter::handle:hover {
    background-color: #3b82f6;
}

QPlainTextEdit, QTextEdit {
    background-color: #1a1a20;
    color: #e2e8f0;
    border: 1px solid #33333e;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border-radius: 4px;
}

QMenuBar {
    background-color: #1a1a20;
    color: #e0e0e0;
    border-bottom: 1px solid #2e2e38;
    padding: 2px 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #2e303d;
}

QMenu {
    background-color: #22222a;
    color: #e0e0e0;
    border: 1px solid #434656;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #33333e;
    margin: 4px 8px;
}

QToolBar {
    background-color: #1c1c23;
    border-bottom: 1px solid #2e2e3a;
    spacing: 6px;
    padding: 4px 8px;
}

QToolButton {
    background-color: #282834;
    color: #f3f4f6;
    border: 1px solid #3e3e4e;
    border-radius: 4px;
    padding: 5px 10px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #3b3e4f;
    border-color: #60a5fa;
}

QToolButton:pressed {
    background-color: #252733;
}
"""
